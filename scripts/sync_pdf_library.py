#!/usr/bin/env python
"""Safely preview or apply PDF library synchronization.

The script compares a source MSDS PDF folder with the local site PDF folder.
It never deletes, moves, or renames files. In --apply mode it only copies new
or changed PDFs, backing up changed target files first.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_TARGET = Path("pdf")
DEFAULT_BACKUP_ROOT = Path("data/backups/pdf-sync")
DEFAULT_PREVIEW_JSON = Path("reports/pdf-sync-preview.local.json")
DEFAULT_PREVIEW_CSV = Path("reports/pdf-sync-preview.local.csv")
DEFAULT_APPLY_JSON = Path("reports/pdf-sync-apply.local.json")
DEFAULT_APPLY_CSV = Path("reports/pdf-sync-apply.local.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview or apply safe MSDS PDF library sync.")
    parser.add_argument("--source", required=True, type=Path, help="Source MSDS PDF folder")
    parser.add_argument("--target", default=DEFAULT_TARGET, type=Path, help="Target site PDF folder")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only; this is the default")
    parser.add_argument("--apply", action="store_true", help="Copy new/changed PDFs into the target folder")
    parser.add_argument("--backup-root", default=DEFAULT_BACKUP_ROOT, type=Path, help="Backup folder for overwritten PDFs")
    parser.add_argument("--report-json", type=Path, help="Override local JSON report path")
    parser.add_argument("--report-csv", type=Path, help="Override local CSV report path")
    parser.add_argument("--run-audit", action="store_true", help="After sync, run inventory/link/audit scripts")
    parser.add_argument("--example-limit", default=5, type=int, help="Maximum examples to print per category")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_relative(path: Path) -> str:
    return path.as_posix()


def scan_pdfs(root: Path) -> dict[str, dict[str, Any]]:
    if not root.exists():
        raise SystemExit(f"Folder does not exist: {root}")
    if not root.is_dir():
        raise SystemExit(f"Path is not a folder: {root}")

    items: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*.pdf")):
        if not path.is_file():
            continue
        relative_path = normalize_relative(path.relative_to(root))
        stat = path.stat()
        items[relative_path] = {
            "relativePath": relative_path,
            "fileName": path.name,
            "fileSize": stat.st_size,
            "modifiedTime": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "sha256": sha256_file(path),
            "_path": path,
        }
    return items


def duplicate_groups(items: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_file_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items.values():
        by_sha[item["sha256"]].append(item)
        by_file_name[item["fileName"].lower()].append(item)

    exact_duplicates = [
        {
            "status": "exact_duplicate_candidate",
            "sha256": sha,
            "files": [item["relativePath"] for item in group],
            "reviewRequired": True,
        }
        for sha, group in by_sha.items()
        if len(group) > 1
    ]
    filename_duplicates = [
        {
            "status": "filename_duplicate_candidate",
            "fileName": group[0]["fileName"],
            "files": [item["relativePath"] for item in group],
            "reviewRequired": True,
        }
        for group in by_file_name.values()
        if len(group) > 1
    ]
    return exact_duplicates, filename_duplicates


def build_sync_plan(source: dict[str, dict[str, Any]], target: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source_by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    target_by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in source.values():
        source_by_sha[item["sha256"]].append(item)
    for item in target.values():
        target_by_sha[item["sha256"]].append(item)

    items: list[dict[str, Any]] = []
    moved_or_renamed: list[dict[str, Any]] = []

    for relative_path, source_item in source.items():
        target_item = target.get(relative_path)
        if target_item:
            status = "unchanged" if source_item["sha256"] == target_item["sha256"] else "changed_same_path"
            items.append({
                "status": status,
                "relativePath": relative_path,
                "fileName": source_item["fileName"],
                "sourceSha256": source_item["sha256"],
                "targetSha256": target_item["sha256"],
                "sourceFileSize": source_item["fileSize"],
                "targetFileSize": target_item["fileSize"],
            })
            continue

        same_hash_targets = [
            item for item in target_by_sha.get(source_item["sha256"], [])
            if item["relativePath"] != relative_path
        ]
        status = "moved_or_renamed_candidate" if same_hash_targets else "new_file"
        items.append({
            "status": status,
            "relativePath": relative_path,
            "fileName": source_item["fileName"],
            "sourceSha256": source_item["sha256"],
            "targetSha256": "",
            "sourceFileSize": source_item["fileSize"],
            "targetFileSize": "",
            "candidateTargetPaths": [item["relativePath"] for item in same_hash_targets],
        })
        if same_hash_targets:
            moved_or_renamed.append({
                "status": "moved_or_renamed_candidate",
                "sourceRelativePath": relative_path,
                "targetRelativePaths": [item["relativePath"] for item in same_hash_targets],
                "sha256": source_item["sha256"],
                "reviewRequired": True,
            })

    for relative_path, target_item in target.items():
        if relative_path in source:
            continue
        same_hash_sources = [
            item for item in source_by_sha.get(target_item["sha256"], [])
            if item["relativePath"] != relative_path
        ]
        items.append({
            "status": "deleted_from_source",
            "relativePath": relative_path,
            "fileName": target_item["fileName"],
            "sourceSha256": "",
            "targetSha256": target_item["sha256"],
            "sourceFileSize": "",
            "targetFileSize": target_item["fileSize"],
            "candidateSourcePaths": [item["relativePath"] for item in same_hash_sources],
        })
        if same_hash_sources:
            moved_or_renamed.append({
                "status": "moved_or_renamed_candidate",
                "sourceRelativePaths": [item["relativePath"] for item in same_hash_sources],
                "targetRelativePath": relative_path,
                "sha256": target_item["sha256"],
                "reviewRequired": True,
            })

    source_exact_duplicates, source_filename_duplicates = duplicate_groups(source)
    return {
        "items": sorted(items, key=lambda item: (item["status"], item["relativePath"])),
        "movedOrRenamedCandidates": moved_or_renamed,
        "exactDuplicateCandidates": source_exact_duplicates,
        "filenameDuplicateCandidates": source_filename_duplicates,
    }


def summarize(plan: dict[str, Any], source_count: int, target_count: int, mode: str) -> dict[str, Any]:
    status_counts = defaultdict(int)
    for item in plan["items"]:
        status_counts[item["status"]] += 1
    return {
        "mode": mode,
        "sourcePdfCount": source_count,
        "targetPdfCount": target_count,
        "newFileCount": status_counts["new_file"],
        "changedSamePathCount": status_counts["changed_same_path"],
        "unchangedCount": status_counts["unchanged"],
        "deletedFromSourceCount": status_counts["deleted_from_source"],
        "movedOrRenamedCandidateCount": len(plan["movedOrRenamedCandidates"]),
        "exactDuplicateCandidateCount": len(plan["exactDuplicateCandidates"]),
        "filenameDuplicateCandidateCount": len(plan["filenameDuplicateCandidates"]),
        "appliedCopyCount": 0,
        "backedUpChangedFileCount": 0,
    }


def copy_with_backup(
    plan: dict[str, Any],
    source_root: Path,
    target_root: Path,
    backup_root: Path,
) -> tuple[int, int]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    applied = 0
    backed_up = 0

    for item in plan["items"]:
        if item["status"] not in {"new_file", "changed_same_path", "moved_or_renamed_candidate"}:
            continue

        relative_path = Path(item["relativePath"])
        source_path = source_root / relative_path
        target_path = target_root / relative_path
        if source_path.resolve() == target_path.resolve():
            continue

        target_path.parent.mkdir(parents=True, exist_ok=True)
        if target_path.exists() and item["status"] == "changed_same_path":
            backup_path = backup_root / timestamp / relative_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target_path, backup_path)
            backed_up += 1

        shutil.copy2(source_path, target_path)
        applied += 1

    return applied, backed_up


def redact_plan_for_report(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "items": plan["items"],
        "movedOrRenamedCandidates": plan["movedOrRenamedCandidates"],
        "exactDuplicateCandidates": plan["exactDuplicateCandidates"],
        "filenameDuplicateCandidates": plan["filenameDuplicateCandidates"],
    }


def examples(plan: dict[str, Any], limit: int) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in plan["items"]:
        if item["status"] == "unchanged":
            continue
        if len(grouped[item["status"]]) < limit:
            grouped[item["status"]].append({
                "relativePath": item["relativePath"],
                "status": item["status"],
                "fileName": item["fileName"],
            })
    grouped["moved_or_renamed_candidate"] = plan["movedOrRenamedCandidates"][:limit]
    grouped["exact_duplicate_candidate"] = plan["exactDuplicateCandidates"][:limit]
    grouped["filename_duplicate_candidate"] = plan["filenameDuplicateCandidates"][:limit]
    return dict(grouped)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, plan: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "status",
                "relativePath",
                "fileName",
                "sourceFileSize",
                "targetFileSize",
                "sourceSha256",
                "targetSha256",
            ],
        )
        writer.writeheader()
        for item in plan["items"]:
            writer.writerow({
                "status": item.get("status", ""),
                "relativePath": item.get("relativePath", ""),
                "fileName": item.get("fileName", ""),
                "sourceFileSize": item.get("sourceFileSize", ""),
                "targetFileSize": item.get("targetFileSize", ""),
                "sourceSha256": item.get("sourceSha256", ""),
                "targetSha256": item.get("targetSha256", ""),
            })


def report_paths(args: argparse.Namespace, mode: str) -> tuple[Path, Path]:
    default_json = DEFAULT_APPLY_JSON if mode == "apply" else DEFAULT_PREVIEW_JSON
    default_csv = DEFAULT_APPLY_CSV if mode == "apply" else DEFAULT_PREVIEW_CSV
    return args.report_json or default_json, args.report_csv or default_csv


def print_summary(summary: dict[str, Any], json_path: Path, csv_path: Path) -> None:
    print("PDF library sync summary")
    print(f"- Mode: {summary['mode']}")
    print(f"- Source PDF files: {summary['sourcePdfCount']}")
    print(f"- Target PDF files: {summary['targetPdfCount']}")
    print(f"- New files: {summary['newFileCount']}")
    print(f"- Changed same path: {summary['changedSamePathCount']}")
    print(f"- Unchanged: {summary['unchangedCount']}")
    print(f"- Deleted from source: {summary['deletedFromSourceCount']}")
    print(f"- Moved/renamed candidates: {summary['movedOrRenamedCandidateCount']}")
    print(f"- Exact duplicate candidates: {summary['exactDuplicateCandidateCount']}")
    print(f"- Filename duplicate candidates: {summary['filenameDuplicateCandidateCount']}")
    print(f"- Applied copies: {summary['appliedCopyCount']}")
    print(f"- Backed up changed files: {summary['backedUpChangedFileCount']}")
    print(f"- JSON report: {json_path}")
    print(f"- CSV report: {csv_path}")
    print("\nNext recommended checks:")
    print("  python scripts/build_pdf_inventory.py")
    print("  python scripts/check_pdf_links.py --data data/msds.local.json --pdf-dir pdf")
    print("  python scripts/audit_msds_workflow.py")


def run_followup_checks() -> None:
    commands = [
        [sys.executable, "scripts/build_pdf_inventory.py"],
        [sys.executable, "scripts/check_pdf_links.py", "--data", "data/msds.local.json", "--pdf-dir", "pdf"],
        [sys.executable, "scripts/audit_msds_workflow.py"],
    ]
    for command in commands:
        subprocess.run(command, check=False)


def main() -> int:
    args = parse_args()
    if args.apply and args.dry_run:
        raise SystemExit("Use either --dry-run or --apply, not both.")
    mode = "apply" if args.apply else "dry-run"
    source_root = args.source
    target_root = args.target

    source = scan_pdfs(source_root)
    target = scan_pdfs(target_root)
    plan = build_sync_plan(source, target)
    summary = summarize(plan, len(source), len(target), mode)

    if args.apply:
        applied, backed_up = copy_with_backup(plan, source_root, target_root, args.backup_root)
        summary["appliedCopyCount"] = applied
        summary["backedUpChangedFileCount"] = backed_up

    json_path, csv_path = report_paths(args, mode)
    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "source": str(source_root),
            "target": str(target_root),
            "backupRoot": str(args.backup_root),
        },
        "summary": summary,
        "examples": examples(plan, args.example_limit),
        "plan": redact_plan_for_report(plan),
        "safetyNotes": [
            "No PDF is deleted, moved, or renamed by this script.",
            "Apply mode only copies new/changed files and backs up overwritten target files.",
            "Deleted-from-source files are reported only.",
        ],
    }
    write_json(json_path, report)
    write_csv(csv_path, plan)
    print_summary(summary, json_path, csv_path)

    if args.run_audit:
        run_followup_checks()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
