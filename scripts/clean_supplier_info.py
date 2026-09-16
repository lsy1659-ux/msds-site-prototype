#!/usr/bin/env python
"""Trim supplier fields that swallowed the next section of the PDF.

예전 추출기가 주소 칸에 그 뒤에 오는 내용까지 통째로 담은 제품이 있다.
"그린플러스"는 주소 뒤에 긴급전화번호와 2항 유해성 분류가 한 줄로 붙어 있어
경고표지 공급자 정보 칸이 알아볼 수 없게 나온다.

주소는 주소까지만 남기고, 그 뒤에 붙은 다른 항목은 잘라낸다. 값을 지어내지
않고 자르기만 한다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTS = ROOT / "data" / "msds.public.json"

# 어느 칸에서든 다른 절이 시작되면 거기서 끊는다.
SECTION_START = (
    r"[○●◎]"
    r"|유해성\s*[·ㆍ]?\s*위험성"
    r"|그림\s*문자"
    r"|예방\s*조치"
    r"|신\s*호\s*어"
    r"|구성성분"
    r"|\s\d{1,2}\s*[.．]\s*[가-힣]"
)

# 주소 칸은 주소까지만 남긴다. 연락처나 담당부서가 뒤에 붙어 있으면 끊는다.
CUT_ADDRESS = re.compile(SECTION_START + r"|긴급\s*(연락|전화)|FAX|담당\s*부서|작성\s*부서|정보\s*제공")

# 연락처 칸에는 긴급 전화번호가 들어가야 한다. 절 제목만 보고 끊는다.
CUT_CONTACT = re.compile(SECTION_START)

CUT_RULES = {
    "supplier": CUT_CONTACT,
    "supplierAddress": CUT_ADDRESS,
    "emergencyContact": CUT_CONTACT,
}

# 값이 아니라 항목 이름만 들어간 경우.
LABEL_ONLY = {"신호어", "그림문자", "제품명", "공급자", "공급자 정보", "회사명", "주소", "-", "자료없음"}

MAX_LENGTH = 90
MAX_LENGTH_CONTACT = 120


def tidy(value: str, field: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if text in LABEL_ONLY:
        return ""
    cut = CUT_RULES[field].search(text)
    if cut and cut.start() > 0:
        text = text[:cut.start()].strip(" ,;·-")
    limit = MAX_LENGTH_CONTACT if field == "emergencyContact" else MAX_LENGTH
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean supplier fields.")
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    products = json.loads(args.products.read_text(encoding="utf-8"))

    changed = []
    for product in products:
        for field in ("supplier", "supplierAddress", "emergencyContact"):
            before = str(product.get(field) or "")
            after = tidy(before, field)
            if after != before:
                product[field] = after
                changed.append((product.get("productName", "")[:26], field, len(before), len(after)))

    print(f"손본 칸: {len(changed)}개")
    for name, field, old, new in changed[:12]:
        print(f"  {name:28} {field:18} {old:4}자 → {new}자")

    if args.dry_run:
        print("dry-run 이라 파일을 쓰지 않았습니다.")
        return 0

    args.products.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8", newline="\n")
    print("저장 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
