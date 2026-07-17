#!/usr/bin/env python
"""Apply PDF-authoritative dates and remove byte-for-byte duplicate product records."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from .finalize_msds_data_quality import build_pdf_index, extract_dates_from_pdf, resolve_pdf_path
except ImportError:  # 직접 스크립트로 실행할 때
    from finalize_msds_data_quality import build_pdf_index, extract_dates_from_pdf, resolve_pdf_path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "msds.local.json"
REPORT_PATH = ROOT / "reports" / "selected-pdf-reconcile.local.json"


def read_payload(path: Path) -> tuple[Any, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return payload, payload
    if isinstance(payload, dict) and isinstance(payload.get("products"), list):
        return payload, payload["products"]
    raise ValueError(f"제품 목록을 찾을 수 없습니다: {path}")


def replace_products(payload: Any, products: list[dict[str, Any]]) -> Any:
    if isinstance(payload, list):
        return products
    return {**payload, "products": products}


def normalized_file_name(value: Any) -> str:
    return str(value or "").strip().casefold()


def identity_key(product: dict[str, Any]) -> tuple[str, str, str]:
    return (
        normalized_file_name(product.get("fileName")),
        re.sub(r"\s+", "", str(product.get("productName") or "")).casefold(),
        re.sub(r"\s+", "", str(product.get("msdsNo") or "")).casefold(),
    )


def content_without_id(product: dict[str, Any]) -> str:
    comparable = {key: value for key, value in product.items() if key != "id"}
    return json.dumps(comparable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def id_score(product: dict[str, Any]) -> tuple[int, str]:
    product_id = str(product.get("id") or "")
    match = re.search(r"(\d+)$", product_id)
    return (int(match.group(1)) if match else 10**9, product_id)


def reconcile(
    products: list[dict[str, Any]],
    selected_names: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    result = deepcopy(products)
    pdf_index = build_pdf_index()
    changes: list[dict[str, Any]] = []
    errors: list[str] = []

    for file_name in sorted(selected_names):
        matches = [item for item in result if normalized_file_name(item.get("fileName")) == file_name]
        if not matches:
            errors.append(f"제품 데이터 없음: {file_name}")
            continue
        pdf_path = resolve_pdf_path(matches[0], pdf_index)
        dates = extract_dates_from_pdf(pdf_path)
        if not dates.get("issueDate") or not dates.get("revisionDate"):
            errors.append(f"PDF 날짜 추출 실패: {file_name} / {dates}")
            continue
        for product in matches:
            before = {
                "issueDate": product.get("issueDate", ""),
                "revisionDate": product.get("revisionDate", ""),
            }
            product["issueDate"] = dates["issueDate"]
            product["revisionDate"] = dates["revisionDate"]
            changes.append({
                "type": "pdf_authoritative_dates",
                "id": product.get("id", ""),
                "fileName": product.get("fileName", ""),
                "before": before,
                "after": dates,
            })

    selected_products = [
        item for item in result
        if normalized_file_name(item.get("fileName")) in selected_names
    ]
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for product in selected_products:
        groups.setdefault(identity_key(product), []).append(product)

    removed_ids: set[str] = set()
    for group in groups.values():
        if len(group) < 2:
            continue
        fingerprints = {content_without_id(item) for item in group}
        if len(fingerprints) != 1:
            errors.append(
                "중복 후보의 내용이 서로 달라 자동 통합하지 않음: "
                + ", ".join(str(item.get("id") or "") for item in group)
            )
            continue
        keeper = sorted(group, key=id_score)[0]
        duplicates = [item for item in group if item is not keeper]
        removed_ids.update(str(item.get("id") or "") for item in duplicates)
        changes.append({
            "type": "exact_duplicate_product_removed",
            "fileName": keeper.get("fileName", ""),
            "keptId": keeper.get("id", ""),
            "removedIds": [item.get("id", "") for item in duplicates],
        })

    reconciled = [item for item in result if str(item.get("id") or "") not in removed_ids]
    return reconciled, changes, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file-name", action="append", required=True, help="대상 PDF 파일명; 여러 번 지정 가능")
    parser.add_argument("--apply", action="store_true", help="백업 후 실제 local 제품 데이터에 적용")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload, products = read_payload(DATA_PATH)
    selected_names = {normalized_file_name(value) for value in args.file_name}
    reconciled, changes, errors = reconcile(products, selected_names)
    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "mode": "apply" if args.apply else "dry-run",
        "productCountBefore": len(products),
        "productCountAfter": len(reconciled),
        "changes": changes,
        "errors": errors,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        return 1
    if not args.apply:
        return 0

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = DATA_PATH.with_name(f"{DATA_PATH.stem}.backup.pdf-date-reconcile.{timestamp}{DATA_PATH.suffix}")
    shutil.copy2(DATA_PATH, backup)
    DATA_PATH.write_text(
        json.dumps(replace_products(payload, reconciled), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"백업: {backup}")
    print(f"적용: {DATA_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
