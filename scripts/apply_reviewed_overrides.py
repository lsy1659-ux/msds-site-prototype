#!/usr/bin/env python
"""Safely apply reviewed MSDS override JSON to the local override file.

This helper is for local-only reviewed data. It validates the downloaded
review JSON, backs up the current local override file, then applies the
reviewed file. It never touches PDF files.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = Path("data/msds-overrides.local.json")
DEFAULT_BACKUP_DIR = Path("data/backups")
VALID_REVIEW_STATUSES = {"검토필요", "검토완료", "수정필요", "제외"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and safely apply a reviewed MSDS overrides JSON file."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Reviewed JSON downloaded from review.html, e.g. msds-overrides.reviewed.local.json",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        type=Path,
        help=f"Local override path to replace. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--backup-dir",
        default=DEFAULT_BACKUP_DIR,
        type=Path,
        help=f"Backup folder for the previous local override. Default: {DEFAULT_BACKUP_DIR}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize only. Do not write or replace any file.",
    )
    return parser.parse_args()


def load_reviewed_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"Input file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc}") from exc

    if isinstance(data, dict) and isinstance(data.get("overrides"), list):
        data = data["overrides"]

    if not isinstance(data, list):
        raise ValueError("Reviewed override JSON must be an array, or an object with an overrides array.")

    validated: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            errors.append(f"Row {index}: item is not an object.")
            continue
        if not isinstance(item.get("match"), dict):
            errors.append(f"Row {index}: missing match object.")
        status = item.get("reviewStatus")
        if status not in VALID_REVIEW_STATUSES:
            errors.append(
                f"Row {index}: invalid or missing reviewStatus "
                f"({status!r}). Allowed: {', '.join(sorted(VALID_REVIEW_STATUSES))}."
            )
        validated.append(item)

    if errors:
        preview = "\n".join(errors[:10])
        suffix = "" if len(errors) <= 10 else f"\n... and {len(errors) - 10} more validation errors."
        raise ValueError(f"Validation failed:\n{preview}{suffix}")

    return validated


def summarize(overrides: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    counts["전체"] = len(overrides)
    for item in overrides:
        counts[item.get("reviewStatus", "검토필요")] += 1
    for status in VALID_REVIEW_STATUSES:
        counts.setdefault(status, 0)
    return counts


def backup_existing_output(output: Path, backup_dir: Path) -> Path | None:
    if not output.exists():
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"msds-overrides.local.{timestamp}.json"
    shutil.copy2(output, backup_path)
    return backup_path


def apply_reviewed_file(input_path: Path, output: Path, backup_dir: Path) -> Path | None:
    input_resolved = input_path.resolve()
    output_resolved = output.resolve()
    if input_resolved == output_resolved:
        raise ValueError("Input file and output file are the same path. Use a separate reviewed JSON file.")

    output.parent.mkdir(parents=True, exist_ok=True)
    backup_path = backup_existing_output(output, backup_dir)
    shutil.copy2(input_path, output)
    return backup_path


def print_summary(counts: Counter[str]) -> None:
    print("Reviewed override summary")
    print(f"- 전체 항목 수: {counts['전체']}")
    print(f"- 검토필요 수: {counts['검토필요']}")
    print(f"- 검토완료 수: {counts['검토완료']}")
    print(f"- 수정필요 수: {counts['수정필요']}")
    print(f"- 제외 수: {counts['제외']}")


def main() -> int:
    args = parse_args()

    try:
      overrides = load_reviewed_json(args.input)
      counts = summarize(overrides)
      print_summary(counts)

      if args.dry_run:
          print("\nDry-run mode: no files were changed.")
          return 0

      backup_path = apply_reviewed_file(args.input, args.output, args.backup_dir)
      if backup_path:
          print(f"\nBackup created: {backup_path}")
      else:
          print("\nNo existing local override file was found, so no backup was needed.")
      print(f"Applied reviewed overrides to: {args.output}")
      return 0
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
