#!/usr/bin/env python
"""Normalize visible MSDS product and ingredient text without changing source PDFs or Excel."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_PATH = ROOT / "data" / "msds.local.json"
OVERRIDES_PATH = ROOT / "data" / "msds-overrides.local.json"
REPORT_JSON = ROOT / "reports" / "msds-display-text-audit.local.json"
REPORT_CSV = ROOT / "reports" / "msds-display-text-audit.local.csv"

PRODUCT_NAME_REPLACEMENTS = {
    "Isovaleric Acid": "아이소발레르산(Isovaleric Acid)",
    "Acetone (100080)": "아세톤(Acetone, 100080)",
    "Phosphoric acid": "인산(Phosphoric acid)",
    "Stainless Steel Coat": "스테인리스강 코팅제(Stainless Steel Coat)",
    "ISOPROPYL ALCOHOL BULK": "이소프로필 알코올 벌크(ISOPROPYL ALCOHOL BULK)",
    "Natural Gas with Odorant": "부취제가 첨가된 천연가스(Natural Gas with Odorant)",
    "Graco TSL": "그라코 TSL",
    "MULTI-CLEANER DC-3000": "다목적 세정제 DC-3000",
    "LONG #2 Spray": "LONG #2 스프레이",
    "KU 4150KNK.. (H600-H0554H)": "KU 4150KNK (H600-H0554H)",
    "KC-28.": "KC-28",
    "LOCTITE SF CPG CA PRIMIER GOLD known as CA PRIMER GOLD 230ML": "LOCTITE SF CPG CA PRIMER GOLD 230ML",
    "PN3084 FINESSE-IT FINISHING MATERIAL": "PN3084 피네스잇 마무리 연마재(FINESSE-IT FINISHING MATERIAL)",
    "INTEC - SPRAY": "인텍 스프레이(INTEC - SPRAY)",
    "3M PN3021 Imperial Micro finishing Compound": "3M PN3021 임페리얼 미세 마감 컴파운드",
    "3M™ Finesse-It™ Polish - Finishing Material, 13084, 28792, 81235, 83058": "3M™ 피네스잇™ 폴리시 - 마무리 연마재(13084, 28792, 81235, 83058)",
    "3M™ Finesse-It™ Polish - Final Finish 28796, 84224, 82877, 82878, 88753": "3M™ 피네스잇™ 폴리시 - 최종 마감재(28796, 84224, 82877, 82878, 88753)",
}

INGREDIENT_NAME_REPLACEMENTS = {
    "Polyester resin": "폴리에스터 수지",
    "Polyolefin": "폴리올레핀",
    "FLUORPHLOGOPITE": "플루오르플로고파이트(합성 운모)",
    "Copolymer of Acrylic and Polyester resin": "아크릴-폴리에스터 공중합 수지",
    "Copolymer of Acrliyc and Polyester resin": "아크릴-폴리에스터 공중합 수지",
    "Dihydro-3-(tetrapropenyl)-2,5-furandione": "테트라프로페닐 숙신산 무수물",
    "(1-메틸에틸)벤젠": "큐멘(1-메틸에틸벤젠)",
    "폴리(헥사메틸렌 디아이소시안산)": "헥사메틸렌 디이소시아네이트 중합체",
}

TEXT_REPLACEMENTS = {
    "2.5-푸란디온": "2,5-푸란디온",
    "프로필렌 글라이콜 모노메틸 에테르 아세트산": "프로필렌 글리콜 모노메틸 에테르 아세테이트",
    "폴리(헥사메틸렌 디아이 소시안산)": "헥사메틸렌 디이소시아네이트 중합체",
    "2-(2-뷰톡시에톡시)에탄올 아 세테이트": "2-(2-뷰톡시에톡시)에탄올 아세테이트",
    "방향족 경질 나프타 용매 (석유)": "방향족 경질 나프타 용매(석유)",
    "방향족 중질 나프타 용매 (석유)": "방향족 중질 나프타 용매(석유)",
    "Acrliyc": "Acrylic",
    "arcrylate": "acrylate",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_list(path: Path, key: str) -> tuple[Any, list[dict[str, Any]]]:
    payload = read_json(path)
    if isinstance(payload, list):
        return payload, payload
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return payload, payload[key]
    raise ValueError(f"목록을 찾을 수 없습니다: {path}")


def replace_list(payload: Any, key: str, values: list[dict[str, Any]]) -> Any:
    if isinstance(payload, list):
        return values
    return {**payload, key: values}


def clean_display_text(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    for before, after in TEXT_REPLACEMENTS.items():
        text = text.replace(before, after)
    return text


def has_korean(value: Any) -> bool:
    return bool(re.search(r"[가-힣]", str(value or "")))


def normalize_product_name(value: Any) -> str:
    text = clean_display_text(value)
    text = re.sub(r"\bCAMS\s+용\b", "CAMS용", text)
    return PRODUCT_NAME_REPLACEMENTS.get(text, text)


def normalize_ingredient_name(value: Any, cas_no: Any, cas_map: dict[str, str]) -> tuple[str, str]:
    before = clean_display_text(value)
    exact = INGREDIENT_NAME_REPLACEMENTS.get(before)
    if exact:
        return clean_display_text(exact), "exact_translation"

    cas = str(cas_no or "").strip()
    reference = clean_display_text(cas_map.get(cas, ""))
    if before and not has_korean(before) and reference and has_korean(reference):
        return reference, "cas_reference_translation"
    return before, "text_cleanup" if before != str(value or "").strip() else ""


def normalize_ingredients(
    owner: dict[str, Any],
    owner_type: str,
    owner_name: str,
    cas_map: dict[str, str],
    changes: list[dict[str, Any]],
) -> None:
    for field in ("ingredients", "components"):
        values = owner.get(field)
        if not isinstance(values, list):
            continue
        for ingredient in values:
            if not isinstance(ingredient, dict):
                continue
            name_field = "chemicalName" if "chemicalName" in ingredient else "name"
            before = ingredient.get(name_field, "")
            after, reason = normalize_ingredient_name(before, ingredient.get("casNo") or ingredient.get("cas"), cas_map)
            if after and after != before:
                ingredient[name_field] = after
                changes.append({
                    "type": f"{owner_type}_{field}_chemicalName",
                    "owner": owner_name,
                    "casNo": ingredient.get("casNo") or ingredient.get("cas") or "",
                    "reason": reason,
                    "before": before,
                    "after": after,
                })


def normalize_products(products: list[dict[str, Any]], cas_map: dict[str, str], changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = deepcopy(products)
    for product in result:
        before = product.get("productName", "")
        after = normalize_product_name(before)
        if after != before:
            product["productName"] = after
            changes.append({"type": "productName", "owner": product.get("id", ""), "before": before, "after": after})
        normalize_ingredients(product, "product", after, cas_map, changes)
    return result


def normalize_overrides(overrides: list[dict[str, Any]], cas_map: dict[str, str], changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = deepcopy(overrides)
    for override in result:
        before = override.get("productNameCandidate", "")
        after = normalize_product_name(before)
        if after != before:
            override["productNameCandidate"] = after
            changes.append({"type": "overrideProductName", "owner": (override.get("match") or {}).get("fileName", ""), "before": before, "after": after})
        normalize_ingredients(override, "override", after or (override.get("match") or {}).get("fileName", ""), cas_map, changes)
    return result


def write_report(changes: list[dict[str, Any]], mode: str) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "changeCount": len(changes),
        "changeTypeCounts": {},
        "changes": changes,
    }
    for change in changes:
        kind = change["type"]
        summary["changeTypeCounts"][kind] = summary["changeTypeCounts"].get(kind, 0) + 1
    write_json(REPORT_JSON, summary)
    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["type", "owner", "casNo", "reason", "before", "after"])
        writer.writeheader()
        for change in changes:
            writer.writerow({key: change.get(key, "") for key in writer.fieldnames})


def backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = path.with_name(f"{path.stem}.backup.display-text.{timestamp}{path.suffix}")
    shutil.copy2(path, target)
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cas-map", type=Path, required=True, help="CAS No.별 대표 한글 물질명 JSON")
    parser.add_argument("--apply", action="store_true", help="검토 결과를 로컬 제품/override JSON에 적용")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cas_map = {str(key).strip(): clean_display_text(value) for key, value in read_json(args.cas_map).items()}
    product_payload, products = read_list(PRODUCTS_PATH, "products")
    override_payload, overrides = read_list(OVERRIDES_PATH, "overrides")
    changes: list[dict[str, Any]] = []
    normalized_products = normalize_products(products, cas_map, changes)
    normalized_overrides = normalize_overrides(overrides, cas_map, changes)
    mode = "apply" if args.apply else "dry-run"
    write_report(changes, mode)
    print(json.dumps({"mode": mode, "changeCount": len(changes), "examples": changes[:30]}, ensure_ascii=False, indent=2))
    if not args.apply:
        return 0

    print(f"백업: {backup(PRODUCTS_PATH)}")
    print(f"백업: {backup(OVERRIDES_PATH)}")
    write_json(PRODUCTS_PATH, replace_list(product_payload, "products", normalized_products))
    write_json(OVERRIDES_PATH, replace_list(override_payload, "overrides", normalized_overrides))
    print(f"적용: {PRODUCTS_PATH}")
    print(f"적용: {OVERRIDES_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
