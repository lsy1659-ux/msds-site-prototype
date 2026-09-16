#!/usr/bin/env python
"""Extract the first-aid section (4. 응급조치 요령) from each product PDF.

현장에서 사고가 났을 때 26쪽짜리 PDF에서 4항을 찾게 하지 않으려고 만든다.

일부 PDF는 글꼴 정보가 잘못되어 한글이 다른 글자로 바뀌어 추출된다
("신발" -> "싞발"). 치환 규칙이 일관되지 않아 되돌릴 수 없으므로, 그런
PDF는 고치려 하지 않고 건너뛴다. 응급조치 문구가 깨진 채로 화면에 뜨면
없느니만 못하다.

이 스크립트는 PDF를 읽기만 하고 수정하지 않는다.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

# 폰트 경고가 수백 줄 쏟아져 결과가 묻힌다. 추출 품질과는 무관하다.
logging.getLogger("pypdf").setLevel(logging.ERROR)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTS = ROOT / "data" / "msds.public.json"
DEFAULT_REPORT = ROOT / "reports" / "first-aid-extract.local.json"

SECTION_START = re.compile(r"^\s*4\s*[.．]\s*응급조치\s*요령")
SECTION_END = re.compile(r"^\s*5\s*[.．]\s*폭발|^\s*5\s*[.．]\s*화재")

# 하위 항목 기호가 제조사마다 다르다. 가./나. 도 있고 a./b. 나 1)/2) 도 있어서
# 기호가 아니라 뒤따르는 말로 가른다.
ENUM = r"^[\s　]*(?:[가-하]|[a-eA-E]|[1-5])?\s*[.．)]?\s*"

SUBSECTIONS = [
    ("eye", re.compile(ENUM + r"눈에")),
    ("skin", re.compile(ENUM + r"피부(에|와)")),
    ("inhalation", re.compile(ENUM + r"(흡입|들이마)")),
    ("ingestion", re.compile(ENUM + r"(먹었|삼켰|섭취)")),
    ("note", re.compile(ENUM + r"(기타|의사|의료진)")),
]

PAGE_MARK = re.compile(r"^\s*\d+\s*/\s*\d+\s*$")

# 글꼴이 깨진 PDF에서 흔한 글자 대신 튀어나오는 음절들.
# 정상 문서에서는 거의 나오지 않아 깨짐 여부를 가리는 기준으로 쓴다.
# (실측: 정상 PDF 0.00% / 깨진 PDF 3.8~5.2%)
CORRUPTION_MARKERS = "싞늒맊홖젂핚짂갂숚렦맋핛젗벖첛얶옦젘"
CORRUPTION_RATIO = 0.005


def looks_corrupted(text: str) -> tuple[bool, float]:
    """글꼴 정보가 잘못된 PDF인지 판단한다.

    치환 규칙이 일관되지 않아 되돌릴 수 없으므로, 고치지 않고 걸러낸다.
    """
    syllables = sum(1 for ch in text if 0 <= ord(ch) - 0xAC00 < 11172)
    if syllables < 200:
        return False, 0.0
    hits = sum(text.count(marker) for marker in CORRUPTION_MARKERS)
    ratio = hits / syllables
    return ratio >= CORRUPTION_RATIO, round(ratio, 4)


def read_layout_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text(extraction_mode="layout") or "")
        except Exception:  # 레이아웃 추출이 안 되는 페이지는 기본 모드로
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                parts.append("")
    return "\n".join(parts)


def clean_line(line: str) -> str:
    text = line.strip()
    text = re.sub(r"^[-·•▪○]\s*", "", text)
    return text.strip()


def parse_first_aid(text: str) -> dict[str, list[str]]:
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if SECTION_START.search(line)), -1)
    if start < 0:
        return {}

    result: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines[start + 1:]:
        if SECTION_END.search(line):
            break
        if PAGE_MARK.match(line):
            continue
        matched = next((key for key, pattern in SUBSECTIONS if pattern.search(line)), None)
        if matched:
            current = matched
            result.setdefault(current, [])
            continue
        if current is None:
            continue
        value = clean_line(line)
        # 다른 절 제목이 끼어들면 수집을 멈춘다.
        if re.match(r"^\s*\d+\s*[.．]\s*\S", value):
            break
        if value and len(value) > 3:
            result[current].append(value)
    return {key: items for key, items in result.items() if items}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract first-aid sections from product PDFs.")
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--limit", type=int, default=0, help="0 이면 전체")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    products = json.loads(args.products.read_text(encoding="utf-8"))
    if args.limit:
        products = products[: args.limit]

    records = []
    stats = {"total": 0, "extracted": 0, "corrupted": 0, "no_section": 0, "read_failed": 0}

    for index, product in enumerate(products, 1):
        pdf_path = ROOT / str(product.get("pdfPath") or "")
        entry = {"id": product.get("id"), "productName": product.get("productName"),
                 "pdfPath": product.get("pdfPath"), "status": "", "firstAid": {}}
        stats["total"] += 1

        if not pdf_path.is_file():
            entry["status"] = "pdf_missing"
            stats["read_failed"] += 1
            records.append(entry)
            continue

        try:
            text = read_layout_text(pdf_path)
        except Exception as error:
            entry["status"] = "read_failed"
            entry["error"] = str(error)[:200]
            stats["read_failed"] += 1
            records.append(entry)
            continue

        corrupted, ratio = looks_corrupted(text)
        entry["rareFinalRatio"] = ratio
        if corrupted:
            entry["status"] = "font_corrupted"
            stats["corrupted"] += 1
            records.append(entry)
            continue

        first_aid = parse_first_aid(text)
        if first_aid:
            entry["status"] = "extracted"
            entry["firstAid"] = first_aid
            stats["extracted"] += 1
        else:
            entry["status"] = "section_not_found"
            stats["no_section"] += 1
        records.append(entry)

        if index % 25 == 0:
            print(f"  {index}/{len(products)} 처리 중...", flush=True)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps({"stats": stats, "records": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")

    print("응급조치 추출 결과")
    print(f"- 대상 PDF: {stats['total']}건")
    print(f"- 추출 성공: {stats['extracted']}건")
    print(f"- 글꼴 깨짐으로 제외: {stats['corrupted']}건")
    print(f"- 4항을 찾지 못함: {stats['no_section']}건")
    print(f"- 읽기 실패: {stats['read_failed']}건")
    print(f"- 보고서: {args.report.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
