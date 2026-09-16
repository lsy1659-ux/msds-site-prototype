#!/usr/bin/env python
"""Apply the re-extracted section 2 / section 15 results.

보수적으로만 반영한다.

 - 성분의 관리대상·작업환경측정·특수건강진단은 지금 비어 있는 칸만 채운다.
   기존 값은 엑셀 등록대장에서 온 확정 정보라 덮어쓰지 않는다.
 - 유해·위험 문구는 회사명이나 문서 제목이 섞인 항목만 새 추출로 갈아끼운다.
   멀쩡한 기존 문구는 손대지 않는다.
 - 새 추출이 비어 있으면 아무것도 하지 않는다. 지우는 쪽으로는 움직이지 않는다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTS = ROOT / "data" / "msds.public.json"
DEFAULT_OVERRIDES = ROOT / "data" / "msds-overrides.public.json"
DEFAULT_REPORT = ROOT / "reports" / "quality-reextract.local.json"

JUNK_LINE = re.compile(
    r"CO\.\s*,?\s*LTD|Inc\.|Corp|주식회사|㈜"
    r"|SAFETY\s*DATA\s*SHEET|물질안전보건자료"
    r"|Date\s*(prepared|revised)|작성일자|개정일자"
    r"|\d{2,4}-\d{3,4}-\d{4}|TEL|FAX",
    re.I)

FLAG_FIELDS = ("managementTarget", "workplaceMonitoringTarget", "specialHealthCheckTarget")


def normalize_name(value: str) -> str:
    return re.sub(r"[\s()\[\]{}·,，.\-_/]", "", str(value or "")).lower()


def is_dirty(items: list) -> bool:
    return any(JUNK_LINE.search(str(item)) or len(str(item)) > 120 for item in items)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply re-extracted quality data.")
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    products = json.loads(args.products.read_text(encoding="utf-8"))
    overrides = json.loads(args.overrides.read_text(encoding="utf-8"))
    report = json.loads(args.report.read_text(encoding="utf-8"))

    by_id = {r["id"]: r for r in report.get("records", []) if r.get("status") == "ok"}

    filled_flags = 0
    touched_products = set()
    for product in products:
        record = by_id.get(product.get("id"))
        if not record:
            continue
        flags = {normalize_name(name): values for name, values in (record.get("section15") or {}).items()}
        if not flags:
            continue
        for ingredient in product.get("ingredients") or []:
            match = flags.get(normalize_name(ingredient.get("chemicalName")))
            if not match:
                continue
            for field in FLAG_FIELDS:
                if field in match and not str(ingredient.get(field) or "").strip() and match[field]:
                    ingredient[field] = match[field]
                    filled_flags += 1
                    touched_products.add(product["id"])

    # 오염된 유해문구를 깨끗한 재추출본으로 교체
    by_path = {}
    for record in report.get("records", []):
        if record.get("status") == "ok":
            by_path[record["id"]] = record
    product_by_file = {p.get("fileName"): p.get("id") for p in products if p.get("fileName")}

    cleaned = 0
    for override in overrides:
        source = str(override.get("sourcePdfPath") or "")
        file_name = source.rsplit("/", 1)[-1]
        record = by_path.get(product_by_file.get(file_name, ""))
        if not record:
            continue
        section2 = record.get("section2") or {}
        fresh = section2.get("hazardStatements") or []

        current = override.get("hazardStatements") or []
        if current and is_dirty(current) and fresh:
            override["hazardStatements"] = fresh
            cleaned += 1

        ppe = override.get("ppeCandidates") or []
        if ppe and is_dirty(ppe):
            kept = [item for item in ppe if not JUNK_LINE.search(str(item)) and len(str(item)) <= 120]
            override["ppeCandidates"] = kept
            cleaned += 1

    print(f"성분 법적 플래그 채움: {filled_flags}칸 (제품 {len(touched_products)}건)")
    print(f"오염된 문구 정리: {cleaned}건")

    if args.dry_run:
        print("dry-run 이라 파일을 쓰지 않았습니다.")
        return 0

    args.products.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8", newline="\n")
    args.overrides.write_text(json.dumps(overrides, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8", newline="\n")
    print("저장 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
