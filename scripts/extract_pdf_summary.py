#!/usr/bin/env python
"""Extract review-only MSDS summary candidates from one PDF.

This script creates local override candidates only. It does not modify PDF
files, does not change the public sample data, and never marks extracted
content as reviewed.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("pdf/PN3021.pdf")
DEFAULT_OUTPUT = Path("data/msds-overrides.local.json")
CAS_RE = re.compile(r"\b\d{2,7}-\d{2}-\d\b")
DATE_RE = re.compile(r"\b(?:19|20)\d{2}[.\-/년]\s?\d{1,2}[.\-/월]\s?\d{1,2}\s?일?\b")
CONTENT_RE = re.compile(
    r"\b\d{1,3}(?:\.\d+)?\s*(?:~|–|to)\s*\d{1,3}(?:\.\d+)?\s*%?"
    r"|\b\d{1,3}(?:\.\d+)?\s+-\s+\d{1,3}(?:\.\d+)?\s*%?"
    r"|\b\d{1,3}(?:\.\d+)?\s*%"
)

GHS_PATTERNS = [
    ("explosive", "폭발성", ["폭발", "폭탄"]),
    ("flame", "인화성", ["인화", "화염", "불꽃"]),
    ("oxidizer", "산화성", ["산화"]),
    ("gas", "고압가스", ["고압가스", "가스 실린더"]),
    ("corrosion", "부식성", ["부식"]),
    ("skull", "급성독성", ["급성독성", "해골"]),
    ("exclamation", "유해/자극성", ["자극", "유해"]),
    ("health", "건강유해성", ["건강유해", "발암", "생식독성", "흡인유해"]),
    ("environment", "환경유해성", ["환경유해", "수생환경"]),
]

SECTION_MARKERS = {
    "section1": ["1. 화학제품", "화학제품과 회사"],
    "section2": ["2. 유해성", "유해성·위험성", "유해성 위험성"],
    "section3": ["3. 구성성분", "구성성분의 명칭", "구성성분"],
    "section4": ["4. 응급조치", "응급조치"],
}


def read_pdf_text(path: Path, pages: int = 0) -> tuple[str, dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - depends on environment
        return "", {
            "method": "pypdf",
            "status": "text_extract_failed",
            "error": f"pypdf_import_failed: {exc}",
            "pageCount": 0,
            "extractedPageCount": 0,
            "extractedCharacterCount": 0,
        }

    try:
        reader = PdfReader(str(path))
        total_pages = len(reader.pages)
        page_count = total_pages if pages <= 0 else min(pages, total_pages)
        chunks: list[str] = []
        extracted_pages = 0
        for page in reader.pages[:page_count]:
            text = page.extract_text() or ""
            if text.strip():
                extracted_pages += 1
            chunks.append(text)
        text = "\n".join(chunks).strip()
    except Exception as exc:
        return "", {
            "method": "pypdf",
            "status": "text_extract_failed",
            "error": str(exc),
            "pageCount": 0,
            "extractedPageCount": 0,
            "extractedCharacterCount": 0,
        }

    return text, {
        "method": "pypdf",
        "status": "text_extracted" if text else "scanned_pdf_or_image_pdf",
        "error": "",
        "pageCount": total_pages,
        "extractedPageCount": extracted_pages,
        "extractedCharacterCount": len(text),
    }


def clean_line(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    return value.strip("-ㆍ•·* ")


def clean_lines(text: str) -> list[str]:
    return [line for line in (clean_line(line) for line in text.splitlines()) if line]


def find_marker(text: str, markers: list[str], start: int = 0) -> int:
    candidates = [text.find(marker, start) for marker in markers if text.find(marker, start) >= 0]
    return min(candidates) if candidates else -1


def section_between(text: str, start_markers: list[str], end_markers: list[str]) -> str:
    start = find_marker(text, start_markers)
    if start < 0:
        return ""
    end_candidates = [text.find(marker, start + 1) for marker in end_markers if text.find(marker, start + 1) > start]
    end = min(end_candidates) if end_candidates else len(text)
    return text[start:end]


def first_label_value(lines: list[str], labels: list[str]) -> str:
    for index, line in enumerate(lines):
        for label in labels:
            if label not in line:
                continue
            match = re.search(rf"{re.escape(label)}\s*[:：]?\s*(.+)", line)
            if match:
                value = clean_line(match.group(1))
                if value and value != label:
                    return value
            if index + 1 < len(lines):
                return clean_line(lines[index + 1])
    return ""


def first_regex(lines: list[str], pattern: re.Pattern[str]) -> str:
    for line in lines:
        match = pattern.search(line)
        if match:
            return clean_line(match.group(0))
    return ""


def extract_ghs_candidates(text: str) -> list[dict[str, str]]:
    compact_text = re.sub(r"\s+", "", text)
    found: list[dict[str, str]] = []
    for code, label, keywords in GHS_PATTERNS:
        compact_keywords = [re.sub(r"\s+", "", keyword) for keyword in keywords]
        if any(keyword in text or compact_keyword in compact_text for keyword, compact_keyword in zip(keywords, compact_keywords)):
            found.append({"code": code, "label": label})
    return found


def subsection_lines(lines: list[str], start_keywords: list[str], stop_keywords: list[str]) -> list[str]:
    start_index = -1
    for index, line in enumerate(lines):
        if any(keyword in line for keyword in start_keywords):
            start_index = index + 1
            break
    if start_index < 0:
        return []

    result: list[str] = []
    for line in lines[start_index:]:
        if any(keyword in line for keyword in stop_keywords):
            break
        if len(line) >= 2:
            result.append(line)
    return unique_keep_order(result)


def unique_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = re.sub(r"\s+", "", item)
        if not item or normalized in seen:
            continue
        seen.add(normalized)
        result.append(item)
    return result


def filter_statement_candidates(lines: list[str]) -> list[str]:
    blocked = ["분류", "그림문자", "신호어", "예방조치", "해당없음", "자료없음"]
    result = [
        line for line in lines
        if not any(word in line for word in blocked) and len(line) >= 4
    ]
    return unique_keep_order(result)


def h_code_candidates(lines: list[str]) -> list[str]:
    return unique_keep_order([line for line in lines if re.search(r"\bH\d{3}\b", line)])


def split_precautions(lines: list[str]) -> dict[str, list[str]]:
    groups = {
        "prevention": [],
        "response": [],
        "storage": [],
        "disposal": [],
    }
    labels = {
        "prevention": ["예방"],
        "response": ["대응"],
        "storage": ["저장"],
        "disposal": ["폐기"],
    }
    all_label_words = [word for words in labels.values() for word in words]

    current = "prevention"
    for line in lines:
        switched = False
        for key, words in labels.items():
            if any(re.fullmatch(rf".*{word}.*", line) for word in words) and len(line) <= 12:
                current = key
                switched = True
                break
        if switched:
            continue
        if any(line.startswith(word) and len(line) <= 18 for word in all_label_words):
            continue
        if len(line) >= 4 and is_precaution_candidate(line):
            groups[current].append(line)

    return {key: unique_keep_order(value) for key, value in groups.items()}


def is_precaution_candidate(line: str) -> bool:
    action_words = ["하시오", "마시오", "피하", "착용", "보관", "폐기", "조치", "씻으시오", "받으시오"]
    return bool(re.search(r"\bP\d{3}\b", line)) or any(word in line for word in action_words)


def extract_ingredients(section3: str) -> list[dict[str, str]]:
    lines = clean_lines(section3)
    ingredients: list[dict[str, str]] = []
    for index, line in enumerate(lines):
        cas_numbers = CAS_RE.findall(line)
        if not cas_numbers:
            continue
        context = " ".join(lines[max(0, index - 1): min(len(lines), index + 2)])
        content_match = CONTENT_RE.search(context)
        chemical = clean_line(CAS_RE.sub("", line))
        chemical = clean_line(CONTENT_RE.sub("", chemical))
        chemical = re.sub(r"(CAS|No\.?|함유량|성분|명칭)", "", chemical, flags=re.IGNORECASE)
        chemical = clean_line(chemical)
        ingredients.append(
            {
                "chemicalName": chemical,
                "casNo": cas_numbers[0],
                "content": clean_line(content_match.group(0)) if content_match else "",
            }
        )
    return dedupe_ingredients(ingredients)


def dedupe_ingredients(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for item in items:
        key = (item.get("chemicalName", ""), item.get("casNo", ""))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def extract_ppe_candidates(lines: list[str]) -> list[str]:
    keywords = ["보호구", "보호장갑", "보안경", "호흡", "마스크", "보호복", "개인보호"]
    return unique_keep_order([line for line in lines if any(keyword in line for keyword in keywords)])


def build_override(pdf_path: Path, text: str, metadata: dict[str, Any]) -> dict[str, Any]:
    lines = clean_lines(text)
    section1 = section_between(text, SECTION_MARKERS["section1"], SECTION_MARKERS["section2"])
    section2 = section_between(text, SECTION_MARKERS["section2"], SECTION_MARKERS["section3"])
    section3 = section_between(text, SECTION_MARKERS["section3"], SECTION_MARKERS["section4"])
    section1_lines = clean_lines(section1)
    section2_lines = clean_lines(section2)

    hazard_lines = subsection_lines(
        section2_lines,
        ["유해·위험문구", "유해 위험문구", "유해위험문구"],
        ["예방조치문구", "예방 조치", "예방"]
    )
    precaution_lines = subsection_lines(
        section2_lines,
        ["예방조치문구", "예방 조치"],
        ["3. 구성성분", "구성성분의 명칭"]
    )

    override = {
        "match": {
            "fileName": pdf_path.name
        },
        "sourcePdfPath": f"/pdf/{pdf_path.name}",
        "extractStatus": "candidate_extracted" if metadata["status"] == "text_extracted" else metadata["status"],
        "reviewStatus": "검토필요",
        "productNameCandidate": first_label_value(section1_lines or lines, ["제품명", "제품의 명칭", "제품명칭"]),
        "supplierCandidate": first_label_value(section1_lines or lines, ["공급자", "공급업체", "제조자", "제조사", "회사명"]),
        "msdsNoCandidate": first_label_value(lines, ["MSDS번호", "MSDS No", "MSDS No."]),
        "revisionDateCandidate": first_label_value(lines, ["개정일", "최종 개정일", "작성일"]) or first_regex(lines, DATE_RE),
        "signalWordCandidate": first_label_value(section2_lines or lines, ["신호어"]),
        "ghsPictograms": extract_ghs_candidates(section2 or text),
        "hazardStatements": unique_keep_order(filter_statement_candidates(hazard_lines) + h_code_candidates(section2_lines)),
        "precautionaryStatements": split_precautions(precaution_lines),
        "ingredients": extract_ingredients(section3 or text),
        "ppeCandidates": extract_ppe_candidates(lines),
        "notes": "PDF 자동 추출 후보이며 검토 필요",
        "extractionMeta": {
            "method": metadata["method"],
            "pageCount": metadata["pageCount"],
            "extractedPageCount": metadata["extractedPageCount"],
            "extractedCharacterCount": metadata["extractedCharacterCount"],
            "textStored": False,
        }
    }
    return override


def merge_override(output_path: Path, override: dict[str, Any]) -> list[dict[str, Any]]:
    existing: list[dict[str, Any]] = []
    if output_path.exists():
        try:
            data = json.loads(output_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                existing = data
        except json.JSONDecodeError:
            existing = []

    target_file = override["match"]["fileName"]
    merged = [
        item for item in existing
        if item.get("match", {}).get("fileName") != target_file
    ]
    merged.append(override)
    return merged


def print_summary(override: dict[str, Any], output_path: Path) -> None:
    precautions = override["precautionaryStatements"]
    summary = {
        "fileName": override["match"]["fileName"],
        "extractStatus": override["extractStatus"],
        "reviewStatus": override["reviewStatus"],
        "counts": {
            "ghsPictograms": len(override["ghsPictograms"]),
            "hazardStatements": len(override["hazardStatements"]),
            "preventionStatements": len(precautions["prevention"]),
            "responseStatements": len(precautions["response"]),
            "storageStatements": len(precautions["storage"]),
            "disposalStatements": len(precautions["disposal"]),
            "ingredients": len(override["ingredients"]),
            "ppeCandidates": len(override["ppeCandidates"]),
        },
        "preview": {
            "ghsPictograms": override["ghsPictograms"][:5],
            "hazardStatements": override["hazardStatements"][:5],
            "preventionStatements": precautions["prevention"][:5],
            "responseStatements": precautions["response"][:5],
            "storageStatements": precautions["storage"][:5],
            "disposalStatements": precautions["disposal"][:5],
            "ingredients": override["ingredients"][:5],
            "ppeCandidates": override["ppeCandidates"][:5],
        },
        "outputPath": str(output_path),
        "note": "후보 추출 결과이며 검토완료 전까지 확정 정보로 사용하지 않습니다."
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract review-only MSDS summary candidates from a PDF.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="PDF file path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Local override JSON output")
    parser.add_argument("--pages", type=int, default=0, help="Pages to extract; 0 means all pages")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    text, metadata = read_pdf_text(args.input, args.pages)
    if not text:
        override = {
            "match": {"fileName": args.input.name},
            "sourcePdfPath": f"/pdf/{args.input.name}",
            "extractStatus": metadata["status"],
            "reviewStatus": "검토필요",
            "productNameCandidate": "",
            "supplierCandidate": "",
            "msdsNoCandidate": "",
            "revisionDateCandidate": "",
            "signalWordCandidate": "",
            "ghsPictograms": [],
            "hazardStatements": [],
            "precautionaryStatements": {
                "prevention": [],
                "response": [],
                "storage": [],
                "disposal": []
            },
            "ingredients": [],
            "ppeCandidates": [],
            "notes": "PDF 텍스트 추출 실패 또는 이미지 PDF로 추정되며 수동 확인 필요",
            "extractionMeta": {
                **metadata,
                "textStored": False,
            }
        }
    else:
        override = build_override(args.input, text, metadata)

    merged = merge_override(args.output, override)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print_summary(override, args.output)


if __name__ == "__main__":
    main()
