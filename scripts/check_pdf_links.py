#!/usr/bin/env python
"""Check PDF link candidates for converted MSDS data.

This tool does not modify, move, rename, or delete PDF files. It only writes
local report files that are ignored by Git.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from pdf_match_utils import is_strong_or_probable, score_pdf_candidate


CAS_RE = re.compile(r"\b\d{2,7}-\d{2}-\d\b")
DEFAULT_DATA = Path("data/msds.local.json")
DEFAULT_PDF_DIR = Path("pdf")
DEFAULT_JSON_REPORT = Path("reports/pdf-link-report.local.json")
DEFAULT_CSV_REPORT = Path("reports/pdf-link-report.local.csv")


def normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"\.pdf", "", text)
    return re.sub(r"[\s()[\]{}<>（）［］｛｝_\-/\\]", "", text)


def read_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("products"), list):
        return data["products"]
    raise SystemExit(f"Unsupported JSON structure: {path}")


def product_ingredients(product: dict[str, Any]) -> list[dict[str, Any]]:
    ingredients = product.get("ingredients")
    if isinstance(ingredients, list):
        return ingredients
    components = product.get("components")
    if isinstance(components, list):
        return components
    return []


def product_search_terms(product: dict[str, Any]) -> dict[str, Any]:
    ingredients = product_ingredients(product)
    chemical_names = [
        str(item.get("chemicalName", "")).strip()
        for item in ingredients
        if str(item.get("chemicalName", "")).strip()
    ]
    cas_numbers = {
        cas
        for item in ingredients
        for cas in CAS_RE.findall(str(item.get("casNo", "")))
    }
    file_name = str(product.get("fileName", "")).strip()
    return {
        "productName": str(product.get("productName", "")).strip(),
        "erpName": str(product.get("erpName", "")).strip(),
        "msdsNo": str(product.get("msdsNo", "")).strip(),
        "supplier": str(product.get("supplier", "")).strip(),
        "fileName": file_name,
        "normalizedFileName": normalize_text(file_name),
        "chemicalNames": chemical_names,
        "normalizedChemicalNames": [
            normalize_text(name)
            for name in chemical_names
            if len(normalize_text(name)) >= 3
        ],
        "casNumbers": cas_numbers,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_pages_text(reader: Any, page_count: int) -> tuple[str, int]:
    chunks: list[str] = []
    extracted_pages = 0
    for page in reader.pages[:page_count]:
        text = page.extract_text() or ""
        if text.strip():
            extracted_pages += 1
        chunks.append(text)
    return "\n".join(chunks).strip(), extracted_pages


def extract_pdf_text(path: Path, max_pages: int) -> tuple[str, str, str]:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # pragma: no cover - environment dependent
        return "", "text_extract_failed", f"pypdf_import_failed: {exc}"

    try:
        reader = PdfReader(str(path))
        total_pages = len(reader.pages)
        page_count = total_pages if max_pages <= 0 else min(max_pages, total_pages)
        text, extracted_pages = extract_pages_text(reader, page_count)
        if not text and page_count < total_pages:
            text, extracted_pages = extract_pages_text(reader, total_pages)
    except Exception as exc:
        return "", "text_extract_failed", str(exc)

    if not text:
        return "", "scanned_pdf_or_image_pdf", "No extractable text in selected pages"
    return text, "text_extracted", f"extracted_pages={extracted_pages}"


def scan_pdfs(pdf_dir: Path, max_pages: int) -> list[dict[str, Any]]:
    if not pdf_dir.exists():
        return []

    pdfs: list[dict[str, Any]] = []
    for path in sorted(pdf_dir.rglob("*.pdf")):
        text, text_status, error = extract_pdf_text(path, max_pages)
        normalized_text = normalize_text(text)
        cas_numbers = sorted(set(CAS_RE.findall(text)))
        pdfs.append(
            {
                "path": str(path),
                "fileName": path.name,
                "relativePath": path.relative_to(pdf_dir).as_posix(),
                "normalizedFileName": normalize_text(path.name),
                "sha256": sha256_file(path),
                "textStatus": text_status,
                "textError": error,
                "casNumbers": cas_numbers,
                "casNoCandidates": cas_numbers,
                "normalizedText": normalized_text,
                "contentKey": "|".join(cas_numbers),
            }
        )
    return pdfs


def duplicate_groups(pdfs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for pdf in pdfs:
        by_hash[pdf["sha256"]].append(pdf)

    exact = [
        {
            "type": "exact_duplicate_pdf",
            "sha256": file_hash,
            "files": [pdf["fileName"] for pdf in group],
        }
        for file_hash, group in by_hash.items()
        if len(group) > 1
    ]
    return exact, []


def pdf_duplicate_names(exact_groups: list[dict[str, Any]], content_groups: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()
    for group in exact_groups + content_groups:
        names.update(group["files"])
    return names


def match_pdf_to_product(product: dict[str, Any], pdf: dict[str, Any]) -> dict[str, Any]:
    return score_pdf_candidate(product, pdf)


def decide_status(candidates: list[dict[str, Any]], duplicate_names: set[str]) -> tuple[str, bool]:
    if not candidates:
        return "manual_review_required", True

    strong_probable = [candidate for candidate in candidates if is_strong_or_probable(candidate)]
    if any("exact_file_match" in candidate["reasons"] for candidate in candidates):
        return "exact_file_match", False
    if any("normalized_filename_match" in candidate["reasons"] for candidate in candidates):
        return "normalized_filename_match", True
    duplicate_candidate = any(candidate["fileName"] in duplicate_names for candidate in candidates)
    if duplicate_candidate:
        return "possible_duplicate", True
    if len(strong_probable) > 1:
        return "multiple_candidates", True
    if candidates[0]["confidence"] == "strong_match_candidate":
        return "strong_match_candidate", True
    if candidates[0]["confidence"] == "probable_match_candidate":
        return "probable_match_candidate", True
    if candidates[0]["confidence"] == "weak_match_candidate":
        return "weak_match_candidate", True
    return "manual_review_required", True


def find_content_duplicate_groups(product_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for item in product_results:
        files = [
            candidate["fileName"]
            for candidate in item["candidates"]
            if is_strong_or_probable(candidate)
            and any(reason in candidate["reasons"] for reason in ("product_name_strong", "erp_name_strong", "cas_2plus_match", "msds_no_match"))
        ]
        if len(files) > 1:
            groups.append(
                {
                    "type": "possible_content_duplicate",
                    "basis": "same_product_content_match",
                    "productIndex": item["productIndex"],
                    "files": files,
                }
            )
    return groups


def find_multiple_candidate_groups(product_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for item in product_results:
        strong_probable = [candidate for candidate in item["candidates"] if is_strong_or_probable(candidate)]
        if len(strong_probable) > 1 and not any("exact_file_match" in candidate["reasons"] for candidate in item["candidates"]):
            groups.append(
                {
                    "type": "multiple_pdf_candidates",
                    "productIndex": item["productIndex"],
                    "files": [candidate["fileName"] for candidate in strong_probable],
                }
            )
    return groups


def build_report(products: list[dict[str, Any]], pdfs: list[dict[str, Any]]) -> dict[str, Any]:
    exact_groups, content_groups = duplicate_groups(pdfs)

    raw_product_results: list[dict[str, Any]] = []
    ignored_low_confidence_count = 0
    cas_only_weak_count = 0
    suppressed_by_exact_count = 0
    for index, product in enumerate(products, start=1):
        candidates: list[dict[str, Any]] = []
        for pdf in pdfs:
            candidate = match_pdf_to_product(product, pdf)
            if candidate["casOnlyWeak"]:
                cas_only_weak_count += 1
            if not candidate["include"]:
                if candidate["score"] > 0:
                    ignored_low_confidence_count += 1
                continue
            candidate["textStatus"] = pdf["textStatus"]
            candidate["reviewRequired"] = "exact_file_match" not in candidate["reasons"]
            candidates.append(candidate)

        if any("exact_file_match" in candidate["reasons"] for candidate in candidates):
            before = len(candidates)
            candidates = [
                candidate for candidate in candidates
                if candidate["confidence"] != "weak_match_candidate"
                or "exact_file_match" in candidate["reasons"]
            ]
            suppressed_by_exact_count += before - len(candidates)
        candidates = sorted(candidates, key=lambda item: item["score"], reverse=True)

        raw_product_results.append(
            {
                "productIndex": index,
                "productId": product.get("id", ""),
                "candidateCount": len(candidates),
                "strongProbableCandidateCount": sum(1 for candidate in candidates if is_strong_or_probable(candidate)),
                "weakCandidateCount": sum(1 for candidate in candidates if candidate["confidence"] == "weak_match_candidate"),
                "candidates": candidates,
            }
        )

    content_duplicate_groups: list[dict[str, Any]] = []
    multiple_candidate_groups = find_multiple_candidate_groups(raw_product_results)
    duplicate_groups_all = exact_groups + content_groups + content_duplicate_groups + multiple_candidate_groups
    duplicate_names = pdf_duplicate_names(duplicate_groups_all, [])

    product_results: list[dict[str, Any]] = []
    for item in raw_product_results:
        status, review_required = decide_status(item["candidates"], duplicate_names)
        product_results.append(
            {
                **item,
                "status": status,
                "reviewRequired": review_required,
            }
        )

    text_failed = [
        pdf for pdf in pdfs
        if pdf["textStatus"] in {"text_extract_failed", "scanned_pdf_or_image_pdf"}
    ]
    duplicate_pdf_count = len(duplicate_names)
    multiple_candidates = [item for item in product_results if item["status"] == "multiple_candidates"]
    manual_review_products = [item for item in product_results if item["reviewRequired"]]

    summary = {
        "totalProducts": len(products),
        "totalPdfs": len(pdfs),
        "exactFileMatchCount": sum(1 for item in product_results if item["status"] == "exact_file_match"),
        "normalizedFilenameMatchCount": sum(1 for item in product_results if item["status"] == "normalized_filename_match"),
        "strongMatchCandidateCount": sum(1 for item in product_results for candidate in item["candidates"] if candidate["confidence"] == "strong_match_candidate"),
        "probableMatchCandidateCount": sum(1 for item in product_results for candidate in item["candidates"] if candidate["confidence"] == "probable_match_candidate"),
        "weakMatchCandidateCount": sum(1 for item in product_results for candidate in item["candidates"] if candidate["confidence"] == "weak_match_candidate"),
        "ignoredLowConfidenceCount": ignored_low_confidence_count,
        "candidatesSuppressedByExactMatchCount": suppressed_by_exact_count,
        "casOnlyWeakMatchCount": cas_only_weak_count,
        "contentMatchCandidateCount": sum(1 for item in product_results if item["status"] in {"strong_match_candidate", "probable_match_candidate", "weak_match_candidate"}),
        "pdfTextExtractFailedCount": len(text_failed),
        "suspectedDuplicatePdfCount": duplicate_pdf_count,
        "multiplePdfCandidatesCount": len(multiple_candidates),
        "multipleCandidatesStrongProbableOnlyCount": len(multiple_candidates),
        "manualReviewRequiredCount": len(manual_review_products) + len(text_failed),
    }

    examples = [
        {
            "productIndex": item["productIndex"],
            "status": item["status"],
            "candidateCount": item["candidateCount"],
            "candidateStatuses": sorted({reason for candidate in item["candidates"] for reason in candidate["reasons"]}),
        }
        for item in product_results
        if item["reviewRequired"] or item["candidateCount"] > 1
    ][:5]

    return {
        "summary": summary,
        "examples": examples,
        "products": product_results,
        "pdfs": [
            {
                "fileName": pdf["fileName"],
                "textStatus": pdf["textStatus"],
                "textError": pdf["textError"],
                "casCount": len(pdf["casNumbers"]),
            }
            for pdf in pdfs
        ],
        "duplicateGroups": duplicate_groups_all,
    }


def write_reports(report: dict[str, Any], json_path: Path, csv_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "productIndex",
                "productId",
                "status",
                "reviewRequired",
                "candidateCount",
                "candidateFiles",
                "candidateReasons",
                "candidateScores",
                "candidateConfidence",
            ],
        )
        writer.writeheader()
        for item in report["products"]:
            writer.writerow(
                {
                    "productIndex": item["productIndex"],
                    "productId": item["productId"],
                    "status": item["status"],
                    "reviewRequired": item["reviewRequired"],
                    "candidateCount": item["candidateCount"],
                    "candidateFiles": "; ".join(candidate["fileName"] for candidate in item["candidates"]),
                    "candidateReasons": "; ".join(
                        ",".join(candidate["reasons"])
                        for candidate in item["candidates"]
                    ),
                    "candidateScores": "; ".join(str(candidate["score"]) for candidate in item["candidates"]),
                    "candidateConfidence": "; ".join(candidate["confidence"] for candidate in item["candidates"]),
                }
            )


def print_summary(report: dict[str, Any], json_path: Path, csv_path: Path) -> None:
    summary = report["summary"]
    print("PDF link check summary")
    print(f"- Products: {summary['totalProducts']}")
    print(f"- PDF files: {summary['totalPdfs']}")
    print(f"- Exact file matches: {summary['exactFileMatchCount']}")
    print(f"- Normalized filename match candidates: {summary['normalizedFilenameMatchCount']}")
    print(f"- Strong match candidates: {summary['strongMatchCandidateCount']}")
    print(f"- Probable match candidates: {summary['probableMatchCandidateCount']}")
    print(f"- Weak match candidates: {summary['weakMatchCandidateCount']}")
    print(f"- Ignored low confidence candidates: {summary['ignoredLowConfidenceCount']}")
    print(f"- Candidates suppressed by exact match: {summary['candidatesSuppressedByExactMatchCount']}")
    print(f"- CAS-only weak matches: {summary['casOnlyWeakMatchCount']}")
    print(f"- PDF text extraction failures: {summary['pdfTextExtractFailedCount']}")
    print(f"- Suspected duplicate PDFs: {summary['suspectedDuplicatePdfCount']}")
    print(f"- Products with multiple strong/probable PDF candidates: {summary['multiplePdfCandidatesCount']}")
    print(f"- Manual review required items: {summary['manualReviewRequiredCount']}")
    print(f"- JSON report: {json_path}")
    print(f"- CSV report: {csv_path}")
    if report["examples"]:
        print("- Representative review examples (redacted):")
        for example in report["examples"]:
            print(
                f"  productIndex={example['productIndex']}, "
                f"status={example['status']}, "
                f"candidateCount={example['candidateCount']}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check MSDS PDF link candidates.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Converted MSDS JSON path")
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR, help="PDF directory")
    parser.add_argument("--pages", type=int, default=3, help="Number of first pages to extract; use 0 for all pages")
    parser.add_argument("--json-report", type=Path, default=DEFAULT_JSON_REPORT, help="Local JSON report output")
    parser.add_argument("--csv-report", type=Path, default=DEFAULT_CSV_REPORT, help="Local CSV report output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    products = read_json(args.data)
    pdfs = scan_pdfs(args.pdf_dir, max(args.pages, 1))
    report = build_report(products, pdfs)
    write_reports(report, args.json_report, args.csv_report)
    print_summary(report, args.json_report, args.csv_report)


if __name__ == "__main__":
    main()
