#!/usr/bin/env python
"""Keep one canonical file per exact PDF hash and reconcile site products/overrides."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "pdf"
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
INVENTORY_PATH = DATA_DIR / "pdf-inventory.local.json"
PRODUCTS_PATH = DATA_DIR / "msds.local.json"
OVERRIDES_PATH = DATA_DIR / "msds-overrides.local.json"
REPORT_PATH = REPORTS_DIR / "pdf-dedup.local.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_list(payload: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in keys:
            if isinstance(payload.get(key), list):
                return payload[key]
    raise ValueError("JSON 목록을 찾을 수 없습니다.")


def replace_list(payload: Any, key: str, values: list[dict[str, Any]]) -> Any:
    if isinstance(payload, list):
        return values
    return {**payload, key: values}


def normalize_path(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/").removeprefix("/").removeprefix("pdf/")


def normalize_name(value: Any) -> str:
    return re.sub(r"[\W_]+", "", str(value or "").casefold())


def canonical_score(relative_path: str) -> tuple[int, int, str]:
    first = relative_path.split("/", 1)[0]
    penalties = {
        "GGM 상주원": 100,
        "03_ 시험실(시약)": 50,
        "00_ 사출": 40,
        "01_ 도장": 30,
        "02_ 조립": 30,
    }
    penalty = penalties.get(first, 60 if "/" not in relative_path else 0)
    # 같은 PDF라면 오타가 포함된 경로를 대표본으로 남기지 않는다.
    if "블스원" in relative_path or "코광택" in relative_path:
        penalty += 200
    return penalty, len(relative_path), relative_path.casefold()


def product_score(product: dict[str, Any]) -> tuple[int, int, int, str]:
    product_id = str(product.get("id") or "")
    score = 1000 if not product_id.startswith("msds-pdf-") else 0
    msds_no = str(product.get("msdsNo") or "")
    if msds_no and "미기재" not in msds_no and "적용되지" not in msds_no:
        score += 100
    elif re.search(r"/\s*[A-Za-z0-9][A-Za-z0-9._-]*", msds_no):
        # 예: 'MSDS번호 미기재 / LP1027.6'처럼 보조 관리번호가 있으면 보존한다.
        score += 50
    score += len(product.get("ingredients") or [])
    score += sum(1 for key in ("erpName", "supplier", "hazardClassification", "revisionDate") if product.get(key))
    return score, len(product.get("ingredients") or []), -len(product_id), product_id


def override_score(override: dict[str, Any], canonical_path: str) -> tuple[int, int, int]:
    score = 1000 if override.get("reviewStatus") == "검토완료" else 0
    if normalize_path(override.get("sourceRelativePath")) == canonical_path:
        score += 200
    score += 100 * sum(1 for key in override if key.startswith("manual") or key.startswith("reviewed"))
    score += len(override.get("hazardStatements") or []) + len(override.get("ingredients") or [])
    return score, len(override.get("ingredients") or []), len(override.get("hazardStatements") or [])


def path_for_override(override: dict[str, Any]) -> str:
    match = override.get("match") if isinstance(override.get("match"), dict) else {}
    return normalize_path(override.get("sourceRelativePath") or match.get("relativePath") or override.get("sourcePdfPath"))


def update_product_path(product: dict[str, Any], canonical: dict[str, Any]) -> None:
    relative = canonical["relativePath"]
    product["fileName"] = canonical["fileName"]
    product["relativePath"] = relative
    product["pdfPath"] = f"pdf/{relative}"


def update_override_path(override: dict[str, Any], canonical: dict[str, Any]) -> None:
    relative = canonical["relativePath"]
    override["sourceRelativePath"] = relative
    override["sourcePdfPath"] = f"pdf/{relative}"
    match = deepcopy(override.get("match") or {})
    match["fileName"] = canonical["fileName"]
    match["relativePath"] = relative
    override["match"] = match


def merge_review_fields(target: dict[str, Any], source: dict[str, Any]) -> None:
    if source.get("reviewStatus") == "검토완료" and target.get("reviewStatus") != "검토완료":
        target["reviewStatus"] = "검토완료"
    for key, value in source.items():
        if (key.startswith("manual") or key.startswith("reviewed")) and value not in (None, "", [], {}):
            target.setdefault(key, value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="백업 후 중복 PDF와 중복 사이트 항목을 실제 정리")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory_payload = read_json(INVENTORY_PATH)
    product_payload = read_json(PRODUCTS_PATH)
    override_payload = read_json(OVERRIDES_PATH)
    inventory = get_list(inventory_payload, ("items", "inventory"))
    products = deepcopy(get_list(product_payload, ("products",)))
    overrides = deepcopy(get_list(override_payload, ("overrides",)))

    hash_groups: dict[str, list[dict[str, Any]]] = {}
    for item in inventory:
        sha256 = str(item.get("sha256") or "").lower()
        if sha256:
            hash_groups.setdefault(sha256, []).append(item)
    duplicates = {key: items for key, items in hash_groups.items() if len(items) > 1}

    path_to_hash = {
        normalize_path(item.get("relativePath")): sha256
        for sha256, items in duplicates.items()
        for item in items
    }
    name_to_hashes: dict[str, set[str]] = {}
    for sha256, items in duplicates.items():
        for item in items:
            name_to_hashes.setdefault(str(item.get("fileName") or "").casefold(), set()).add(sha256)

    plans: list[dict[str, Any]] = []
    canonical_by_hash: dict[str, dict[str, Any]] = {}
    removed_paths: list[str] = []
    for sha256, items in sorted(duplicates.items()):
        canonical = sorted(items, key=lambda item: canonical_score(normalize_path(item.get("relativePath"))))[0]
        canonical = {**canonical, "relativePath": normalize_path(canonical.get("relativePath"))}
        canonical_by_hash[sha256] = canonical
        removed = sorted(
            normalize_path(item.get("relativePath"))
            for item in items
            if normalize_path(item.get("relativePath")) != canonical["relativePath"]
        )
        removed_paths.extend(removed)
        plans.append({"sha256": sha256, "canonical": canonical["relativePath"], "removed": removed})

    product_hashes: dict[str, list[dict[str, Any]]] = {}
    for product in products:
        direct_path = normalize_path(product.get("relativePath") or product.get("pdfPath"))
        sha256 = path_to_hash.get(direct_path)
        if not sha256:
            hashes = name_to_hashes.get(str(product.get("fileName") or "").casefold(), set())
            if len(hashes) == 1:
                sha256 = next(iter(hashes))
        if sha256:
            product_hashes.setdefault(sha256, []).append(product)

    removed_product_ids: set[str] = set()
    for sha256, group_products in product_hashes.items():
        canonical = canonical_by_hash[sha256]
        by_name: dict[str, list[dict[str, Any]]] = {}
        for product in group_products:
            by_name.setdefault(normalize_name(product.get("productName")), []).append(product)
        for same_name_products in by_name.values():
            keeper = sorted(same_name_products, key=product_score, reverse=True)[0]
            update_product_path(keeper, canonical)
            for duplicate in same_name_products:
                if duplicate is not keeper:
                    removed_product_ids.add(str(duplicate.get("id") or ""))
        for product in group_products:
            if str(product.get("id") or "") not in removed_product_ids:
                update_product_path(product, canonical)
    products = [item for item in products if str(item.get("id") or "") not in removed_product_ids]

    override_hashes: dict[str, list[dict[str, Any]]] = {}
    untouched_overrides: list[dict[str, Any]] = []
    for override in overrides:
        path = path_for_override(override)
        sha256 = path_to_hash.get(path)
        if sha256:
            override_hashes.setdefault(sha256, []).append(override)
        else:
            untouched_overrides.append(override)
    selected_overrides: list[dict[str, Any]] = []
    removed_override_count = 0
    for sha256, group_overrides in override_hashes.items():
        canonical = canonical_by_hash[sha256]
        keeper = sorted(group_overrides, key=lambda item: override_score(item, canonical["relativePath"]), reverse=True)[0]
        for item in group_overrides:
            if item is not keeper:
                merge_review_fields(keeper, item)
                removed_override_count += 1
        update_override_path(keeper, canonical)
        selected_overrides.append(keeper)
    overrides = untouched_overrides + selected_overrides

    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "mode": "apply" if args.apply else "dry-run",
        "exactDuplicateGroupCount": len(plans),
        "physicalPdfRemovalCount": len(removed_paths),
        "productRemovalCount": len(removed_product_ids),
        "overrideRemovalCount": removed_override_count,
        "productCountBefore": len(get_list(product_payload, ("products",))),
        "productCountAfter": len(products),
        "overrideCountBefore": len(get_list(override_payload, ("overrides",))),
        "overrideCountAfter": len(overrides),
        "plans": plans,
        "removedProductIds": sorted(removed_product_ids),
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    write_json(REPORT_PATH, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.apply:
        return 0

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = DATA_DIR / "backups" / "pdf-dedup" / timestamp
    backup_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PRODUCTS_PATH, backup_root / PRODUCTS_PATH.name)
    shutil.copy2(OVERRIDES_PATH, backup_root / OVERRIDES_PATH.name)
    for relative in removed_paths:
        source = (PDF_DIR / relative).resolve()
        if PDF_DIR.resolve() not in source.parents or not source.is_file():
            raise ValueError(f"삭제 대상 경로가 안전하지 않습니다: {source}")
        backup_file = backup_root / "pdf" / relative
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, backup_file)
        source.unlink()

    write_json(PRODUCTS_PATH, replace_list(product_payload, "products", products))
    write_json(OVERRIDES_PATH, replace_list(override_payload, "overrides", overrides))
    print(f"백업: {backup_root}")
    print(f"PDF 삭제: {len(removed_paths)}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
