#!/usr/bin/env python
"""Extract review-only MSDS summary candidates from PDF files.

This script is intentionally PDF-first. It can process all PDFs, only
Excel-linked PDFs, only Excel-missing PDFs, or only PDFs that do not yet have
local overrides. Extracted values are candidates only; reviewStatus remains
review-required unless an existing reviewed status is being preserved.

The script never modifies, deletes, moves, or renames PDF files.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("pdf/PN3021.pdf")
DEFAULT_PDF_DIR = Path("pdf")
DEFAULT_OUTPUT = Path("data/msds-overrides.local.json")
DEFAULT_INVENTORY = Path("data/pdf-inventory.local.json")
DEFAULT_REGISTRATION_QUEUE = Path("data/pdf-registration-queue.local.json")
DEFAULT_REPORT_JSON = Path("reports/pdf-summary-batch-extract.local.json")
DEFAULT_REPORT_CSV = Path("reports/pdf-summary-batch-extract.local.csv")
logging.getLogger("pypdf").setLevel(logging.CRITICAL)
PDF_IMPORT_ERROR = ""

try:
    from pypdf import PdfReader
except Exception as exc:  # pragma: no cover - depends on local env
    PdfReader = None  # type: ignore[assignment]
    PDF_IMPORT_ERROR = str(exc)

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

LOCKED_REVIEW_STATUSES = {"검토완료", "수정필요", "제외"}
GENERATED_NOTES = {
    "PDF 자동 추출 후보이며 검토 필요",
    "PDF 텍스트 추출 실패 또는 이미지 PDF로 추정되며 수동 확인 필요",
}
NON_MSDS_EXCLUDE_REASONS = {
    "비MSDS",
    "QR코드/안내문",
    "카탈로그/기타자료",
    "카탈로그",
    "시험성적서",
    "인증서",
    "기타",
}
FAILED_EXTRACT_STATUSES = {
    "text_extract_failed",
    "scanned_pdf_or_image_pdf",
    "manual_review_required",
    "pypdf_import_failed",
}


@dataclass
class PdfTarget:
    path: Path
    file_name: str
    relative_path: str
    source_pdf_path: str
    pdf_registration_type: str
    excel_product_matched: bool
    queue_review_decision: str


def normalize_path(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip()


def read_json_list(path: Path, list_key: str | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if list_key and isinstance(data, dict) and isinstance(data.get(list_key), list):
        return [item for item in data[list_key] if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("items", "overrides", "queue", "products"):
            if isinstance(data.get(key), list):
                return [item for item in data[key] if isinstance(item, dict)]
    return []


def read_pdf_text(path: Path, pages: int = 0) -> tuple[str, dict[str, Any]]:
    if PdfReader is None:
        return "", {
            "method": "pypdf",
            "status": "text_extract_failed",
            "error": f"pypdf_import_failed: {PDF_IMPORT_ERROR}",
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


def has_no_ghs_label_element(text: str) -> bool:
    compact = re.sub(r"\s+", "", text).lower()
    no_label_markers = [
        "그림문자해당없음",
        "심볼(문자)해당없음",
        "심볼해당없음",
        "신호어해당없음",
        "유해위험문구해당없음",
        "유해▪위험문구해당없음",
        "유해화학물질로분류되지않음",
        "notclassified",
        "noghslabelelement",
        "notapplicable",
    ]
    return any(marker in compact for marker in no_label_markers)


def extract_ghs_candidates(text: str) -> list[dict[str, str]]:
    if has_no_ghs_label_element(text):
        return []

    compact_text = re.sub(r"\s+", "", text)
    found: list[dict[str, str]] = []
    for code, label, keywords in GHS_PATTERNS:
        compact_keywords = [re.sub(r"\s+", "", keyword) for keyword in keywords]
        if any(keyword in text or compact_keyword in compact_text for keyword, compact_keyword in zip(keywords, compact_keywords)):
            found.append({"code": code, "label": label})
    return found


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


def filter_statement_candidates(lines: list[str]) -> list[str]:
    blocked = ["분류", "그림문자", "신호어", "예방조치", "해당없음", "자료없음"]
    return unique_keep_order([line for line in lines if not any(word in line for word in blocked) and len(line) >= 4])


def h_code_candidates(lines: list[str]) -> list[str]:
    return unique_keep_order([line for line in lines if re.search(r"\bH\d{3}\b", line)])


def is_precaution_candidate(line: str) -> bool:
    action_words = ["하시오", "마시오", "피하", "착용", "보관", "폐기", "조치", "씻으시오", "받으시오"]
    return bool(re.search(r"\bP\d{3}\b", line)) or any(word in line for word in action_words)


def split_precautions(lines: list[str]) -> dict[str, list[str]]:
    groups = {"prevention": [], "response": [], "storage": [], "disposal": []}
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


def source_pdf_path(relative_path: str) -> str:
    return f"/pdf/{normalize_path(relative_path)}"


def build_override(target: PdfTarget, text: str, metadata: dict[str, Any]) -> dict[str, Any]:
    lines = clean_lines(text)
    section1 = section_between(text, SECTION_MARKERS["section1"], SECTION_MARKERS["section2"])
    section2 = section_between(text, SECTION_MARKERS["section2"], SECTION_MARKERS["section3"])
    section3 = section_between(text, SECTION_MARKERS["section3"], SECTION_MARKERS["section4"])
    section1_lines = clean_lines(section1)
    section2_lines = clean_lines(section2)

    hazard_lines = subsection_lines(
        section2_lines,
        ["유해·위험문구", "유해 위험문구", "유해위험문구"],
        ["예방조치문구", "예방 조치", "예방"],
    )
    precaution_lines = subsection_lines(
        section2_lines,
        ["예방조치문구", "예방 조치"],
        ["3. 구성성분", "구성성분의 명칭"],
    )

    return {
        "match": {
            "fileName": target.file_name,
            "relativePath": target.relative_path,
        },
        "sourcePdfPath": target.source_pdf_path,
        "sourceRelativePath": target.relative_path,
        "pdfRegistrationType": target.pdf_registration_type,
        "excelProductMatched": target.excel_product_matched,
        "queueReviewDecision": target.queue_review_decision,
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
        },
    }


def build_failed_override(target: PdfTarget, metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "match": {
            "fileName": target.file_name,
            "relativePath": target.relative_path,
        },
        "sourcePdfPath": target.source_pdf_path,
        "sourceRelativePath": target.relative_path,
        "pdfRegistrationType": target.pdf_registration_type,
        "excelProductMatched": target.excel_product_matched,
        "queueReviewDecision": target.queue_review_decision,
        "extractStatus": metadata["status"],
        "reviewStatus": "검토필요",
        "productNameCandidate": "",
        "supplierCandidate": "",
        "msdsNoCandidate": "",
        "revisionDateCandidate": "",
        "signalWordCandidate": "",
        "ghsPictograms": [],
        "hazardStatements": [],
        "precautionaryStatements": {"prevention": [], "response": [], "storage": [], "disposal": []},
        "ingredients": [],
        "ppeCandidates": [],
        "notes": "PDF 텍스트 추출 실패 또는 이미지 PDF로 추정되며 수동 확인 필요",
        "extractionMeta": {**metadata, "manualReviewRequired": True, "textStored": False},
    }


def build_override_for_target(target: PdfTarget, pages: int) -> dict[str, Any]:
    text, metadata = read_pdf_text(target.path, pages)
    if text:
        return build_override(target, text, metadata)
    return build_failed_override(target, metadata)


def override_key(item: dict[str, Any]) -> str:
    match = item.get("match") if isinstance(item.get("match"), dict) else {}
    relative_path = normalize_path(match.get("relativePath") or item.get("sourceRelativePath"))
    file_name = str(match.get("fileName") or "").strip()
    return relative_path or file_name


def override_file_name(item: dict[str, Any]) -> str:
    match = item.get("match") if isinstance(item.get("match"), dict) else {}
    file_name = str(match.get("fileName") or "").strip()
    if file_name:
        return file_name
    source_path = normalize_path(item.get("sourcePdfPath"))
    return Path(source_path).name if source_path else ""


def is_failed_override(item: dict[str, Any]) -> bool:
    status = str(item.get("extractStatus") or "").strip().lower()
    notes = str(item.get("notes") or "").lower()
    meta = item.get("extractionMeta") if isinstance(item.get("extractionMeta"), dict) else {}
    error = str(meta.get("error") or "").lower()
    return (
        status in FAILED_EXTRACT_STATUSES
        or "failed" in status
        or "pypdf_import_failed" in notes
        or "pypdf_import_failed" in error
    )


def read_existing_overrides(output_path: Path) -> list[dict[str, Any]]:
    return read_json_list(output_path, "overrides")


def merge_override_item(existing_item: dict[str, Any] | None, override: dict[str, Any]) -> tuple[dict[str, Any], bool, bool]:
    if not existing_item:
        return override, False, False

    existing_status = existing_item.get("reviewStatus")
    locked = existing_status in LOCKED_REVIEW_STATUSES
    generated_fields = {
        "productNameCandidate",
        "supplierCandidate",
        "msdsNoCandidate",
        "revisionDateCandidate",
        "signalWordCandidate",
        "ghsPictograms",
        "hazardStatements",
        "precautionaryStatements",
        "ingredients",
        "ppeCandidates",
    }

    if locked:
        merged = {**override, **existing_item}
        merged["match"] = {**override.get("match", {}), **existing_item.get("match", {})}
        for field in ("sourcePdfPath", "sourceRelativePath", "pdfRegistrationType", "excelProductMatched", "queueReviewDecision", "extractStatus", "extractionMeta"):
            if field in override:
                merged[field] = override[field]
        for field in generated_fields:
            if field in existing_item:
                merged[field] = existing_item[field]
    else:
        merged = {**existing_item, **override}
        merged["match"] = {**existing_item.get("match", {}), **override.get("match", {})}

    for key, value in existing_item.items():
        if key.startswith("manual") or key.startswith("reviewed"):
            merged[key] = value

    merged["reviewStatus"] = existing_status or override.get("reviewStatus", "검토필요")

    existing_notes = str(existing_item.get("notes") or "").strip()
    if existing_notes and existing_notes not in GENERATED_NOTES:
        merged["notes"] = existing_notes

    return merged, True, locked or bool(existing_status)


def merge_overrides(output_path: Path, overrides: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    existing = read_existing_overrides(output_path)
    by_key = {override_key(item): item for item in existing if override_key(item)}
    by_file = {override_file_name(item): item for item in existing if override_file_name(item)}
    original_order = [override_key(item) for item in existing if override_key(item)]

    stats = {"created": 0, "updated": 0, "reviewStatusPreserved": 0}
    new_order: list[str] = []

    for override in overrides:
        target_key = override_key(override)
        file_name = override_file_name(override)
        existing_item = by_key.get(target_key) or by_file.get(file_name)
        merged, existed, preserved_status = merge_override_item(existing_item, override)
        if existed:
            stats["updated"] += 1
        else:
            stats["created"] += 1
            new_order.append(target_key)
        if preserved_status:
            stats["reviewStatusPreserved"] += 1
        by_key[target_key] = merged

    merged_items = [by_key[key] for key in original_order if key in by_key]
    merged_items.extend(by_key[key] for key in new_order if key in by_key and key not in original_order)
    return merged_items, stats


def queue_items_by_key(queue_path: Path) -> dict[str, dict[str, Any]]:
    queue = read_json_list(queue_path)
    lookup: dict[str, dict[str, Any]] = {}
    for item in queue:
        relative_path = normalize_path(item.get("relativePath"))
        file_name = str(item.get("fileName") or "").strip()
        if relative_path:
            lookup[relative_path] = item
        if file_name and file_name not in lookup:
            lookup[file_name] = item
    return lookup


def queue_review_decision(queue_item: dict[str, Any] | None) -> str:
    if not queue_item:
        return ""
    return str(queue_item.get("reviewDecision") or "").strip()


def is_non_msds_excluded(queue_item: dict[str, Any] | None) -> bool:
    if not queue_item:
        return False
    decision = str(queue_item.get("reviewDecision") or "").strip()
    reason = str(queue_item.get("excludeReason") or "").strip()
    if decision != "제외":
        return False
    return (
        reason in NON_MSDS_EXCLUDE_REASONS
        or "QR" in reason.upper()
        or "안내" in reason
        or "비MSDS" in reason
    )


def inventory_items(inventory_path: Path) -> list[dict[str, Any]]:
    data = {}
    if inventory_path.exists():
        data = json.loads(inventory_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return [item for item in data["items"] if isinstance(item, dict)]
    return []


def make_target_from_path(pdf_path: Path, pdf_dir: Path, queue_lookup: dict[str, dict[str, Any]], inventory_item: dict[str, Any] | None = None) -> PdfTarget:
    try:
        relative_path = normalize_path(pdf_path.relative_to(pdf_dir))
    except ValueError:
        relative_path = normalize_path(pdf_path.name)

    file_name = pdf_path.name
    inventory_status = str((inventory_item or {}).get("inventoryStatus") or "")
    excel_missing = inventory_status == "excel_missing_pdf"
    registration_type = "excel_missing_pdf" if excel_missing else "excel_linked"
    matched = not excel_missing
    queue_item = queue_lookup.get(relative_path) or queue_lookup.get(file_name)
    decision = queue_review_decision(queue_item)

    return PdfTarget(
        path=pdf_path,
        file_name=file_name,
        relative_path=relative_path,
        source_pdf_path=source_pdf_path(relative_path),
        pdf_registration_type=registration_type,
        excel_product_matched=matched,
        queue_review_decision=decision,
    )


def discover_targets(args: argparse.Namespace, existing_overrides: list[dict[str, Any]]) -> tuple[list[PdfTarget], int]:
    queue_lookup = queue_items_by_key(args.registration_queue)
    existing_keys = {override_key(item) for item in existing_overrides if override_key(item)}
    existing_files = {override_file_name(item) for item in existing_overrides if override_file_name(item)}

    inventory = inventory_items(args.inventory)
    inventory_by_relative = {normalize_path(item.get("relativePath")): item for item in inventory if item.get("relativePath")}
    inventory_by_file = {str(item.get("fileName") or ""): item for item in inventory if item.get("fileName")}

    if args.retry_failed:
        retry_paths: list[Path] = []
        for item in existing_overrides:
            if not is_failed_override(item):
                continue
            relative_path = normalize_path(item.get("sourceRelativePath") or item.get("match", {}).get("relativePath"))
            if relative_path:
                retry_paths.append(args.pdf_dir / Path(relative_path))
                continue
            file_name = override_file_name(item)
            if file_name:
                inventory_item = inventory_by_file.get(file_name)
                if inventory_item and inventory_item.get("relativePath"):
                    retry_paths.append(args.pdf_dir / Path(normalize_path(inventory_item["relativePath"])))
                else:
                    retry_paths.append(args.pdf_dir / file_name)
        pdf_paths = retry_paths
    elif args.input:
        pdf_paths = [args.input]
    elif inventory and args.pdf_dir == DEFAULT_PDF_DIR:
        pdf_paths = []
        for item in inventory:
            relative = normalize_path(item.get("relativePath"))
            if relative:
                pdf_paths.append(args.pdf_dir / Path(relative))
    else:
        pdf_paths = sorted(args.pdf_dir.rglob("*.pdf")) if args.pdf_dir.exists() else []

    targets: list[PdfTarget] = []
    for pdf_path in pdf_paths:
        if not pdf_path.exists() or not pdf_path.is_file():
            continue
        item = inventory_by_relative.get(normalize_path(pdf_path.relative_to(args.pdf_dir))) if args.pdf_dir else None
        if item is None:
            item = inventory_by_file.get(pdf_path.name)
        target = make_target_from_path(pdf_path, args.pdf_dir, queue_lookup, item)
        queue_item = queue_lookup.get(target.relative_path) or queue_lookup.get(target.file_name)

        if args.skip_excluded and is_non_msds_excluded(queue_item):
            continue

        if args.folder:
            folder = normalize_path(args.folder).strip("/")
            if not target.relative_path.startswith(folder):
                continue

        if args.target == "excel-linked" and target.pdf_registration_type != "excel_linked":
            continue
        if args.target == "excel-missing" and target.pdf_registration_type != "excel_missing_pdf":
            continue
        if args.only_missing_overrides and (
            target.relative_path in existing_keys
            or target.file_name in existing_files
        ):
            continue

        targets.append(target)

    targets = sorted(targets, key=lambda item: item.relative_path)
    total_after_filters = len(targets)
    if args.limit and args.limit > 0:
        targets = targets[: args.limit]
    return targets, total_after_filters


def override_counts(override: dict[str, Any]) -> dict[str, int]:
    precautions = override.get("precautionaryStatements") if isinstance(override.get("precautionaryStatements"), dict) else {}
    return {
        "ghsPictograms": len(override.get("ghsPictograms", [])),
        "hazardStatements": len(override.get("hazardStatements", [])),
        "preventionStatements": len(precautions.get("prevention", [])),
        "responseStatements": len(precautions.get("response", [])),
        "storageStatements": len(precautions.get("storage", [])),
        "disposalStatements": len(precautions.get("disposal", [])),
        "ingredients": len(override.get("ingredients", [])),
        "ppeCandidates": len(override.get("ppeCandidates", [])),
    }


def is_text_success(override: dict[str, Any]) -> bool:
    return override.get("extractStatus") == "candidate_extracted"


def needs_manual_review(override: dict[str, Any]) -> bool:
    return override.get("reviewStatus") == "검토필요" or override.get("extractStatus") in {
        "text_extract_failed",
        "scanned_pdf_or_image_pdf",
        "manual_review_required",
    }


def build_batch_report(
    targets: list[PdfTarget],
    overrides: list[dict[str, Any]],
    merge_stats: dict[str, int],
    total_pdf_count: int,
    filtered_target_count: int,
    args: argparse.Namespace,
) -> dict[str, Any]:
    text_success = [item for item in overrides if is_text_success(item)]
    text_failed = [item for item in overrides if not is_text_success(item)]
    manual_review = [item for item in overrides if needs_manual_review(item)]
    ghs = [item for item in overrides if override_counts(item)["ghsPictograms"] > 0]
    hazards = [item for item in overrides if override_counts(item)["hazardStatements"] > 0]
    precautions = [
        item for item in overrides
        if override_counts(item)["preventionStatements"]
        or override_counts(item)["responseStatements"]
        or override_counts(item)["storageStatements"]
        or override_counts(item)["disposalStatements"]
    ]
    ingredients = [item for item in overrides if override_counts(item)["ingredients"] > 0]
    excel_linked = [target for target in targets if target.pdf_registration_type == "excel_linked"]
    excel_missing = [target for target in targets if target.pdf_registration_type == "excel_missing_pdf"]

    return {
        "inputs": {
            "pdfDir": str(args.pdf_dir),
            "output": str(args.output),
            "target": args.target,
            "onlyMissingOverrides": args.only_missing_overrides,
            "limit": args.limit,
            "folder": args.folder,
        },
        "summary": {
            "totalPdfCount": total_pdf_count,
            "filteredTargetCountBeforeLimit": filtered_target_count,
            "processedPdfCount": len(targets),
            "excelLinkedProcessedCount": len(excel_linked),
            "excelMissingProcessedCount": len(excel_missing),
            "textExtractSuccessCount": len(text_success),
            "textExtractFailedCount": len(text_failed),
            "ghsCandidatePdfCount": len(ghs),
            "hazardStatementPdfCount": len(hazards),
            "precautionStatementPdfCount": len(precautions),
            "ingredientCandidatePdfCount": len(ingredients),
            "newOverrideCreatedCount": merge_stats["created"],
            "existingOverrideUpdatedCount": merge_stats["updated"],
            "reviewStatusPreservedCount": merge_stats["reviewStatusPreserved"],
            "reviewRequiredOverrideCount": len(manual_review),
            "manualReviewRequiredPdfCount": len(manual_review),
            "retryCandidateCount": filtered_target_count if args.retry_failed else 0,
            "retrySuccessCount": len(text_success) if args.retry_failed else 0,
            "retryFailureCount": len(text_failed) if args.retry_failed else 0,
            "retryStillFailedCount": len(text_failed) if args.retry_failed else 0,
            "retryRecoveredCount": len(text_success) if args.retry_failed else 0,
        },
        "items": [
            {
                "fileName": target.file_name,
                "relativePath": target.relative_path,
                "pdfRegistrationType": target.pdf_registration_type,
                "excelProductMatched": target.excel_product_matched,
                "queueReviewDecision": target.queue_review_decision,
                "extractStatus": override.get("extractStatus", ""),
                "reviewStatus": override.get("reviewStatus", ""),
                "counts": override_counts(override),
            }
            for target, override in zip(targets, overrides)
        ],
        "examples": [
            {
                "fileName": target.file_name,
                "relativePath": target.relative_path,
                "pdfRegistrationType": target.pdf_registration_type,
                "extractStatus": override.get("extractStatus", ""),
                "reviewStatus": override.get("reviewStatus", ""),
                "counts": override_counts(override),
            }
            for target, override in list(zip(targets, overrides))[:5]
        ],
        "notes": [
            "Original PDF text is not stored in this report.",
            "Extracted values are candidates and require review.",
        ],
    }


def write_report_files(report: dict[str, Any], json_path: Path, csv_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "fileName",
                "relativePath",
                "pdfRegistrationType",
                "excelProductMatched",
                "queueReviewDecision",
                "extractStatus",
                "reviewStatus",
                "ghsPictograms",
                "hazardStatements",
                "preventionStatements",
                "responseStatements",
                "storageStatements",
                "disposalStatements",
                "ingredients",
                "ppeCandidates",
            ],
        )
        writer.writeheader()
        for item in report["items"]:
            writer.writerow({
                "fileName": item["fileName"],
                "relativePath": item["relativePath"],
                "pdfRegistrationType": item["pdfRegistrationType"],
                "excelProductMatched": item["excelProductMatched"],
                "queueReviewDecision": item["queueReviewDecision"],
                "extractStatus": item["extractStatus"],
                "reviewStatus": item["reviewStatus"],
                **item["counts"],
            })


def print_batch_summary(report: dict[str, Any], json_path: Path, csv_path: Path) -> None:
    summary = report["summary"]
    print("PDF summary batch extraction")
    print(f"- 전체 PDF 수: {summary['totalPdfCount']}")
    print(f"- 필터 후 대상 수: {summary['filteredTargetCountBeforeLimit']}")
    print(f"- 이번 배치 처리 PDF 수: {summary['processedPdfCount']}")
    print(f"- 엑셀 등록 PDF 처리 수: {summary['excelLinkedProcessedCount']}")
    print(f"- 엑셀 미등록 PDF 처리 수: {summary['excelMissingProcessedCount']}")
    print(f"- 텍스트 추출 성공 수: {summary['textExtractSuccessCount']}")
    print(f"- 텍스트 추출 실패 수: {summary['textExtractFailedCount']}")
    print(f"- GHS 후보 추출 수: {summary['ghsCandidatePdfCount']}")
    print(f"- 유해위험문구 후보 추출 수: {summary['hazardStatementPdfCount']}")
    print(f"- 예방조치문구 후보 추출 수: {summary['precautionStatementPdfCount']}")
    print(f"- 성분/CAS 후보 추출 수: {summary['ingredientCandidatePdfCount']}")
    print(f"- 신규 override 생성 수: {summary['newOverrideCreatedCount']}")
    print(f"- 기존 override 갱신 수: {summary['existingOverrideUpdatedCount']}")
    print(f"- 기존 reviewStatus 보존 수: {summary['reviewStatusPreservedCount']}")
    print(f"- 수동확인 필요 수: {summary['manualReviewRequiredPdfCount']}")
    if summary.get("retryCandidateCount"):
        print(f"- retry 대상 수: {summary['retryCandidateCount']}")
        print(f"- retry 성공 수: {summary['retrySuccessCount']}")
        print(f"- retry 실패 수: {summary['retryFailureCount']}")
        print(f"- 성공으로 전환된 수: {summary['retryRecoveredCount']}")
        print(f"- 기존 실패 유지 수: {summary['retryStillFailedCount']}")
    print(f"- JSON report: {json_path}")
    print(f"- CSV report: {csv_path}")


def print_single_summary(override: dict[str, Any], output_path: Path) -> None:
    precautions = override.get("precautionaryStatements", {})
    summary = {
        "fileName": override.get("match", {}).get("fileName", ""),
        "relativePath": override.get("match", {}).get("relativePath", ""),
        "extractStatus": override.get("extractStatus", ""),
        "reviewStatus": override.get("reviewStatus", ""),
        "pdfRegistrationType": override.get("pdfRegistrationType", ""),
        "counts": override_counts(override),
        "preview": {
            "ghsPictograms": override.get("ghsPictograms", [])[:5],
            "hazardStatements": override.get("hazardStatements", [])[:5],
            "preventionStatements": precautions.get("prevention", [])[:5],
            "responseStatements": precautions.get("response", [])[:5],
            "storageStatements": precautions.get("storage", [])[:5],
            "disposalStatements": precautions.get("disposal", [])[:5],
            "ingredients": override.get("ingredients", [])[:5],
            "ppeCandidates": override.get("ppeCandidates", [])[:5],
        },
        "outputPath": str(output_path),
        "note": "후보 추출 결과이며 검토완료 전까지 확정 정보로 사용하지 않습니다.",
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract review-only MSDS summary candidates from PDFs.")
    parser.add_argument("--input", type=Path, help=f"Single PDF file path. Default: {DEFAULT_INPUT}")
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR, help="PDF directory for batch extraction.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Local override JSON output.")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY, help="Local PDF inventory JSON.")
    parser.add_argument("--registration-queue", type=Path, default=DEFAULT_REGISTRATION_QUEUE, help="Local PDF registration queue JSON.")
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON, help="Local JSON batch report output.")
    parser.add_argument("--report-csv", type=Path, default=DEFAULT_REPORT_CSV, help="Local CSV batch report output.")
    parser.add_argument("--pages", type=int, default=0, help="Pages to extract; 0 means all pages.")
    parser.add_argument(
        "--target",
        choices=("all", "excel-linked", "excel-missing"),
        default="all",
        help="Select all PDFs, Excel-linked PDFs, or Excel-missing PDFs.",
    )
    parser.add_argument("--retry-failed", action="store_true", help="Retry only existing overrides whose previous extraction failed.")
    parser.add_argument("--only-missing-overrides", action="store_true", help="Process only PDFs that do not have a local override yet.")
    parser.add_argument("--skip-excluded", action=argparse.BooleanOptionalAction, default=True, help="Skip queue items excluded as non-MSDS/QR/guide/catalog documents. Default: true.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum PDFs to process in this batch. 0 means no limit.")
    parser.add_argument("--folder", default="", help="Only process PDFs under this relative folder path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if PdfReader is None:
        print("Error: pypdf is not installed in this Python environment.")
        print("Install dependencies with: python -m pip install -r requirements.txt")
        print("No override or report files were changed.")
        return 1

    existing_overrides = read_existing_overrides(args.output)
    total_pdf_count = len(list(args.pdf_dir.rglob("*.pdf"))) if args.pdf_dir.exists() else 0
    targets, filtered_target_count = discover_targets(args, existing_overrides)
    if args.input and not targets and args.input.exists():
        queue_lookup = queue_items_by_key(args.registration_queue)
        targets = [make_target_from_path(args.input, args.input.parent, queue_lookup)]
        filtered_target_count = 1

    overrides = [build_override_for_target(target, args.pages) for target in targets]
    merged, merge_stats = merge_overrides(args.output, overrides)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    batch_mode = args.input is None or len(targets) != 1
    if batch_mode:
        report = build_batch_report(targets, overrides, merge_stats, total_pdf_count, filtered_target_count, args)
        write_report_files(report, args.report_json, args.report_csv)
        print_batch_summary(report, args.report_json, args.report_csv)
    elif overrides:
        print_single_summary(overrides[0], args.output)
    else:
        print("No PDFs matched the requested extraction target.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
