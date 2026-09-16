#!/usr/bin/env python
"""Apply extracted first-aid sections to the public product data.

extract_first_aid.py 가 만든 보고서에서 status 가 "extracted" 인 항목만
공개 데이터의 firstAid 필드에 넣는다. 글꼴이 깨졌거나 4항을 찾지 못한
제품은 건드리지 않는다. 비워 두면 화면에서 해당 구역이 나오지 않고,
작업자는 기존대로 PDF 원문을 본다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTS = ROOT / "data" / "msds.public.json"
DEFAULT_REPORT = ROOT / "reports" / "first-aid-extract.local.json"

ORDER = ("eye", "skin", "inhalation", "ingestion", "note")
MAX_ITEMS_PER_SECTION = 8
MAX_ITEM_LENGTH = 200


def tidy(items: list) -> list[str]:
    seen = []
    for item in items:
        text = " ".join(str(item or "").split())
        if not text or len(text) < 4:
            continue
        if len(text) > MAX_ITEM_LENGTH:
            text = text[:MAX_ITEM_LENGTH].rstrip() + "…"
        if text not in seen:
            seen.append(text)
        if len(seen) >= MAX_ITEMS_PER_SECTION:
            break
    return seen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply extracted first-aid data.")
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 결과만 보여 준다")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    products = json.loads(args.products.read_text(encoding="utf-8"))
    report = json.loads(args.report.read_text(encoding="utf-8"))

    by_id = {
        record["id"]: record
        for record in report.get("records", [])
        if record.get("status") == "extracted" and record.get("firstAid")
    }

    applied = 0
    skipped = 0
    for product in products:
        record = by_id.get(product.get("id"))
        if not record:
            product.pop("firstAid", None)
            skipped += 1
            continue
        cleaned = {}
        for key in ORDER:
            items = tidy(record["firstAid"].get(key) or [])
            if items:
                cleaned[key] = items
        if cleaned:
            product["firstAid"] = cleaned
            applied += 1
        else:
            product.pop("firstAid", None)
            skipped += 1

    print(f"응급조치 반영: {applied}건 / 미반영 {skipped}건 (전체 {len(products)}건)")
    if args.dry_run:
        print("dry-run 이라 파일을 쓰지 않았습니다.")
        return 0

    args.products.write_text(
        json.dumps(products, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    print(f"저장: {args.products.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
