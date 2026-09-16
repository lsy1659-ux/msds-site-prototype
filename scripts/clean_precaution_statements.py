#!/usr/bin/env python
"""Split merged 예방조치 문구 back into single statements.

일부 PDF는 2항 전체가 줄바꿈 없이 한 덩어리로 읽혔다. PP-303 GW(PU) 는
예방조치 문구 칸 하나에 1002자가 들어가 경고표지에 글씨 벽이 찍힌다.

다행히 덩어리 안에 "P280 - ..." 같은 표시가 그대로 남아 있어 P코드를
경계로 쪼갤 수 있다. 쪼갠 문구는 코드 번호에 따라 제자리 칸으로 보낸다.
P2 는 예방, P3 은 대응, P4 는 저장, P5 는 폐기다.

P코드가 하나라도 있는 제품에서 코드가 없는 줄은 목차나 다른 항목이
섞여 들어온 것이므로 걸러낸다. P코드가 아예 없는 제품은 판단 근거가
없으니 손대지 않는다. 값을 지어내지 않고 쪼개고 걸러내기만 한다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTS = ROOT / "data" / "msds.public.json"

FIELD = "precautionaryStatements"
BUCKETS = ("prevention", "response", "storage", "disposal")

PCODE = re.compile(r"P\d{3}")
# "P305 + P351 + P338 - ..." 처럼 묶인 코드도 한 문구다.
STATEMENT_START = re.compile(r"P\d{3}(?:\s*\+\s*P\d{3})*")
# 쪼갠 문구 끝에 다음 절 제목이 붙어 나온다. "...씻으시오.대응:" 처럼.
SECTION_LABEL = "예방|대응|저장|보관|폐기|기타|응급조치"
TRAILING_LABEL = re.compile(r"[.\s]*(?:" + SECTION_LABEL + r")\s*:\s*$")
TRAILING_SECTION = re.compile(r"(?<=[.])\s*(?:유해성|물리적|환경에|독성에|그\s*밖의).*$")

MERGED_MIN_LENGTH = 200
MAX_LENGTH = 160

BUCKET_BY_DIGIT = {"1": "prevention", "2": "prevention", "3": "response",
                   "4": "storage", "5": "disposal"}


def bucket_for(code: str) -> str:
    return BUCKET_BY_DIGIT.get(code[1], "prevention")


def split_merged(text: str) -> list[tuple[str, str]]:
    """덩어리를 (칸, 문구) 목록으로 쪼갠다."""
    out: list[tuple[str, str]] = []
    marks = list(STATEMENT_START.finditer(text))
    for index, mark in enumerate(marks):
        end = marks[index + 1].start() if index + 1 < len(marks) else len(text)
        piece = " ".join(text[mark.start():end].split())
        piece = TRAILING_SECTION.sub("", piece)
        piece = TRAILING_LABEL.sub("", piece)
        piece = piece.rstrip(" .,;·-")
        if not piece:
            continue
        if len(piece) > MAX_LENGTH:
            piece = piece[:MAX_LENGTH].rstrip() + "…"
        out.append((bucket_for(mark.group(0)), piece))
    return out


def tidy(groups: dict) -> tuple[dict, int, int]:
    """(정리한 칸, 쪼갠 수, 걸러낸 수)."""
    flat: list[tuple[str, str]] = []
    for name in BUCKETS:
        for value in groups.get(name) or []:
            flat.append((name, " ".join(str(value).split())))
    flat = [(name, text) for name, text in flat if text]
    if not flat:
        return groups, 0, 0

    coded = [text for _, text in flat if PCODE.search(text)]
    if not coded:
        return groups, 0, 0

    split_count = 0
    dropped = 0
    result: dict[str, list[str]] = {name: [] for name in BUCKETS}
    for name, text in flat:
        if not PCODE.search(text):
            dropped += 1
            continue
        if len(text) >= MERGED_MIN_LENGTH and len(PCODE.findall(text)) > 1:
            pieces = split_merged(text)
            if pieces:
                split_count += 1
                for target, piece in pieces:
                    result[target].append(piece)
                continue
        result[name].append(text if len(text) <= MAX_LENGTH
                            else text[:MAX_LENGTH].rstrip() + "…")

    for name in BUCKETS:
        seen = set()
        unique = []
        for text in result[name]:
            if text in seen:
                continue
            seen.add(text)
            unique.append(text)
        result[name] = unique

    merged = dict(groups)
    merged.update(result)
    return merged, split_count, dropped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean precautionary statements.")
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    products = json.loads(args.products.read_text(encoding="utf-8"))

    touched = split_total = drop_total = 0
    for product in products:
        groups = product.get(FIELD)
        if not isinstance(groups, dict):
            continue
        before = json.dumps(groups, ensure_ascii=False, sort_keys=True)
        after, splits, dropped = tidy(groups)
        if json.dumps(after, ensure_ascii=False, sort_keys=True) == before:
            continue
        product[FIELD] = after
        touched += 1
        split_total += splits
        drop_total += dropped
        name = str(product.get("productName", ""))[:28]
        counts = " / ".join(f"{k[:4]} {len(after.get(k) or [])}" for k in BUCKETS)
        print(f"  {name:30} 쪼갬 {splits} 걸러냄 {dropped} → {counts}")

    print(f"손본 제품 {touched}개 / 쪼갠 덩어리 {split_total}개 / 걸러낸 줄 {drop_total}개")

    if args.dry_run:
        print("dry-run 이라 파일을 쓰지 않았습니다.")
        return 0

    args.products.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8", newline="\n")
    print("저장 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
