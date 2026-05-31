#!/usr/bin/env python
"""Safely apply a reviewed PDF registration queue JSON file.

This helper validates the JSON downloaded from pdf-queue.html, summarizes
review decisions, backs up the current local queue, then applies the reviewed
queue. It never modifies, deletes, moves, or renames PDF files.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = Path("data/pdf-registration-queue.local.json")
DEFAULT_BACKUP_DIR = Path("data/backups")
VALID_REVIEW_DECISIONS = {
    "미검토",
    "엑셀등록필요",
    "기존제품매핑필요",
    "중복의심",
    "제외",
    "보류",
}
REQUIRED_FIELDS = ("relativePath", "fileName", "reviewDecision")
RECOMMENDED_FIELDS = (
    "status",
    "suggestedAction",
    "tempProductName",
    "supplier",
    "category",
    "note",
    "matchedExcelCandidate",
    "duplicateCandidate",
    "excludeReason",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and safely apply a reviewed PDF registration queue JSON file."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Reviewed queue JSON downloaded from pdf-queue.html.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        type=Path,
        help=f"Local queue path to replace. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--backup-dir",
        default=DEFAULT_BACKUP_DIR,
        type=Path,
        help=f"Backup folder for the previous local queue. Default: {DEFAULT_BACKUP_DIR}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize only. Do not write or replace any file.",
    )
    return parser.parse_args()


def load_json_array(path: Path, label: str) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"{label} file not found: {path}")
    if not path.is_file():
        raise ValueError(f"{label} path is not a file: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} file is not valid JSON: {exc}") from exc

    if isinstance(data, dict):
        for key in ("queue", "items", "pdfRegistrationQueue"):
            if isinstance(data.get(key), list):
                data = data[key]
                break

    if not isinstance(data, list):
        raise ValueError(f"{label} JSON must be an array, or an object containing a queue/items array.")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{label} row {index}: item is not an object.")
        normalized.append(item)
    return normalized


def validate_queue(queue: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for index, item in enumerate(queue, start=1):
        for field in REQUIRED_FIELDS:
            if not str(item.get(field) or "").strip():
                errors.append(f"Row {index}: missing required field '{field}'.")

        decision = item.get("reviewDecision")
        if decision not in VALID_REVIEW_DECISIONS:
            errors.append(
                f"Row {index}: invalid reviewDecision {decision!r}. "
                f"Allowed: {', '.join(sorted(VALID_REVIEW_DECISIONS))}."
            )

        for field in RECOMMENDED_FIELDS:
            if field not in item:
                warnings.append(f"Row {index}: recommended field '{field}' is missing.")

        if "duplicateCandidate" in item and not isinstance(item.get("duplicateCandidate"), bool):
            warnings.append(f"Row {index}: duplicateCandidate should normally be true or false.")

    return errors, warnings


def summarize(queue: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    counts["전체"] = len(queue)
    for item in queue:
        counts[item.get("reviewDecision", "미검토")] += 1
    for decision in VALID_REVIEW_DECISIONS:
        counts.setdefault(decision, 0)
    return counts


def queue_key(item: dict[str, Any]) -> str:
    relative_path = str(item.get("relativePath") or "").strip()
    file_name = str(item.get("fileName") or "").strip()
    return relative_path or file_name


def truncate(value: str, limit: int = 64) -> str:
    value = value.replace("\n", " ").strip()
    if len(value) <= limit:
        return value
    return f"{value[: limit - 1]}..."


def compare_queues(
    old_queue: list[dict[str, Any]],
    new_queue: list[dict[str, Any]],
) -> dict[str, Any]:
    old_by_key = {queue_key(item): item for item in old_queue if queue_key(item)}
    new_by_key = {queue_key(item): item for item in new_queue if queue_key(item)}

    old_keys = set(old_by_key)
    new_keys = set(new_by_key)
    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)
    changed: list[str] = []

    for key in sorted(old_keys & new_keys):
        old_decision = old_by_key[key].get("reviewDecision")
        new_decision = new_by_key[key].get("reviewDecision")
        if old_decision != new_decision:
            changed.append(key)

    return {
        "old_count": len(old_queue),
        "new_count": len(new_queue),
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_decision_count": len(changed),
        "added_examples": added[:5],
        "removed_examples": removed[:5],
        "changed_examples": changed[:5],
    }


def load_existing_queue(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return load_json_array(path, "Existing local queue")


def backup_existing_output(output: Path, backup_dir: Path) -> Path | None:
    if not output.exists():
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"pdf-registration-queue.local.{timestamp}.json"
    shutil.copy2(output, backup_path)
    return backup_path


def apply_queue(queue: list[dict[str, Any]], output: Path, backup_dir: Path, input_path: Path) -> Path | None:
    if input_path.resolve() == output.resolve():
        raise ValueError("Input file and output file are the same path. Use a separate reviewed queue JSON file.")

    output.parent.mkdir(parents=True, exist_ok=True)
    backup_path = backup_existing_output(output, backup_dir)
    output.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return backup_path


def print_summary(counts: Counter[str]) -> None:
    print("PDF registration queue summary")
    print(f"- 전체 항목 수: {counts['전체']}")
    print(f"- 미검토 수: {counts['미검토']}")
    print(f"- 엑셀등록필요 수: {counts['엑셀등록필요']}")
    print(f"- 기존제품매핑필요 수: {counts['기존제품매핑필요']}")
    print(f"- 중복의심 수: {counts['중복의심']}")
    print(f"- 제외 수: {counts['제외']}")
    print(f"- 보류 수: {counts['보류']}")


def print_warnings(warnings: list[str]) -> None:
    if not warnings:
        return
    print("\nWarnings")
    for warning in warnings[:10]:
        print(f"- {warning}")
    if len(warnings) > 10:
        print(f"- ... and {len(warnings) - 10} more warnings.")


def print_comparison(comparison: dict[str, Any]) -> None:
    print("\nComparison with existing local queue")
    print(f"- 기존 항목 수: {comparison['old_count']}")
    print(f"- 새 항목 수: {comparison['new_count']}")
    print(f"- 새로 추가된 항목 수: {comparison['added_count']}")
    print(f"- 사라진 항목 수: {comparison['removed_count']}")
    print(f"- reviewDecision 변경 항목 수: {comparison['changed_decision_count']}")

    examples: list[tuple[str, list[str]]] = [
        ("추가 예시", comparison["added_examples"]),
        ("사라진 예시", comparison["removed_examples"]),
        ("상태 변경 예시", comparison["changed_examples"]),
    ]
    for label, values in examples:
        if values:
            print(f"- {label}: {', '.join(truncate(value) for value in values[:5])}")


def main() -> int:
    args = parse_args()

    try:
        reviewed_queue = load_json_array(args.input, "Input")
        errors, warnings = validate_queue(reviewed_queue)
        if errors:
            preview = "\n".join(f"- {error}" for error in errors[:10])
            suffix = "" if len(errors) <= 10 else f"\n- ... and {len(errors) - 10} more validation errors."
            raise ValueError(f"Validation failed:\n{preview}{suffix}")

        counts = summarize(reviewed_queue)
        print_summary(counts)
        print_warnings(warnings)

        existing_queue = load_existing_queue(args.output)
        print_comparison(compare_queues(existing_queue, reviewed_queue))

        if args.dry_run:
            print("\nDry-run mode: no files were changed.")
            return 0

        backup_path = apply_queue(reviewed_queue, args.output, args.backup_dir, args.input)
        if backup_path:
            print(f"\nBackup created: {backup_path}")
        else:
            print("\nNo existing local queue file was found, so no backup was needed.")
        print(f"Applied reviewed queue to: {args.output}")
        print("Next step: run python scripts/audit_msds_workflow.py to confirm queue counts.")
        return 0
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    except OSError as exc:
        print(f"Error: file operation failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
