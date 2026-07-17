#!/usr/bin/env python
"""Apply selected product updates from a reference JSON without replacing the site dataset."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "msds.local.json"
PRESERVED_FIELDS = {
    "id",
    "fileName",
    "pdfPath",
    "relativePath",
    "sourcePdfPath",
    "sourceRelativePath",
    # 등록대장은 참고·비교용이다. 작성일과 개정일은 PDF 원문에서만 갱신한다.
    "issueDate",
    "preparationDate",
    "revisionDate",
    "isPdfAbsorbed",
    "dataSource",
}


def read_products(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("products"), list):
        return payload["products"]
    raise ValueError(f"제품 배열을 찾을 수 없습니다: {path}")


def write_products(path: Path, original_payload: Any, products: list[dict[str, Any]]) -> None:
    payload = products
    if isinstance(original_payload, dict):
        payload = {**original_payload, "products": products}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True, help="선택 업데이트에 사용할 참고 JSON")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="현재 사이트 로컬 제품 JSON")
    parser.add_argument("--file-name", action="append", required=True, help="갱신할 PDF 파일명; 여러 번 지정 가능")
    parser.add_argument("--apply", action="store_true", help="검증 후 실제 파일에 적용")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_path = args.data.resolve()
    reference_path = args.reference.resolve()
    current_payload = json.loads(data_path.read_text(encoding="utf-8"))
    current_products = read_products(data_path)
    reference_products = read_products(reference_path)
    target_names = {name.strip().casefold() for name in args.file_name}

    current_by_id = {str(item.get("id") or ""): item for item in current_products}
    reference_targets = [
        item for item in reference_products
        if str(item.get("fileName") or "").strip().casefold() in target_names
    ]
    missing_files = sorted(
        name for name in target_names
        if not any(str(item.get("fileName") or "").strip().casefold() == name for item in reference_targets)
    )
    if missing_files:
        raise ValueError(f"참고 JSON에서 파일명을 찾을 수 없습니다: {missing_files}")

    changes: list[dict[str, Any]] = []
    for reference in reference_targets:
        product_id = str(reference.get("id") or "")
        current = current_by_id.get(product_id)
        if not current:
            raise ValueError(f"현재 사이트 데이터에서 제품 ID를 찾을 수 없습니다: {product_id}")
        if str(current.get("fileName") or "").strip().casefold() != str(reference.get("fileName") or "").strip().casefold():
            raise ValueError(f"제품 ID와 파일명이 일치하지 않습니다: {product_id}")

        before = {
            "revisionDate": current.get("revisionDate"),
            "ingredientCount": len(current.get("ingredients") or []),
            "productName": current.get("productName"),
        }
        for key, value in reference.items():
            if key not in PRESERVED_FIELDS:
                current[key] = value
        after = {
            "revisionDate": current.get("revisionDate"),
            "ingredientCount": len(current.get("ingredients") or []),
            "productName": current.get("productName"),
        }
        changes.append({"id": product_id, "fileName": current.get("fileName"), "before": before, "after": after})

    print(json.dumps({"mode": "apply" if args.apply else "dry-run", "changeCount": len(changes), "changes": changes}, ensure_ascii=False, indent=2))
    if not args.apply:
        return 0

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = data_path.with_name(f"{data_path.stem}.backup.reference-update.{timestamp}{data_path.suffix}")
    shutil.copy2(data_path, backup_path)
    write_products(data_path, current_payload, current_products)
    print(f"백업: {backup_path}")
    print(f"적용: {data_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
