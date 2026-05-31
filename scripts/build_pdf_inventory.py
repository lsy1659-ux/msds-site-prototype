#!/usr/bin/env python
"""Build a local recursive PDF inventory for MSDS library management.

This script scans PDF files, extracts lightweight text signals, compares them
with the converted Excel JSON, and writes local-only inventory/report files.
It never deletes, moves, renames, or modifies PDF files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_DATA = Path("data/msds.local.json")
DEFAULT_PDF_DIR = Path("pdf")
DEFAULT_MAP = Path("data/pdf-map.local.json")
DEFAULT_INVENTORY = Path("data/pdf-inventory.local.json")
DEFAULT_SAMPLE = Path("data/pdf-inventory.sample.json")
DEFAULT_REPORT_JSON = Path("reports/pdf-inventory-report.local.json")
DEFAULT_REPORT_CSV = Path("reports/pdf-inventory-report.local.csv")

CAS_RE = re.compile(r"\b\d{2,7}-\d{2}-\d\b")
MSDS_NO_RE = re.compile(r"\b(?:MSDS|SDS)\s*(?:No\.?|번호)?\s*[:\-]?\s*([A-Za-z0-9][A-Za-z0-9_.\-/]{2,})", re.I)
LABEL_VALUE_RE = re.compile(r"^\s*([^:：]+)\s*[:：]\s*(.+?)\s*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local recursive MSDS PDF inventory.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Converted MSDS product JSON")
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR, help="PDF library root")
    parser.add_argument("--map", type=Path, default=DEFAULT_MAP, help="Optional local manual PDF map JSON")
    parser.add_argument("--output", type=Path, default=DEFAULT_INVENTORY, help="Local inventory JSON output")
    parser.add_argument("--sample-output", type=Path, default=DEFAULT_SAMPLE, help="Safe sample inventory JSON output")
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON, help="Local JSON report output")
    parser.add_argument("--report-csv", type=Path, default=DEFAULT_REPORT_CSV, help="Local CSV report output")
    parser.add_argument("--pages", type=int, default=3, help="First pages to extract for text signals; use 0 for all")
    parser.add_argument("--example-limit", type=int, default=5, help="Maximum examples in console/report summaries")
    return parser.parse_args()


def normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"\.pdf$", "", text)
    return re.sub(r"[\s()[\]{}<>_\-/\\.,:;]+", "", text)


def normalize_path(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/").lstrip("/")


def read_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("products", "items", "data"):
            if isinstance(data.get(key), list):
                return [item for item in data[key] if isinstance(item, dict)]
    return []


def read_pdf_map(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    entries: list[dict[str, str]] = []
    if isinstance(data, dict):
        raw_entries = data.get("mappings", data)
        if isinstance(raw_entries, dict):
            for key, value in raw_entries.items():
                entries.append({"source": str(key), "relativePath": normalize_path(value)})
        elif isinstance(raw_entries, list):
            data = raw_entries
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            entries.append({
                "productId": str(item.get("productId") or ""),
                "fileName": str(item.get("fileName") or ""),
                "msdsNo": str(item.get("msdsNo") or ""),
                "relativePath": normalize_path(item.get("relativePath") or item.get("pdfPath") or ""),
            })
    return [entry for entry in entries if entry.get("relativePath")]


def product_ingredients(product: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("ingredients", "components"):
        if isinstance(product.get(key), list):
            return [item for item in product[key] if isinstance(item, dict)]
    return []


def product_terms(product: dict[str, Any]) -> dict[str, Any]:
    file_name = str(product.get("fileName") or "").strip()
    product_name = str(product.get("productName") or "").strip()
    msds_no = str(product.get("msdsNo") or "").strip()
    cas_numbers = {
        cas
        for ingredient in product_ingredients(product)
        for cas in CAS_RE.findall(str(ingredient.get("casNo") or ""))
    }
    return {
        "id": str(product.get("id") or ""),
        "fileName": file_name,
        "relativePath": normalize_path(product.get("relativePath") or product.get("pdfPath") or ""),
        "normalizedFileName": normalize_text(file_name),
        "productName": product_name,
        "normalizedProductName": normalize_text(product_name),
        "msdsNo": msds_no,
        "normalizedMsdsNo": normalize_text(msds_no),
        "casNumbers": cas_numbers,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_pdf_text(path: Path, pages: int) -> tuple[str, dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover
        return "", {
            "textExtractStatus": "text_extract_failed",
            "textExtractError": f"pypdf_import_failed: {exc}",
            "textCharCount": 0,
            "pageCount": 0,
            "extractedPageCount": 0,
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
        combined = "\n".join(chunks).strip()
    except Exception as exc:
        return "", {
            "textExtractStatus": "text_extract_failed",
            "textExtractError": str(exc),
            "textCharCount": 0,
            "pageCount": 0,
            "extractedPageCount": 0,
        }

    return combined, {
        "textExtractStatus": "text_extracted" if combined else "scanned_pdf_or_image_pdf",
        "textExtractError": "",
        "textCharCount": len(combined),
        "pageCount": total_pages,
        "extractedPageCount": extracted_pages,
    }


def clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" -:\t")


def unique_limited(items: list[str], limit: int = 8) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        value = clean_line(item)
        key = normalize_text(value)
        if not value or key in seen:
            continue
        seen.add(key)
        result.append(value)
        if len(result) >= limit:
            break
    return result


def extract_product_candidates(text: str) -> list[str]:
    lines = [clean_line(line) for line in text.splitlines() if clean_line(line)]
    candidates: list[str] = []
    labels = ("제품명", "제품의 명칭", "화학제품명", "물질명", "Product name", "Trade name")
    for index, line in enumerate(lines[:80]):
        for label in labels:
            if label.lower() not in line.lower():
                continue
            match = LABEL_VALUE_RE.match(line)
            if match and label.lower() in match.group(1).lower():
                candidates.append(match.group(2))
            elif index + 1 < len(lines):
                candidates.append(lines[index + 1])
    return unique_limited([item for item in candidates if 2 <= len(item) <= 160], 5)


def extract_msds_no_candidates(text: str) -> list[str]:
    candidates = [match.group(1).strip() for match in MSDS_NO_RE.finditer(text)]
    for line in text.splitlines()[:100]:
        cleaned = clean_line(line)
        if "MSDS" not in cleaned.upper() and "SDS" not in cleaned.upper() and "관리번호" not in cleaned:
            continue
        match = LABEL_VALUE_RE.match(cleaned)
        if match:
            candidates.append(match.group(2))
    return unique_limited([item for item in candidates if 2 <= len(item) <= 80], 5)


def fingerprint_text(text: str) -> str:
    normalized = normalize_text(text)
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_pdf_item(path: Path, pdf_dir: Path, pages: int) -> dict[str, Any]:
    relative_path = path.relative_to(pdf_dir).as_posix()
    text, meta = extract_pdf_text(path, pages)
    stat = path.stat()
    cas_candidates = sorted(set(CAS_RE.findall(text)))
    return {
        "fileName": path.name,
        "relativePath": relative_path,
        "pdfPath": f"/pdf/{relative_path}",
        "fileSize": stat.st_size,
        "modifiedTime": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "sha256": sha256_file(path),
        "normalizedFileName": normalize_text(path.name),
        "textExtractStatus": meta["textExtractStatus"],
        "textExtractError": meta["textExtractError"],
        "textCharCount": meta["textCharCount"],
        "pageCount": meta["pageCount"],
        "extractedPageCount": meta["extractedPageCount"],
        "productNameCandidates": extract_product_candidates(text),
        "casNoCandidates": cas_candidates[:30],
        "msdsNoCandidates": extract_msds_no_candidates(text),
        "firstPagesTextFingerprint": fingerprint_text(text),
        "inventoryStatus": "unclassified",
        "duplicateStatuses": [],
        "matchCandidates": [],
    }


def scan_pdf_inventory(pdf_dir: Path, pages: int) -> list[dict[str, Any]]:
    if not pdf_dir.exists():
        return []
    return [build_pdf_item(path, pdf_dir, pages) for path in sorted(pdf_dir.rglob("*.pdf")) if path.is_file()]


def add_duplicate_statuses(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    group_specs = [
        ("exact_duplicate_pdf", "sha256"),
        ("filename_duplicate", "fileName"),
        ("possible_content_duplicate", "firstPagesTextFingerprint"),
    ]
    by_relative = {item["relativePath"]: item for item in items}

    for duplicate_type, key in group_specs:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            value = item.get(key)
            if value:
                grouped[str(value).lower() if key == "fileName" else str(value)].append(item)
        for basis, group in grouped.items():
            if len(group) <= 1:
                continue
            for item in group:
                item["duplicateStatuses"].append(duplicate_type)
            groups.append({
                "type": duplicate_type,
                "basis": basis if duplicate_type != "exact_duplicate_pdf" else "sha256",
                "files": [item["relativePath"] for item in group],
                "reviewRequired": True,
            })

    cas_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        cas_key = "|".join(item.get("casNoCandidates") or [])
        if cas_key and len(item.get("casNoCandidates") or []) >= 2:
            cas_groups[cas_key].append(item)
    for cas_key, group in cas_groups.items():
        if len(group) <= 1:
            continue
        for item in group:
            if "possible_content_duplicate" not in item["duplicateStatuses"]:
                item["duplicateStatuses"].append("possible_content_duplicate")
        groups.append({
            "type": "possible_content_duplicate",
            "basis": "same_cas_candidates",
            "files": [item["relativePath"] for item in group],
            "reviewRequired": True,
        })

    return groups


def mapped_paths_for_product(product: dict[str, Any], mappings: list[dict[str, str]]) -> set[str]:
    terms = product_terms(product)
    paths: set[str] = set()
    for entry in mappings:
        if entry.get("productId") and entry["productId"] == terms["id"]:
            paths.add(normalize_path(entry["relativePath"]))
        if entry.get("fileName") and normalize_text(entry["fileName"]) == terms["normalizedFileName"]:
            paths.add(normalize_path(entry["relativePath"]))
        if entry.get("msdsNo") and normalize_text(entry["msdsNo"]) == terms["normalizedMsdsNo"]:
            paths.add(normalize_path(entry["relativePath"]))
        if entry.get("source") and normalize_text(entry["source"]) in {
            terms["id"],
            terms["normalizedFileName"],
            terms["normalizedMsdsNo"],
        }:
            paths.add(normalize_path(entry["relativePath"]))
    return paths


def match_reasons(product: dict[str, Any], pdf: dict[str, Any], mapped_paths: set[str]) -> list[str]:
    terms = product_terms(product)
    reasons: list[str] = []

    if terms["fileName"] and terms["fileName"] == pdf["fileName"]:
        reasons.append("exact_file_match")
    if terms["relativePath"] and terms["relativePath"].removeprefix("pdf/") == pdf["relativePath"]:
        reasons.append("exact_file_match")
    if terms["normalizedFileName"] and terms["normalizedFileName"] == pdf["normalizedFileName"]:
        reasons.append("normalized_filename_match")
    if pdf["relativePath"] in mapped_paths or pdf["pdfPath"].lstrip("/") in mapped_paths:
        reasons.append("mapped")

    pdf_product_names = {normalize_text(name) for name in pdf.get("productNameCandidates") or []}
    if terms["normalizedProductName"] and terms["normalizedProductName"] in pdf_product_names:
        reasons.append("content_match_candidate")
    if terms["normalizedProductName"] and any(
        terms["normalizedProductName"] in name or name in terms["normalizedProductName"]
        for name in pdf_product_names
        if len(name) >= 4
    ):
        reasons.append("content_match_candidate")
    if terms["casNumbers"].intersection(set(pdf.get("casNoCandidates") or [])):
        reasons.append("content_match_candidate")
    if terms["normalizedMsdsNo"] and terms["normalizedMsdsNo"] in {
        normalize_text(value) for value in pdf.get("msdsNoCandidates") or []
    }:
        reasons.append("content_match_candidate")

    return sorted(set(reasons))


def status_from_reasons(reasons: list[str], candidate_count: int, has_duplicate: bool) -> str:
    if has_duplicate:
        return "duplicate_candidate"
    if candidate_count > 1:
        return "multiple_pdf_candidates"
    if "mapped" in reasons:
        return "mapped"
    if "exact_file_match" in reasons:
        return "exact_file_match"
    if "normalized_filename_match" in reasons:
        return "normalized_filename_match"
    if "content_match_candidate" in reasons:
        return "content_match_candidate"
    return "mapping_needed"


def compare_products_to_pdfs(
    products: list[dict[str, Any]],
    pdf_items: list[dict[str, Any]],
    mappings: list[dict[str, str]],
) -> list[dict[str, Any]]:
    product_results: list[dict[str, Any]] = []

    for index, product in enumerate(products, start=1):
        mapped_paths = mapped_paths_for_product(product, mappings)
        candidates: list[dict[str, Any]] = []
        for pdf in pdf_items:
            reasons = match_reasons(product, pdf, mapped_paths)
            if reasons:
                candidates.append({
                    "relativePath": pdf["relativePath"],
                    "fileName": pdf["fileName"],
                    "reasons": reasons,
                })

        has_duplicate = any(
            pdf["duplicateStatuses"]
            for pdf in pdf_items
            if any(candidate["relativePath"] == pdf["relativePath"] for candidate in candidates)
        )
        first_reasons = candidates[0]["reasons"] if candidates else []
        status = "pdf_missing" if not candidates else status_from_reasons(first_reasons, len(candidates), has_duplicate)
        product_results.append({
            "productIndex": index,
            "productId": product.get("id", ""),
            "fileName": product.get("fileName", ""),
            "status": status,
            "candidateCount": len(candidates),
            "candidates": candidates,
            "reviewRequired": status not in {"exact_file_match", "linked"},
        })

    matched_paths = {
        candidate["relativePath"]
        for result in product_results
        for candidate in result["candidates"]
    }
    for pdf in pdf_items:
        if pdf["relativePath"] not in matched_paths:
            pdf["inventoryStatus"] = "excel_missing_pdf"
            continue
        matching_results = [
            result for result in product_results
            if any(candidate["relativePath"] == pdf["relativePath"] for candidate in result["candidates"])
        ]
        if pdf["duplicateStatuses"]:
            pdf["inventoryStatus"] = "duplicate_candidate"
        elif len(matching_results) > 1:
            pdf["inventoryStatus"] = "multiple_pdf_candidates"
        else:
            pdf["inventoryStatus"] = matching_results[0]["status"]

    multiple_groups = [
        {
            "type": "multiple_pdf_candidates",
            "productIndex": result["productIndex"],
            "files": [candidate["relativePath"] for candidate in result["candidates"]],
            "reviewRequired": True,
        }
        for result in product_results
        if result["candidateCount"] > 1
    ]
    return product_results, multiple_groups


def build_inventory(args: argparse.Namespace) -> dict[str, Any]:
    products = read_json_list(args.data)
    mappings = read_pdf_map(args.map)
    pdf_items = scan_pdf_inventory(args.pdf_dir, args.pages)
    duplicate_groups = add_duplicate_statuses(pdf_items)
    product_results, multiple_groups = compare_products_to_pdfs(products, pdf_items, mappings)
    duplicate_groups.extend(multiple_groups)

    pdf_file_names = {item["fileName"] for item in pdf_items}
    pdf_file_names_normalized = {item["normalizedFileName"] for item in pdf_items}
    products_with_file_name = [
        product for product in products
        if str(product.get("fileName") or "").strip()
    ]
    exact_file_linked_products = [
        product for product in products_with_file_name
        if str(product.get("fileName") or "").strip() in pdf_file_names
    ]
    filename_missing_products = [
        product for product in products_with_file_name
        if str(product.get("fileName") or "").strip() not in pdf_file_names
        and normalize_text(product.get("fileName")) not in pdf_file_names_normalized
    ]

    status_counts = defaultdict(int)
    for item in pdf_items:
        status_counts[item["inventoryStatus"]] += 1
    product_status_counts = defaultdict(int)
    for result in product_results:
        product_status_counts[result["status"]] += 1

    summary = {
        "pdfCount": len(pdf_items),
        "productCount": len(products),
        "productsWithFileNameCount": len(products_with_file_name),
        "exactFileLinkedProductCount": len(exact_file_linked_products),
        "excelFileNamePdfMissingCount": len(filename_missing_products),
        "textExtractedPdfCount": sum(1 for item in pdf_items if item["textExtractStatus"] == "text_extracted"),
        "textExtractFailedPdfCount": sum(1 for item in pdf_items if item["textExtractStatus"] != "text_extracted"),
        "pdfWithCasCandidateCount": sum(1 for item in pdf_items if item["casNoCandidates"]),
        "excelMissingPdfCount": status_counts["excel_missing_pdf"],
        "pdfMissingProductCount": product_status_counts["pdf_missing"],
        "exactDuplicateGroupCount": sum(1 for group in duplicate_groups if group["type"] == "exact_duplicate_pdf"),
        "filenameDuplicateGroupCount": sum(1 for group in duplicate_groups if group["type"] == "filename_duplicate"),
        "possibleContentDuplicateGroupCount": sum(1 for group in duplicate_groups if group["type"] == "possible_content_duplicate"),
        "multiplePdfCandidateProductCount": sum(1 for group in duplicate_groups if group["type"] == "multiple_pdf_candidates"),
        "inventoryStatusCounts": dict(sorted(status_counts.items())),
        "productLinkStatusCounts": dict(sorted(product_status_counts.items())),
    }

    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "pdfDir": str(args.pdf_dir),
            "data": str(args.data),
            "map": str(args.map),
            "pages": args.pages,
        },
        "summary": summary,
        "items": pdf_items,
        "productLinkResults": product_results,
        "duplicateGroups": duplicate_groups,
    }


def safe_report(inventory: dict[str, Any], example_limit: int) -> dict[str, Any]:
    examples = {
        "excelMissingPdfs": [
            {"relativePath": item["relativePath"], "inventoryStatus": item["inventoryStatus"]}
            for item in inventory["items"]
            if item["inventoryStatus"] == "excel_missing_pdf"
        ][:example_limit],
        "duplicateGroups": inventory["duplicateGroups"][:example_limit],
        "mappingNeededProducts": [
            {
                "productIndex": item["productIndex"],
                "status": item["status"],
                "candidateCount": item["candidateCount"],
            }
            for item in inventory["productLinkResults"]
            if item["reviewRequired"]
        ][:example_limit],
    }
    return {
        "generatedAt": inventory["generatedAt"],
        "inputs": inventory["inputs"],
        "summary": inventory["summary"],
        "examples": examples,
    }


def build_sample_inventory() -> dict[str, Any]:
    return {
        "generatedAt": "sample",
        "summary": {
            "pdfCount": 1,
            "productCount": 1,
            "textExtractedPdfCount": 1,
            "excelMissingPdfCount": 0,
            "pdfMissingProductCount": 0,
        },
        "items": [
            {
                "fileName": "PN3021.pdf",
                "relativePath": "3M/PN3021.pdf",
                "pdfPath": "/pdf/3M/PN3021.pdf",
                "fileSize": 123456,
                "modifiedTime": "2026-05-31T09:00:00",
                "sha256": "sample-sha256",
                "normalizedFileName": "pn3021",
                "textExtractStatus": "text_extracted",
                "textCharCount": 2500,
                "pageCount": 19,
                "productNameCandidates": ["샘플 제품명"],
                "casNoCandidates": ["000-00-0"],
                "msdsNoCandidates": ["SAMPLE-MSDS-001"],
                "firstPagesTextFingerprint": "sample-fingerprint",
                "inventoryStatus": "exact_file_match",
                "duplicateStatuses": [],
                "matchCandidates": [],
            }
        ],
        "productLinkResults": [
            {
                "productIndex": 1,
                "productId": "sample-001",
                "fileName": "PN3021.pdf",
                "status": "exact_file_match",
                "candidateCount": 1,
                "candidates": [
                    {
                        "relativePath": "3M/PN3021.pdf",
                        "fileName": "PN3021.pdf",
                        "reasons": ["exact_file_match"],
                    }
                ],
                "reviewRequired": False,
            }
        ],
        "duplicateGroups": [],
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, inventory: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "relativePath",
                "fileName",
                "fileSize",
                "modifiedTime",
                "sha256",
                "textExtractStatus",
                "textCharCount",
                "pageCount",
                "casCandidateCount",
                "inventoryStatus",
                "duplicateStatuses",
            ],
        )
        writer.writeheader()
        for item in inventory["items"]:
            writer.writerow({
                "relativePath": item["relativePath"],
                "fileName": item["fileName"],
                "fileSize": item["fileSize"],
                "modifiedTime": item["modifiedTime"],
                "sha256": item["sha256"],
                "textExtractStatus": item["textExtractStatus"],
                "textCharCount": item["textCharCount"],
                "pageCount": item["pageCount"],
                "casCandidateCount": len(item["casNoCandidates"]),
                "inventoryStatus": item["inventoryStatus"],
                "duplicateStatuses": ";".join(item["duplicateStatuses"]),
            })


def print_summary(report: dict[str, Any], inventory_path: Path, json_path: Path, csv_path: Path) -> None:
    summary = report["summary"]
    print("PDF inventory summary")
    print(f"- PDF files scanned: {summary['pdfCount']}")
    print(f"- Products with Excel fileName: {summary['productsWithFileNameCount']}")
    print(f"- Exact fileName linked products: {summary['exactFileLinkedProductCount']}")
    print(f"- Excel fileName PDF missing products: {summary['excelFileNamePdfMissingCount']}")
    print(f"- Text extracted PDFs: {summary['textExtractedPdfCount']}")
    print(f"- Text extraction failed/image PDFs: {summary['textExtractFailedPdfCount']}")
    print(f"- PDFs with CAS candidates: {summary['pdfWithCasCandidateCount']}")
    print(f"- Excel-missing PDFs: {summary['excelMissingPdfCount']}")
    print(f"- PDF-missing products: {summary['pdfMissingProductCount']}")
    print(f"- Exact duplicate groups: {summary['exactDuplicateGroupCount']}")
    print(f"- Filename duplicate groups: {summary['filenameDuplicateGroupCount']}")
    print(f"- Possible content duplicate groups: {summary['possibleContentDuplicateGroupCount']}")
    print(f"- Products with multiple PDF candidates: {summary['multiplePdfCandidateProductCount']}")
    print(f"- Inventory: {inventory_path}")
    print(f"- JSON report: {json_path}")
    print(f"- CSV report: {csv_path}")


def main() -> int:
    args = parse_args()
    inventory = build_inventory(args)
    report = safe_report(inventory, args.example_limit)

    write_json(args.output, inventory)
    write_json(args.sample_output, build_sample_inventory())
    write_json(args.report_json, report)
    write_csv(args.report_csv, inventory)
    print_summary(report, args.output, args.report_json, args.report_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
