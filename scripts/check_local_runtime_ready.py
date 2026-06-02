from __future__ import annotations

from pathlib import Path


REQUIRED_CODE_FILES = [
    Path("index.html"),
    Path("review.html"),
    Path("js/app.js"),
    Path("js/review.js"),
    Path("css/style.css"),
    Path("data/msds-overrides.sample.json"),
]

LOCAL_RUNTIME_FILES = [
    Path("data/msds.local.json"),
    Path("data/msds-overrides.local.json"),
]

PDF_DIR_CANDIDATES = [
    Path("pdf"),
    Path("pdfs"),
    Path("PDF"),
    Path("PDFs"),
    Path("msds"),
    Path("MSDS"),
    Path("msds-pdf"),
    Path("msds-pdfs"),
    Path("data/raw"),
    Path("data/original"),
]

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


def find_pdf_files(root: Path) -> list[Path]:
    pdfs: list[Path] = []
    for path in root.rglob("*.pdf"):
        if path.is_file() and not is_skipped(path, root):
            pdfs.append(path)
    return sorted(pdfs, key=lambda item: rel(item, root).lower())


def find_pdf_folders(root: Path, pdf_files: list[Path]) -> list[Path]:
    folders: set[Path] = set()
    existing_candidates: list[Path] = []
    for candidate in PDF_DIR_CANDIDATES:
        candidate_path = root / candidate
        if candidate_path.is_dir():
            folders.add(candidate_path)
            existing_candidates.append(candidate_path)

    for pdf_file in pdf_files:
        candidate_parent = next(
            (
                candidate
                for candidate in existing_candidates
                if candidate in pdf_file.parents
            ),
            None,
        )
        if candidate_parent:
            folders.add(candidate_parent)
            continue

        folder = pdf_file.parent
        try:
            parts = folder.relative_to(root).parts
        except (IndexError, ValueError):
            continue
        if len(parts) > 1 and parts[0] == "data":
            first_child = root / parts[0] / parts[1]
        else:
            first_child = root / parts[0]
        if first_child != root:
            folders.add(first_child)

    return sorted(folders, key=lambda item: rel(item, root).lower())


def status_line(ok: bool, label: str, detail: str) -> None:
    status = "정상" if ok else "조치 필요"
    print(f"[{status}] {label}: {detail}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    incoming_dir = root / "incoming"
    reports_dir = root / "reports"

    pdf_files = find_pdf_files(root)
    pdf_folders = find_pdf_folders(root, pdf_files)
    incoming_pdf_count = (
        len([path for path in incoming_dir.rglob("*.pdf") if path.is_file()])
        if incoming_dir.is_dir()
        else 0
    )

    missing_count = 0

    print("MSDS 로컬 실행 환경 점검")
    print("=" * 32)
    print(f"프로젝트 루트: {root}")
    print()

    print("필수 코드 파일")
    for path in REQUIRED_CODE_FILES:
        exists = (root / path).is_file()
        missing_count += 0 if exists else 1
        detail = path.as_posix() if exists else f"{path.as_posix()} 없음"
        status_line(exists, "필수 코드", detail)
    print()

    print("실사용 local 파일")
    for path in LOCAL_RUNTIME_FILES:
        exists = (root / path).is_file()
        missing_count += 0 if exists else 1
        detail = path.as_posix() if exists else f"{path.as_posix()} 없음"
        status_line(exists, "local 파일", detail)
    print()

    pdf_folder_ok = bool(pdf_folders)
    missing_count += 0 if pdf_folder_ok else 1
    pdf_folder_detail = (
        ", ".join(rel(path, root) for path in pdf_folders)
        if pdf_folder_ok
        else "PDF 폴더를 찾지 못했습니다"
    )
    status_line(pdf_folder_ok, "PDF 폴더", pdf_folder_detail)

    incoming_ok = incoming_dir.is_dir()
    missing_count += 0 if incoming_ok else 1
    status_line(
        incoming_ok,
        "incoming 폴더",
        "incoming" if incoming_ok else "incoming 폴더 없음",
    )

    reports_ok = reports_dir.is_dir()
    missing_count += 0 if reports_ok else 1
    status_line(
        reports_ok,
        "reports 폴더",
        "reports" if reports_ok else "reports 폴더 없음",
    )
    print()

    print("파일 수 요약")
    print(f"- 기존 PDF 파일 수: {len(pdf_files)}")
    print(f"- incoming PDF 파일 수: {incoming_pdf_count}")
    print(f"- 조치 필요 항목 수: {missing_count}")
    print()

    if missing_count:
        print("결과: 조치 필요 항목이 있습니다.")
        return 1

    print("결과: 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
