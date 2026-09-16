#!/usr/bin/env python
"""Re-extract section 2 and section 15 to repair auto-extracted data quality.

예전 추출기는 뒤섞여 나온 텍스트에 정규식을 걸어서, 회사명과 문서 제목이
유해·위험 문구로 올라오거나 한 문단이 통째로 보호구 후보가 되는 일이 있었다.
레이아웃을 보존해 읽으면 절과 구획이 그대로 잡혀서 이런 오염이 사라진다.

두 가지를 다시 만든다.

 - 2항: 신호어와 유해·위험 문구. 구획 밖의 줄은 담지 않는다.
 - 15항: 성분별 작업환경측정·특수건강진단·관리대상 해당 여부.
   지금은 성분 1,743건 중 1,040건이 화면에 "미확인"으로 뜬다.

PDF는 읽기만 한다. 결과는 보고서로만 남기고, 반영은 apply 쪽에서 한다.
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
DEFAULT_REPORT = ROOT / "reports" / "quality-reextract.local.json"

CORRUPTION_MARKERS = "싞늒맊홖젂핚짂갂숚렦맋핛젗벖첛얶옦젘"
CORRUPTION_RATIO = 0.005

SEC2 = re.compile(r"^\s*2\s*[.．]\s*유해성")
SEC3 = re.compile(r"^\s*3\s*[.．]\s*구성성분")
SEC15 = re.compile(r"^\s*15\s*[.．]\s*법적")
SEC16 = re.compile(r"^\s*16\s*[.．]")

SIGNAL_LABEL = re.compile(r"신\s*호\s*어")
HAZARD_LABEL = re.compile(r"유해\s*[·ㆍ∙]?\s*위험\s*문구")
BLOCK_LABEL = re.compile(r"^[○●◎]\s*(.+)")
VALID_SIGNALS = ("위험", "경고")

NOT_CLASSIFIED = re.compile(r"해당\s*없음|해당사항\s*없음|해당되는\s*분류정보가\s*없음|분류되지\s*않음")
NO_DATA = re.compile(r"자료\s*없음|자료가\s*없음|정보\s*없음|정보가\s*없음")

# 유해·위험 문구로 보기 어려운 줄. 회사 정보나 문서 머리글이 섞여 들어온다.
JUNK_LINE = re.compile(
    r"CO\.\s*,?\s*LTD|Inc\.|Corp|주식회사|㈜"
    r"|SAFETY\s*DATA\s*SHEET|물질안전보건자료"
    r"|Date\s*(prepared|revised)|작성일자|개정일자"
    r"|\d{2,4}-\d{3,4}-\d{4}|TEL|FAX",
    re.I)

FLAG_BLOCKS = [
    ("workplaceMonitoringTarget", re.compile(r"작업\s*환경\s*측정")),
    ("specialHealthCheckTarget", re.compile(r"특수\s*건강\s*진단|특수건강검진")),
    ("managementTarget", re.compile(r"관리\s*대상\s*유해\s*물질|관리대상물질")),
]

APPLICABLE = re.compile(r"해당\s*됨|해당함")
NOT_APPLICABLE = re.compile(r"해당\s*없음|해당\s*안\s*됨")
SUBSTANCE_IN_BRACKET = re.compile(r"\[([^\]]+)\]")
SUBSTANCE_IN_PAREN = re.compile(r"\(([^)]+)\)\s*$")


def looks_corrupted(text: str) -> bool:
    syllables = sum(1 for ch in text if 0 <= ord(ch) - 0xAC00 < 11172)
    if syllables < 200:
        return False
    hits = sum(text.count(marker) for marker in CORRUPTION_MARKERS)
    return hits / syllables >= CORRUPTION_RATIO


def read_layout_text(path: Path) -> str:
    from pypdf import PdfReader

    parts = []
    for page in PdfReader(str(path)).pages:
        try:
            parts.append(page.extract_text(extraction_mode="layout") or "")
        except Exception:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                parts.append("")
    return "\n".join(parts)


def slice_section(lines: list[str], start_pattern: re.Pattern, end_pattern: re.Pattern) -> list[str]:
    start = next((i for i, line in enumerate(lines) if start_pattern.search(line)), -1)
    if start < 0:
        return []
    end = next((i for i, line in enumerate(lines[start + 1:], start + 1) if end_pattern.search(line)), len(lines))
    return lines[start + 1:end]


def split_label_value(line: str) -> tuple[str, str]:
    parts = re.split(r"\s{3,}", line.strip())
    if len(parts) >= 2:
        return parts[0].strip(), " ".join(parts[1:]).strip()
    return line.strip(), ""


def parse_section2(lines: list[str]) -> dict:
    hazards: list[str] = []
    signal = ""
    not_classified = False
    current = ""

    for raw in lines:
        if not raw.strip():
            continue
        cleaned = re.sub(r"^[○●◎\-·•▪\s]+", "", raw).strip()
        label, value = split_label_value(cleaned)

        if HAZARD_LABEL.search(label):
            current = "hazard"
            if value:
                if NOT_CLASSIFIED.search(value):
                    not_classified = True
                elif not NO_DATA.search(value) and not JUNK_LINE.search(value):
                    hazards.append(value)
                current = ""
            continue
        if SIGNAL_LABEL.search(label):
            if value and not signal:
                signal = next((s for s in VALID_SIGNALS if s in value), "")
            current = "signal"
            continue
        if BLOCK_LABEL.match(raw.strip()) or re.match(r"^[가-하]\s*[.．]", label) or re.match(r"^\d{1,2}\s*[.．]", label):
            current = ""
            continue

        if current == "signal" and not signal:
            signal = next((s for s in VALID_SIGNALS if s in cleaned), "")
        elif current == "hazard":
            if NOT_CLASSIFIED.search(cleaned):
                not_classified = True
                current = ""
            elif NO_DATA.search(cleaned) or JUNK_LINE.search(cleaned):
                current = ""
            elif 4 <= len(cleaned) <= 120:
                hazards.append(cleaned)

    return {
        "signalWord": signal,
        "hazardStatements": hazards[:30],
        "notClassified": not_classified and not hazards,
    }


def substance_from_line(line: str) -> str:
    bracket = SUBSTANCE_IN_BRACKET.search(line)
    if bracket:
        return bracket.group(1).strip()
    paren = SUBSTANCE_IN_PAREN.search(line.strip())
    if paren:
        text = paren.group(1).strip()
        text = re.sub(r"^\d+(\.\d+)?\s*%\s*이상\s*함유\w*\s*", "", text)
        return text.strip()
    return ""


# "1) 자일렌" 처럼 물질을 번호로 묶고 그 아래에 항목별 값을 적는 형식.
NUMBERED_SUBSTANCE = re.compile(r"^\(?(\d{1,2})\s*[)．.]\s*(\S.*)$")
# 농도 조건이 적혀 있으면 규제 대상이라는 뜻이다. "1% 이상 일때" 같은 표기.
CONCENTRATION = re.compile(r"\d+(\.\d+)?\s*%\s*이상")


def flag_value(text: str) -> str | None:
    """항목 값이 대상이면 ○, 아니면 빈 문자열, 판단 불가면 None."""
    if NOT_APPLICABLE.search(text):
        return ""
    if APPLICABLE.search(text) or CONCENTRATION.search(text):
        return "○"
    return None


def parse_section15(lines: list[str]) -> dict[str, dict[str, str]]:
    """성분 이름별로 규제 대상 여부를 모은다.

    제조사마다 형식이 달라 두 가지를 함께 읽는다.
      - 항목을 먼저 쓰고 물질을 줄마다 나열하는 형식
      - 물질을 번호로 묶고 그 아래에 항목을 적는 형식
    """
    flags: dict[str, dict[str, str]] = {}
    block_key = ""
    substance = ""

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue

        block = BLOCK_LABEL.match(stripped)
        if block:
            block_key = next((key for key, pattern in FLAG_BLOCKS if pattern.search(block.group(1))), "")
            substance = ""
            continue
        if re.match(r"^[가-하]\s*[.．]", stripped):
            block_key = ""
            substance = ""
            continue

        numbered = NUMBERED_SUBSTANCE.match(stripped)
        if numbered and ":" not in numbered.group(2):
            substance = numbered.group(2).strip()
            block_key = ""
            continue

        if substance and ":" in stripped:
            label, _, value = stripped.partition(":")
            key = next((k for k, pattern in FLAG_BLOCKS if pattern.search(label)), "")
            if key:
                decided = flag_value(value)
                if decided is not None:
                    flags.setdefault(substance, {})[key] = decided
            continue

        if block_key:
            name = substance_from_line(stripped)
            if not name:
                continue
            decided = flag_value(stripped)
            if decided is not None:
                flags.setdefault(name, {})[block_key] = decided

    return flags


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Re-extract section 2 and 15 for data quality.")
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    products = json.loads(args.products.read_text(encoding="utf-8"))
    if args.limit:
        products = products[: args.limit]

    records = []
    stats = {"total": 0, "section2": 0, "section15": 0, "corrupted": 0, "failed": 0}

    for index, product in enumerate(products, 1):
        pdf_path = ROOT / str(product.get("pdfPath") or "")
        entry = {"id": product.get("id"), "productName": product.get("productName")}
        stats["total"] += 1

        if not pdf_path.is_file():
            entry["status"] = "pdf_missing"
            stats["failed"] += 1
            records.append(entry)
            continue
        try:
            text = read_layout_text(pdf_path)
        except Exception as error:
            entry["status"] = "read_failed"
            entry["error"] = str(error)[:160]
            stats["failed"] += 1
            records.append(entry)
            continue

        if looks_corrupted(text):
            entry["status"] = "font_corrupted"
            stats["corrupted"] += 1
            records.append(entry)
            continue

        lines = text.split("\n")
        section2 = parse_section2(slice_section(lines, SEC2, SEC3))
        section15 = parse_section15(slice_section(lines, SEC15, SEC16))

        entry["status"] = "ok"
        entry["section2"] = section2
        entry["section15"] = section15
        if section2.get("hazardStatements") or section2.get("notClassified"):
            stats["section2"] += 1
        if section15:
            stats["section15"] += 1
        records.append(entry)

        if index % 25 == 0:
            print(f"  {index}/{len(products)} 처리 중...", flush=True)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps({"stats": stats, "records": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n")

    print("품질 재추출 결과")
    print(f"- 대상: {stats['total']}건")
    print(f"- 2항(신호어·유해문구) 확보: {stats['section2']}건")
    print(f"- 15항(성분 법적 플래그) 확보: {stats['section15']}건")
    print(f"- 글꼴 깨짐 제외: {stats['corrupted']}건")
    print(f"- 읽기 실패: {stats['failed']}건")
    print(f"- 보고서: {args.report.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
