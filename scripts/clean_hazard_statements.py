#!/usr/bin/env python
"""Drop non-statement lines that leaked into 유해·위험 문구.

일부 PDF는 2항 표가 한 칸으로 읽혀서 목차 제목, 제조자 주소, 성분표
CAS 행까지 유해·위험 문구 목록에 들어갔다. 경고표지에 그대로 찍히면
문구가 수십 줄이 되어 규격을 넘고, 점검에서도 잘못된 표시가 된다.

H코드가 하나라도 있는 제품은 H코드가 붙은 줄만 진짜 문구로 본다.
H코드가 아예 없는 제품은 판단 근거가 없으니 손대지 않는다. 값을
지어내지 않고 걸러내기만 한다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTS = ROOT / "data" / "msds.public.json"

FIELD = "hazardStatements"
HCODE = re.compile(r"\bH\d{3}\b")


def clean(values: list) -> tuple[list, list]:
    """(남길 줄, 걸러낸 줄)을 돌려준다."""
    lines = [" ".join(str(v).split()) for v in values or []]
    lines = [line for line in lines if line]
    coded = [line for line in lines if HCODE.search(line)]
    if not coded or len(coded) == len(lines):
        return lines, []
    dropped = [line for line in lines if not HCODE.search(line)]
    return coded, dropped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean hazard statement lists.")
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    products = json.loads(args.products.read_text(encoding="utf-8"))

    touched = 0
    removed = 0
    for product in products:
        before = product.get(FIELD) or []
        kept, dropped = clean(before)
        if not dropped:
            continue
        product[FIELD] = kept
        touched += 1
        removed += len(dropped)
        name = str(product.get("productName", ""))[:30]
        print(f"  {name:32} {len(before):3}줄 → {len(kept)}줄")
        for line in dropped[:4]:
            print(f"      걸러냄: {line[:58]}")
        if len(dropped) > 4:
            print(f"      … 외 {len(dropped) - 4}줄")

    print(f"손본 제품 {touched}개 / 걸러낸 줄 {removed}개")

    if args.dry_run:
        print("dry-run 이라 파일을 쓰지 않았습니다.")
        return 0

    args.products.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8", newline="\n")
    print("저장 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
