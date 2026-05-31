#!/usr/bin/env python
"""Audit the local MSDS workflow before loading all PDF files.

This script only reads local data and PDF filenames. It does not modify,
move, rename, or delete any PDF or local JSON file. Reports are written as
*.local.* files so they stay out of Git.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_DATA = Path("data/msds.local.json")
DEFAULT_OVERRIDES = Path("data/msds-overrides.local.json")
DEFAULT_PDF_DIR = Path("pdf")
DEFAULT_REPORT_JSON = Path("reports/msds-workflow-audit.local.json")
DEFAULT_REPORT_CSV = Path("reports/msds-workflow-audit.local.csv")
REVIEW_STATUSES = ("검토필요", "검토완료", "수정필요", "제외")
EXTRACT_FAILURE_STATUSES = {
    "text_extract_failed",
    "scanned_pdf_or_image_pdf",
    "manual_review_required",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a local MSDS workflow audit report."
    )
    parser.add_argument("--data", default=DEFAULT_DATA, type=Path, help="Converted MSDS product JSON.")
    parser.add_argument("--overrides", default=DEFAULT_OVERRIDES, type=Path, help="Local PDF extraction override JSON.")
    parser.add_argument("--pdf-dir", default=DEFAULT_PDF_DIR, type=Path, help="Local PDF folder.")
    parser.add_argument("--report-json", default=DEFAULT_REPORT_JSON, type=Path, help="Local JSON report path.")
    parser.add_argument("--report-csv", default=DEFAULT_REPORT_CSV, type=Path, help="Local CSV report path.")
    parser.add_argument("--example-limit", default=5, type=int, help="Maximum example items per category.")
    return parser.parse_args()


def read_json_list(path: Path, list_key: str | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if list_key and isinstance(data, dict) and isinstance(data.get(list_key), list):
        return [item for item in data[list_key] if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("products"), list):
        return [item for item in data["products"] if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("overrides"), list):
        return [item for item in data["overrides"] if isinstance(item, dict)]
    raise ValueError(f"Unsupported JSON structure: {path}")


def product_ingredients(product: dict[str, Any]) -> list[dict[str, Any]]:
    ingredients = product.get("ingredients")
    if isinstance(ingredients, list):
        return [item for item in ingredients if isinstance(item, dict)]
    components = product.get("components")
    if isinstance(components, list):
        return [item for item in components if isinstance(item, dict)]
    return []


def normalize_text(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"\.pdf", "", text)
    return re.sub(r"[\s()[\]{}<>（）［］｛｝_\-/\\]", "", text)


def pdf_files(pdf_dir: Path) -> list[Path]:
    if not pdf_dir.exists():
        return []
    return sorted(path for path in pdf_dir.rglob("*.pdf") if path.is_file())


def override_file_name(override: dict[str, Any]) -> str:
    match = override.get("match") if isinstance(override.get("match"), dict) else {}
    file_name = str(match.get("fileName") or "").strip()
    if file_name:
        return file_name
    source_path = str(override.get("sourcePdfPath") or "").strip()
    return source_path.split("/").pop() if source_path else ""


def has_override_summary(override: dict[str, Any]) -> bool:
    precautions = override.get("precautionaryStatements") if isinstance(override.get("precautionaryStatements"), dict) else {}
    return bool(
        override.get("signalWordCandidate")
        or override.get("ghsPictograms")
        or override.get("hazardStatements")
        or override.get("ppeCandidates")
        or override.get("ingredients")
        or any(isinstance(items, list) and items for items in precautions.values())
    )


def limited(items: list[Any], limit: int) -> list[Any]:
    return items[: max(0, limit)]


def build_audit(args: argparse.Namespace) -> dict[str, Any]:
    products = read_json_list(args.data, "products")
    overrides = read_json_list(args.overrides, "overrides")
    pdf_paths = pdf_files(args.pdf_dir)

    pdf_names = {path.name for path in pdf_paths}
    pdf_names_normalized = {normalize_text(path.name): path.name for path in pdf_paths}

    product_file_names = [
        str(product.get("fileName") or "").strip()
        for product in products
        if str(product.get("fileName") or "").strip()
    ]
    product_file_set = set(product_file_names)
    product_file_normalized = {normalize_text(name): name for name in product_file_names if name}

    linked_products = [
        product
        for product in products
        if str(product.get("fileName") or "").strip() in pdf_names
    ]
    missing_pdf_products = [
        product
        for product in products
        if str(product.get("fileName") or "").strip()
        and str(product.get("fileName") or "").strip() not in pdf_names
    ]

    unregistered_pdf_names = [
        name
        for name in sorted(pdf_names)
        if name not in product_file_set and normalize_text(name) not in product_file_normalized
    ]

    override_names = {name for override in overrides if (name := override_file_name(override))}
    override_names_normalized = {normalize_text(name): name for name in override_names}
    override_with_pdf = [
        override
        for override in overrides
        if override_file_name(override) in pdf_names
        or normalize_text(override_file_name(override)) in pdf_names_normalized
    ]
    overrides_missing_pdf = [
        override
        for override in overrides
        if override_file_name(override)
        and override_file_name(override) not in pdf_names
        and normalize_text(override_file_name(override)) not in pdf_names_normalized
    ]

    pdf_without_override = [
        name
        for name in sorted(pdf_names)
        if name not in override_names and normalize_text(name) not in override_names_normalized
    ]

    review_counts = Counter({status: 0 for status in REVIEW_STATUSES})
    review_counts.update(str(override.get("reviewStatus") or "검토필요") for override in overrides)

    extract_success = [
        override
        for override in overrides
        if str(override.get("extractStatus") or "") not in EXTRACT_FAILURE_STATUSES
    ]
    extract_failed = [
        override
        for override in overrides
        if str(override.get("extractStatus") or "") in EXTRACT_FAILURE_STATUSES
    ]

    field_displayable = [
        override
        for override in overrides
        if override.get("reviewStatus") != "제외" and has_override_summary(override)
    ]
    manual_review_required = [
        override
        for override in overrides
        if override.get("reviewStatus") in {"검토필요", "수정필요"}
        or str(override.get("extractStatus") or "") in EXTRACT_FAILURE_STATUSES
    ]

    ingredient_count = sum(len(product_ingredients(product)) for product in products)
    summary = {
        "convertedProductCount": len(products),
        "ingredientCount": ingredient_count,
        "pdfFileCount": len(pdf_paths),
        "productsWithFileNameCount": len(product_file_names),
        "pdfLinkedProductCount": len(linked_products),
        "pdfMissingProductCount": len(missing_pdf_products),
        "unregisteredPdfCount": len(unregistered_pdf_names),
        "overrideCount": len(overrides),
        "pdfExtractSuccessCount": len(extract_success),
        "pdfExtractFailureCount": len(extract_failed),
        "reviewStatusCounts": {status: review_counts.get(status, 0) for status in REVIEW_STATUSES},
        "fieldDisplayableCount": len(field_displayable),
        "reviewCompletedCount": review_counts.get("검토완료", 0),
        "manualReviewRequiredCount": len(manual_review_required),
        "pdfPreviewPossibleEstimateCount": len(linked_products),
        "pdfWithoutOverrideCount": len(pdf_without_override),
        "overrideWithoutPdfCount": len(overrides_missing_pdf),
    }

    examples = {
        "pdfMissingProducts": [
            {
                "productName": product.get("productName", ""),
                "fileName": product.get("fileName", ""),
            }
            for product in limited(missing_pdf_products, args.example_limit)
        ],
        "unregisteredPdfs": limited(unregistered_pdf_names, args.example_limit),
        "pdfWithoutOverride": limited(pdf_without_override, args.example_limit),
        "overrideWithoutPdf": [
            {
                "fileName": override_file_name(override),
                "reviewStatus": override.get("reviewStatus", ""),
            }
            for override in limited(overrides_missing_pdf, args.example_limit)
        ],
        "manualReviewRequired": [
            {
                "fileName": override_file_name(override),
                "reviewStatus": override.get("reviewStatus", ""),
                "extractStatus": override.get("extractStatus", ""),
            }
            for override in limited(manual_review_required, args.example_limit)
        ],
    }

    return {
        "inputs": {
            "data": str(args.data),
            "overrides": str(args.overrides),
            "pdfDir": str(args.pdf_dir),
        },
        "summary": summary,
        "examples": examples,
    }


def write_json_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["category", "metric", "value"])
        for key, value in report["summary"].items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    writer.writerow(["summary", f"{key}.{sub_key}", sub_value])
            else:
                writer.writerow(["summary", key, value])


def print_console_summary(report: dict[str, Any]) -> None:
    summary = report["summary"]
    review = summary["reviewStatusCounts"]
    print("MSDS workflow audit summary")
    print(f"- 엑셀 변환 제품 수: {summary['convertedProductCount']}")
    print(f"- 성분정보 총 개수: {summary['ingredientCount']}")
    print(f"- PDF 폴더 내 PDF 파일 수: {summary['pdfFileCount']}")
    print(f"- PDF 연결 완료 수: {summary['pdfLinkedProductCount']}")
    print(f"- PDF 미등록 수: {summary['pdfMissingProductCount']}")
    print(f"- 엑셀 미등록 PDF 수: {summary['unregisteredPdfCount']}")
    print(f"- PDF 추출 override 수: {summary['overrideCount']}")
    print(f"- PDF 추출 성공 수: {summary['pdfExtractSuccessCount']}")
    print(f"- PDF 추출 실패 수: {summary['pdfExtractFailureCount']}")
    print(
        "- reviewStatus: "
        f"검토필요 {review['검토필요']}, "
        f"검토완료 {review['검토완료']}, "
        f"수정필요 {review['수정필요']}, "
        f"제외 {review['제외']}"
    )
    print(f"- 현장 표시 가능 항목 수: {summary['fieldDisplayableCount']}")
    print(f"- 수동 확인 필요 항목 수: {summary['manualReviewRequiredCount']}")
    print(f"- PDF는 있으나 override가 없는 항목 수: {summary['pdfWithoutOverrideCount']}")
    print(f"- override는 있으나 PDF 파일이 없는 항목 수: {summary['overrideWithoutPdfCount']}")

    example_count = sum(len(items) for items in report["examples"].values())
    if example_count:
        print("- 대표 예시는 local report 파일에 최대 5개씩 저장했습니다.")


def main() -> int:
    args = parse_args()
    report = build_audit(args)
    write_json_report(report, args.report_json)
    write_csv_report(report, args.report_csv)
    print_console_summary(report)
    print(f"\nJSON report: {args.report_json}")
    print(f"CSV report: {args.report_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
