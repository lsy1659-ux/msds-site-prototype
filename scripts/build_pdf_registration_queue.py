#!/usr/bin/env python
"""Build a local review queue for PDF-only MSDS files.

The queue tracks PDFs that exist in the PDF library but are not yet present in
the converted Excel index. It preserves reviewer decisions across reruns and
does not modify, move, rename, or delete PDF files.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_INVENTORY = Path("data/pdf-inventory.local.json")
DEFAULT_DATA = Path("data/msds.local.json")
DEFAULT_QUEUE = Path("data/pdf-registration-queue.local.json")
DEFAULT_SAMPLE = Path("data/pdf-registration-queue.sample.json")

REVIEW_DECISIONS = (
    "미검토",
    "엑셀등록필요",
    "기존제품매핑필요",
    "중복의심",
    "제외",
    "보류",
)

PRESERVE_FIELDS = {
    "reviewDecision",
    "suggestedAction",
    "tempProductName",
    "supplier",
    "category",
    "note",
    "matchedExcelCandidate",
    "duplicateCandidate",
    "excludeReason",
    "manualProductName",
    "manualSupplier",
    "manualCategory",
    "manualNote",
    "reviewedBy",
    "reviewedAt",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local queue for PDF-only MSDS files.")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY, help="Local PDF inventory JSON")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Converted MSDS product JSON")
    parser.add_argument("--output", type=Path, default=DEFAULT_QUEUE, help="Local registration queue output")
    parser.add_argument("--sample-output", type=Path, default=DEFAULT_SAMPLE, help="Safe sample queue output")
    return parser.parse_args()


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_inventory_items(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return [item for item in data["items"] if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def read_queue(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return [item for item in data["items"] if isinstance(item, dict)]
    return []


def read_product_count(path: Path) -> int:
    data = read_json(path)
    if isinstance(data, list):
        return len([item for item in data if isinstance(item, dict)])
    if isinstance(data, dict) and isinstance(data.get("products"), list):
        return len([item for item in data["products"] if isinstance(item, dict)])
    return 0


def queue_key(item: dict[str, Any]) -> str:
    return str(item.get("relativePath") or "").strip()


def default_suggested_action(inventory_item: dict[str, Any]) -> str:
    duplicate_statuses = inventory_item.get("duplicateStatuses")
    if isinstance(duplicate_statuses, list) and duplicate_statuses:
        return "중복여부확인"
    return "엑셀등록검토"


def build_queue_item(inventory_item: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    duplicate_statuses = inventory_item.get("duplicateStatuses")
    duplicate_candidate = bool(isinstance(duplicate_statuses, list) and duplicate_statuses)
    item = {
        "relativePath": inventory_item.get("relativePath", ""),
        "fileName": inventory_item.get("fileName", ""),
        "status": "excel_missing_pdf",
        "reviewDecision": "미검토",
        "suggestedAction": default_suggested_action(inventory_item),
        "tempProductName": "",
        "supplier": "",
        "category": "",
        "note": "",
        "matchedExcelCandidate": "",
        "duplicateCandidate": duplicate_candidate,
        "excludeReason": "",
        "inventoryStatus": inventory_item.get("inventoryStatus", ""),
        "duplicateStatuses": duplicate_statuses if isinstance(duplicate_statuses, list) else [],
        "sha256": inventory_item.get("sha256", ""),
        "fileSize": inventory_item.get("fileSize", ""),
        "modifiedTime": inventory_item.get("modifiedTime", ""),
        "lastSeenAt": datetime.now().isoformat(timespec="seconds"),
    }

    if existing:
        for key, value in existing.items():
            if key in PRESERVE_FIELDS or key.startswith("manual") or key.startswith("reviewed"):
                item[key] = value
        decision = str(item.get("reviewDecision") or "미검토")
        if decision not in REVIEW_DECISIONS:
            item["reviewDecision"] = "미검토"
    return item


def build_queue(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inventory_items = read_inventory_items(args.inventory)
    existing_items = read_queue(args.output)
    existing_by_path = {
        queue_key(item): item
        for item in existing_items
        if queue_key(item)
    }

    current_missing = [
        item for item in inventory_items
        if item.get("inventoryStatus") == "excel_missing_pdf"
    ]
    current_paths = {queue_key(item) for item in current_missing if queue_key(item)}

    queue_items = [
        build_queue_item(item, existing_by_path.get(queue_key(item)))
        for item in current_missing
        if queue_key(item)
    ]

    missing_from_library = []
    for relative_path, old_item in existing_by_path.items():
        if relative_path in current_paths:
            continue
        kept = dict(old_item)
        kept["status"] = "missing_from_pdf_library"
        kept["lastSeenAt"] = kept.get("lastSeenAt", "")
        missing_from_library.append(kept)

    queue_items.extend(missing_from_library)
    queue_items.sort(key=lambda item: (item.get("status", ""), item.get("relativePath", "")))

    decision_counts = Counter(str(item.get("reviewDecision") or "미검토") for item in queue_items)
    status_counts = Counter(str(item.get("status") or "") for item in queue_items)
    summary = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "inventoryPdfCount": len(inventory_items),
        "convertedProductCount": read_product_count(args.data),
        "excelMissingPdfCount": len(current_missing),
        "queueItemCount": len(queue_items),
        "missingFromPdfLibraryCount": status_counts.get("missing_from_pdf_library", 0),
        "reviewDecisionCounts": {decision: decision_counts.get(decision, 0) for decision in REVIEW_DECISIONS},
        "statusCounts": dict(sorted(status_counts.items())),
    }
    return queue_items, summary


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_sample(path: Path) -> None:
    sample = [
        {
            "relativePath": "3M/example.pdf",
            "fileName": "example.pdf",
            "status": "excel_missing_pdf",
            "reviewDecision": "미검토",
            "suggestedAction": "엑셀등록검토",
            "tempProductName": "",
            "supplier": "",
            "category": "",
            "note": "",
            "matchedExcelCandidate": "",
            "duplicateCandidate": False,
            "excludeReason": "",
        }
    ]
    write_json(path, sample)


def print_summary(summary: dict[str, Any], output: Path) -> None:
    decisions = summary["reviewDecisionCounts"]
    print("PDF registration queue summary")
    print(f"- Inventory PDF files: {summary['inventoryPdfCount']}")
    print(f"- Converted products: {summary['convertedProductCount']}")
    print(f"- Excel-missing PDFs: {summary['excelMissingPdfCount']}")
    print(f"- Queue items: {summary['queueItemCount']}")
    print(f"- Missing from PDF library: {summary['missingFromPdfLibraryCount']}")
    print(
        "- Decisions: "
        f"미검토 {decisions['미검토']}, "
        f"엑셀등록필요 {decisions['엑셀등록필요']}, "
        f"기존제품매핑필요 {decisions['기존제품매핑필요']}, "
        f"중복의심 {decisions['중복의심']}, "
        f"제외 {decisions['제외']}, "
        f"보류 {decisions['보류']}"
    )
    print(f"- Output: {output}")


def main() -> int:
    args = parse_args()
    queue_items, summary = build_queue(args)
    write_json(args.output, queue_items)
    write_sample(args.sample_output)
    print_summary(summary, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
