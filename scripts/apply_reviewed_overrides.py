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
        errors.extend(f"Row {index}: {problem}" for problem in edited_field_problems(item))
        validated.append(item)

    if errors:
        preview = "\n".join(errors[:10])
        suffix = "" if len(errors) <= 10 else f"\n... and {len(errors) - 10} more validation errors."
        raise ValueError(f"Validation failed:\n{preview}{suffix}")

    return validated


VALID_GHS = {f"GHS0{n}" for n in range(1, 10)}
VALID_SIGNALS = {"", "위험", "경고", "해당없음"}
PRECAUTION_GROUPS = ("prevention", "response", "storage", "disposal")


def edited_field_problems(item: dict[str, Any]) -> list[str]:
    """review.html 에서 고칠 수 있는 칸의 꼴을 본다. 틀린 꼴이 사이트까지 가지 않게."""
    problems: list[str] = []
    for field in ("hazardStatements", "ppeCandidates"):
        value = item.get(field)
        if value is not None and not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
            problems.append(f"{field} must be a list of text lines.")
    hazards = item.get("hazardStatements") or []
    if isinstance(hazards, list):
        for line in hazards:
            if isinstance(line, str) and line.strip().startswith("P") and line.strip()[1:4].isdigit():
                problems.append(f"P statement in hazardStatements: {line[:40]!r}")
    precautions = item.get("precautionaryStatements")
    if precautions is not None:
        if not isinstance(precautions, dict):
            problems.append("precautionaryStatements must be an object.")
        else:
            for group, lines in precautions.items():
                if group not in PRECAUTION_GROUPS or not isinstance(lines, list):
                    problems.append(f"precautionaryStatements.{group} must be one of {PRECAUTION_GROUPS} with a list.")
    for field in ("labelGhsCodes", "ghsCodes"):
        codes = item.get(field)
        if codes is not None and (not isinstance(codes, list) or any(code not in VALID_GHS for code in codes)):
            problems.append(f"{field} must list GHS01~GHS09 only: {codes!r}")
    if item.get("signalWordCandidate", "") not in VALID_SIGNALS:
        problems.append(f"signalWordCandidate must be one of {sorted(VALID_SIGNALS)}.")
    for entry in item.get("reviewLog") or []:
        if not isinstance(entry, dict) or not entry.get("field") or not entry.get("at"):
            problems.append("reviewLog entries need field and at.")
            break
    return problems


def print_edits(overrides: list[dict[str, Any]]) -> None:
    """review.html 에서 고친 것(reviewLog)을 한 줄씩 보인다. 반영 전에 눈으로 본다."""
    rows = [(item, entry) for item in overrides for entry in item.get("reviewLog") or []]
    if not rows:
        return
    print(f"\n고친 기록 {len(rows)}건")
    for item, entry in rows[-30:]:
        name = item.get("productNameCandidate") or str(item.get("sourcePdfPath", "")).split("/")[-1]
        before, after = entry.get("before"), entry.get("after")
        size = (lambda v: f"{len(v)}줄" if isinstance(v, list) else repr(v))
        evidence = f"원문 {entry['page']}쪽" if entry.get("page") else "쪽 미기재"
        print(f"- {str(entry.get('at', ''))[:10]} {entry.get('reviewer') or '검토자 미기재'} · {name[:30]} · "
              f"{entry.get('field')} {size(before)} → {size(after)} · {evidence}"
              f"{'' if entry.get('pdfSha256') else ' · PDF 지문 없음'}")


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
      print_edits(overrides)

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
