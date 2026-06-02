from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Iterable


SKIP_DIR_NAMES = {
    ".git",
    ".github",
    ".venv",
    "__pycache__",
    "node_modules",
    "incoming",
    "reports",
}


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def is_skipped(path: Path, root: Path) -> bool:
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(part in SKIP_DIR_NAMES for part in parts)


def find_existing_pdfs(root: Path) -> list[Path]:
    pdfs: list[Path] = []
    for path in root.rglob("*.pdf"):
        if path.is_file() and not is_skipped(path, root):
            pdfs.append(path)
    return sorted(pdfs, key=lambda item: rel(item, root).lower())


def find_incoming_pdfs(incoming_dir: Path) -> list[Path]:
    if not incoming_dir.is_dir():
        return []
    return sorted(
        [path for path in incoming_dir.rglob("*.pdf") if path.is_file()],
        key=lambda item: item.as_posix().lower(),
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def append_map(mapping: dict[str, list[Path]], key: str, path: Path) -> None:
    mapping.setdefault(key, []).append(path)


def joined_paths(paths: Iterable[Path], root: Path) -> str:
    return " | ".join(rel(path, root) for path in paths)


def build_report(root: Path) -> list[dict[str, object]]:
    incoming_dir = root / "incoming"
    existing_pdfs = find_existing_pdfs(root)
    incoming_pdfs = find_incoming_pdfs(incoming_dir)

    existing_by_name: dict[str, list[Path]] = {}
    existing_by_hash: dict[str, list[Path]] = {}

    for path in existing_pdfs:
        append_map(existing_by_name, path.name.lower(), path)
        append_map(existing_by_hash, sha256_file(path), path)

    incoming_hashes: dict[Path, str] = {}
    incoming_by_name: dict[str, list[Path]] = {}
    incoming_by_hash: dict[str, list[Path]] = {}

    for path in incoming_pdfs:
        file_hash = sha256_file(path)
        incoming_hashes[path] = file_hash
        append_map(incoming_by_name, path.name.lower(), path)
        append_map(incoming_by_hash, file_hash, path)

    rows: list[dict[str, object]] = []
    for path in incoming_pdfs:
        file_hash = incoming_hashes[path]
        same_name_existing = existing_by_name.get(path.name.lower(), [])
        same_hash_existing = existing_by_hash.get(file_hash, [])
        same_name_incoming = [
            item for item in incoming_by_name.get(path.name.lower(), []) if item != path
        ]
        same_hash_incoming = [
            item for item in incoming_by_hash.get(file_hash, []) if item != path
        ]

        issues: list[str] = []
        matched_paths: list[Path] = []

        if same_name_existing:
            matched_paths.extend(same_name_existing)
            if any(candidate in same_hash_existing for candidate in same_name_existing):
                issues.append("동일 파일명/동일 내용 중복")
            else:
                issues.append("파일명 충돌")

        different_name_same_hash = [
            candidate
            for candidate in same_hash_existing
            if candidate.name.lower() != path.name.lower()
        ]
        if different_name_same_hash:
            matched_paths.extend(different_name_same_hash)
            issues.append("동일 내용 중복 의심")

        if same_name_incoming:
            matched_paths.extend(same_name_incoming)
            issues.append("incoming 내부 파일명 중복")

        if same_hash_incoming:
            matched_paths.extend(same_hash_incoming)
            issues.append("incoming 내부 동일 내용 중복")

        if not issues:
            issues.append("신규 후보")

        unique_matches = []
        seen = set()
        for matched in matched_paths:
            key = rel(matched, root)
            if key not in seen:
                seen.add(key)
                unique_matches.append(matched)

        needs_review = any(issue != "신규 후보" for issue in issues)
        rows.append(
            {
                "incoming_path": rel(path, root),
                "file_name": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": file_hash,
                "status": "확인 필요" if needs_review else "신규 후보",
                "issue": " / ".join(issues),
                "matched_existing_or_incoming_paths": joined_paths(unique_matches, root),
                "recommendation": (
                    "자동 처리 금지, reports 확인 후 수동 판단"
                    if needs_review
                    else "검토 후 정식 PDF 폴더로 수동 반영 가능"
                ),
            }
        )

    return rows


def write_reports(root: Path, rows: list[dict[str, object]]) -> tuple[Path, Path]:
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    csv_path = reports_dir / "incoming-pdf-check.local.csv"
    json_path = reports_dir / "incoming-pdf-check.local.json"

    fieldnames = [
        "incoming_path",
        "file_name",
        "size_bytes",
        "sha256",
        "status",
        "issue",
        "matched_existing_or_incoming_paths",
        "recommendation",
    ]

    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "summary": {
            "incoming_pdf_count": len(rows),
            "needs_review_count": sum(1 for row in rows if row["status"] == "확인 필요"),
            "new_candidate_count": sum(1 for row in rows if row["status"] == "신규 후보"),
        },
        "items": rows,
    }
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")

    return csv_path, json_path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    incoming_dir = root / "incoming"

    print("incoming PDF 점검")
    print("=" * 32)
    print(f"프로젝트 루트: {root}")

    if not incoming_dir.is_dir():
        print("[조치 필요] incoming 폴더가 없습니다.")

    rows = build_report(root)
    csv_path, json_path = write_reports(root, rows)

    needs_review_count = sum(1 for row in rows if row["status"] == "확인 필요")
    new_candidate_count = sum(1 for row in rows if row["status"] == "신규 후보")

    print(f"- incoming PDF 파일 수: {len(rows)}")
    print(f"- 확인 필요: {needs_review_count}")
    print(f"- 신규 후보: {new_candidate_count}")
    print(f"- CSV 보고서: {rel(csv_path, root)}")
    print(f"- JSON 보고서: {rel(json_path, root)}")

    if needs_review_count:
        print("결과: 중복 또는 충돌 의심 항목이 있습니다. 자동 처리하지 마세요.")
        return 1

    print("결과: 점검 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
