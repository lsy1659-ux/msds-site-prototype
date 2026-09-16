#!/usr/bin/env python
"""Extract section 2 hazard and precautionary statements from product PDFs.

공개 데이터에 유해·위험 문구가 비어 있는 제품이 54건 있다. 현장에서 그
제품을 찾으면 "무엇이 위험한지"가 화면에 뜨지 않아 PDF를 열어야 한다.

기존 추출기는 H코드(H226 …)를 정규식으로 찾는데, 코드 없이 문장만 적은
MSDS가 많아 놓친다. 여기서는 레이아웃을 보존해 읽은 뒤 2항의
"○ 유해·위험 문구", "○ 신호어" 구획을 직접 집는다.

이 스크립트는 PDF를 읽기만 하고 수정하지 않는다. 결과는 후보이며,
사람이 원문과 대조하기 전까지 확정 정보가 아니다.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

logging.getLogger("pypdf").setLevel(logging.ERROR)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTS = ROOT / "data" / "msds.public.json"
DEFAULT_REPORT = ROOT / "reports" / "hazard-statement-extract.local.json"

CORRUPTION_MARKERS = "싞늒맊홖젂핚짂갂숚렦맋핛젗벖첛얶옦젘"
CORRUPTION_RATIO = 0.005

SECTION2_START = re.compile(r"^\s*2\s*[.．]\s*유해성")
SECTION3_START = re.compile(r"^\s*3\s*[.．]\s*구성성분")

BLOCK_MARK = re.compile(r"^\s*[○●◎]\s*(.+?)\s*$")
SIGNAL_BLOCK = re.compile(r"신\s*호\s*어")
HAZARD_BLOCK = re.compile(r"유해\s*[·ㆍ∙]?\s*위험\s*문구")
VALID_SIGNALS = {"위험", "경고", "해당없음"}


def looks_corrupted(text: str) -> tuple[bool, float]:
    syllables = sum(1 for ch in text if 0 <= ord(ch) - 0xAC00 < 11172)
    if syllables < 200:
        return False, 0.0
    hits = sum(text.count(marker) for marker in CORRUPTION_MARKERS)
    return hits / syllables >= CORRUPTION_RATIO, round(hits / max(syllables, 1), 4)


def read_layout_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text(extraction_mode="layout") or "")
        except Exception:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                parts.append("")
    return "\n".join(parts)


def clean_line(line: str) -> str:
    return re.sub(r"^[-·•▪\s]+", "", line).strip()


NOT_CLASSIFIED = re.compile(r"해당\s*없음|해당사항\s*없음|해당되는\s*분류정보가\s*없음|분류되지\s*않음")

# "자료없음"은 분류 대상이 아니라는 뜻이 아니라 MSDS가 값을 적지 않았다는 뜻이다.
# 유해문구로 실으면 현장에서 안전정보로 읽히므로 버린다.
NO_DATA = re.compile(r"자료\s*없음|자료가\s*없음|정보\s*없음|정보가\s*없음|^미상$|^-+$")


def split_label_value(line: str) -> tuple[str, str]:
    """레이아웃 추출본은 라벨과 값이 공백으로 벌어져 한 줄에 같이 온다."""
    parts = re.split(r"\s{3,}", line.strip())
    if len(parts) >= 2:
        return parts[0].strip(), " ".join(parts[1:]).strip()
    return line.strip(), ""


def parse_section2(text: str) -> dict:
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if SECTION2_START.search(line)), -1)
    if start < 0:
        return {}
    end = next((i for i, line in enumerate(lines[start:], start) if SECTION3_START.search(line)), len(lines))

    hazards: list[str] = []
    signal = ""
    not_classified = False
    current = ""

    for raw in lines[start + 1:end]:
        if not raw.strip():
            continue
        cleaned = re.sub(r"^[○●◎\-·•▪\s]+", "", raw).strip()
        label, value = split_label_value(cleaned)

        if HAZARD_BLOCK.search(label):
            current = "hazard"
            if value:
                if NOT_CLASSIFIED.search(value):
                    not_classified = True
                elif not NO_DATA.search(value):
                    hazards.append(value)
                current = ""
            continue
        if SIGNAL_BLOCK.search(label):
            if value and not signal:
                signal = next((c for c in VALID_SIGNALS if c in value), "해당없음" if NOT_CLASSIFIED.search(value) else "")
            current = "signal"
            continue
        if re.match(r"^[가-하]\s*[.．]", label) or re.match(r"^\d\s*[.．]", label):
            if NOT_CLASSIFIED.search(cleaned):
                not_classified = True
            current = ""
            continue
        if label and ("예방조치" in label or "그림문자" in label):
            current = ""
            continue

        if current == "signal" and not signal:
            found = next((c for c in VALID_SIGNALS if c in cleaned), "")
            if found:
                signal = found
            elif NOT_CLASSIFIED.search(cleaned):
                signal = "해당없음"
        elif current == "hazard":
            if NOT_CLASSIFIED.search(cleaned):
                not_classified = True
                current = ""
            elif NO_DATA.search(cleaned):
                current = ""
            elif len(cleaned) >= 4:
                hazards.append(cleaned)

    codes = sorted({code.upper() for code in re.findall(r"H\d{3}", " ".join(hazards))})
    return {
        "signalWord": signal,
        "hazardStatements": hazards[:30],
        "hazardCodes": codes,
        "notClassified": not_classified and not hazards,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract section 2 hazard statements.")
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--only-missing", action="store_true",
                        help="유해·위험 문구가 비어 있는 제품만 처리한다")
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    products = json.loads(args.products.read_text(encoding="utf-8"))
    if args.only_missing:
        products = [p for p in products if not p.get("hazardStatements")]
    if args.limit:
        products = products[: args.limit]

    records = []
    stats = {"total": 0, "extracted": 0, "corrupted": 0, "empty": 0, "read_failed": 0}

    for index, product in enumerate(products, 1):
        pdf_path = ROOT / str(product.get("pdfPath") or "")
        entry = {"id": product.get("id"), "productName": product.get("productName"), "status": ""}
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
        entry["corruptionRatio"] = ratio
        if corrupted:
            entry["status"] = "font_corrupted"
            stats["corrupted"] += 1
            records.append(entry)
            continue

        parsed = parse_section2(text)
        entry.update(parsed)
        if parsed.get("hazardStatements"):
            entry["status"] = "extracted"
            stats["extracted"] += 1
        elif parsed.get("notClassified"):
            entry["status"] = "not_classified"
            stats["not_classified"] = stats.get("not_classified", 0) + 1
        else:
            entry["status"] = "not_found"
            stats["empty"] += 1
        records.append(entry)

        if index % 20 == 0:
            print(f"  {index}/{len(products)} 처리 중...", flush=True)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps({"stats": stats, "records": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")

    print("유해·위험 문구 추출 결과")
    print(f"- 대상: {stats['total']}건")
    print(f"- 추출 성공: {stats['extracted']}건")
    print(f"- 글꼴 깨짐으로 제외: {stats['corrupted']}건")
    print(f"- 원문이 \"해당없음\": {stats.get('not_classified', 0)}건")
    print(f"- 2항에서 찾지 못함: {stats['empty']}건")
    print(f"- 읽기 실패: {stats['read_failed']}건")
    print(f"- 보고서: {args.report.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
