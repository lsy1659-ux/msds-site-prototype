"""Read-only safety validation for the public MSDS release.

The default command only reads the repository and exits non-zero when a public
release invariant is broken.  A manifest is written only when
``--write-manifest`` is explicitly supplied and validation has no errors.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTS = Path("data/msds.public.json")
DEFAULT_OVERRIDES = Path("data/msds-overrides.public.json")
DEFAULT_APP = Path("js/app.js")

VALID_SIGNAL_WORDS = {"", "위험", "경고", "해당없음"}
KNOWN_NON_PRODUCT_PDFS = {"pdf/0. 캠스 msds qr 코드.pdf"}

# Automatic summary fields are public reference information.  The PDF remains
# the source of truth and questionable candidate fields must be removed before
# the release is written.
PRODUCT_SUMMARY_FIELDS = {
    "emergencyContact",
    "supplierAddress",
    "hazardClassification",
    "dangerousGoods",
    "ppeSummary",
    "ingredients",
    "signalWord",
    "ghsPictograms",
    "hazardStatements",
    "precautionaryStatements",
    "classificationGhsCodes",
    "classificationGhsPictograms",
    "ghsCodes",
    "ppeCandidates",
    "ghsSource",
}
OVERRIDE_CANDIDATE_FIELDS = {
    "productNameCandidate",
    "supplierCandidate",
    "msdsNoCandidate",
    "revisionDateCandidate",
    "signalWordCandidate",
    "ghsSource",
    "labelGhsCodes",
    "labelGhsPictograms",
    "classificationGhsCodes",
    "classificationGhsPictograms",
    "ghsCodes",
    "ghsPictograms",
    "hazardStatements",
    "precautionaryStatements",
    "ingredients",
    "ppeCandidates",
}


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    subject: str = ""


class ValidationResult:
    def __init__(self) -> None:
        self.issues: list[ValidationIssue] = []
        self.stats: dict[str, int] = {}

    def add(self, severity: str, code: str, message: str, subject: Any = "") -> None:
        self.issues.append(
            ValidationIssue(severity, code, message, str(subject or ""))
        )

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": not self.errors,
            "errorCount": len(self.errors),
            "warningCount": len(self.warnings),
            "stats": dict(sorted(self.stats.items())),
            "issues": [asdict(issue) for issue in self.issues],
        }


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def coerce_records(payload: Any, key: str, path: Path) -> list[dict[str, Any]]:
    records = payload if isinstance(payload, list) else payload.get(key) if isinstance(payload, dict) else None
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise ValueError(f"{path}: expected a JSON list or an object containing '{key}'")
    return records


def meaningful(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def normalize_key(value: Any) -> str:
    text = str(value or "").strip().replace("\\", "/").lstrip("/")
    return text.casefold()


def path_key_variants(value: Any) -> set[str]:
    key = normalize_key(value)
    if not key:
        return set()
    variants = {key}
    if key.startswith("pdf/"):
        variants.add(key[4:])
    else:
        variants.add(f"pdf/{key}")
    return variants


def parse_iso_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def validate_date_field(
    result: ValidationResult,
    record: dict[str, Any],
    field: str,
    subject: str,
) -> date | None:
    value = str(record.get(field) or "").strip()
    if not value:
        return None
    parsed = parse_iso_date(value)
    if parsed is None:
        result.add("error", "DATE_FORMAT_INVALID", f"{field} must use YYYY-MM-DD: {value}", subject)
    return parsed


def validate_pdf_path(root: Path, value: Any) -> tuple[Path | None, str | None]:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return None, "PDF_PATH_MISSING"
    # ``#`` and ``%`` are legal characters in the company's actual Windows
    # PDF filenames.  The browser layer encodes each path segment, so filesystem
    # validation must not confuse those literal characters with URL syntax.
    if text.startswith(("/", "http://", "https://")) or any(token in text for token in ("?", ":")):
        return None, "PDF_PATH_INVALID"

    pure = PurePosixPath(text)
    if (
        pure.is_absolute()
        or not pure.parts
        or pure.parts[0].casefold() != "pdf"
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.suffix.casefold() != ".pdf"
    ):
        return None, "PDF_PATH_INVALID"

    pdf_root = (root / "pdf").resolve()
    target = root.joinpath(*pure.parts).resolve()
    try:
        target.relative_to(pdf_root)
    except ValueError:
        return None, "PDF_PATH_INVALID"
    if not target.is_file():
        return target, "PDF_FILE_NOT_FOUND"
    return target, None


def publication(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("publication")
    return value if isinstance(value, dict) else {}


def summary_available(record: dict[str, Any]) -> bool:
    meta = publication(record)
    if "summaryAvailable" in meta:
        return meta.get("summaryAvailable") is True
    fields = PRODUCT_SUMMARY_FIELDS | OVERRIDE_CANDIDATE_FIELDS
    return any(meaningful(record.get(field)) for field in fields)


def build_override_lookup(
    overrides: list[dict[str, Any]], result: ValidationResult
) -> tuple[dict[str, dict[str, Any]], dict[int, str]]:
    lookup: dict[str, dict[str, Any]] = {}
    labels: dict[int, str] = {}
    for index, override in enumerate(overrides):
        match = override.get("match") if isinstance(override.get("match"), dict) else {}
        label = str(
            override.get("sourcePdfPath")
            or override.get("sourceRelativePath")
            or match.get("relativePath")
            or match.get("fileName")
            or f"override[{index}]"
        )
        labels[id(override)] = label
        values = (
            override.get("sourcePdfPath"),
            override.get("sourceRelativePath"),
            match.get("relativePath"),
            match.get("fileName"),
        )
        for value in values:
            for key in path_key_variants(value):
                previous = lookup.get(key)
                if previous is not None and previous is not override:
                    result.add(
                        "error",
                        "DUPLICATE_OVERRIDE_MATCH_KEY",
                        "More than one override resolves to the same PDF identity.",
                        value,
                    )
                    continue
                lookup[key] = override
    return lookup, labels


def find_override(product: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    for value in (
        product.get("pdfPath"),
        product.get("relativePath"),
        product.get("sourcePdfPath"),
        product.get("fileName"),
    ):
        for key in path_key_variants(value):
            if key in lookup:
                return lookup[key]
    return None


def read_boolean_config(app_text: str, name: str) -> bool | None:
    match = re.search(rf"\b{re.escape(name)}\s*:\s*(true|false)\b", app_text)
    if not match:
        return None
    return match.group(1) == "true"


def validate_public_release(
    root: Path,
    products_path: Path = DEFAULT_PRODUCTS,
    overrides_path: Path = DEFAULT_OVERRIDES,
    app_path: Path = DEFAULT_APP,
    expected_products: int | None = 223,
) -> ValidationResult:
    """Validate the public dataset and all referenced PDFs without writing files."""

    result = ValidationResult()
    products_file = root / products_path
    overrides_file = root / overrides_path
    app_file = root / app_path

    try:
        products = coerce_records(read_json(products_file), "products", products_file)
        overrides = coerce_records(read_json(overrides_file), "overrides", overrides_file)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        result.add("error", "PUBLIC_DATA_UNREADABLE", str(error))
        return result

    try:
        app_text = app_file.read_text(encoding="utf-8")
    except OSError as error:
        result.add("error", "APP_CONFIG_UNREADABLE", str(error), app_path.as_posix())
        app_text = ""
    allows_automatic_summary = read_boolean_config(app_text, "allowCandidateOverrideDisplay")
    if allows_automatic_summary is None:
        result.add(
            "error",
            "AUTOMATIC_SUMMARY_CONFIG_MISSING",
            "APP_CONFIG.allowCandidateOverrideDisplay must be explicitly configured.",
            app_path.as_posix(),
        )
    elif not allows_automatic_summary:
        result.add(
            "error",
            "AUTOMATIC_SUMMARY_DISPLAY_DISABLED",
            "The field site must display automatic summaries while keeping the PDF-first notice.",
            app_path.as_posix(),
        )

    result.stats.update(
        {
            "products": len(products),
            "overrides": len(overrides),
            "linkedProducts": 0,
            "automaticSummaryProducts": 0,
            "pdfOnlyProducts": 0,
            "dateConflicts": 0,
            "invalidSignalWords": 0,
            "unlinkedPdfFiles": 0,
        }
    )
    if expected_products is not None and len(products) != expected_products:
        result.add(
            "error",
            "PRODUCT_COUNT_MISMATCH",
            f"Expected {expected_products} public products but found {len(products)}.",
            products_path.as_posix(),
        )

    override_lookup, override_labels = build_override_lookup(overrides, result)
    matched_override_ids: set[int] = set()
    product_ids: dict[str, str] = {}
    linked_pdf_keys: dict[str, str] = {}

    for index, product in enumerate(products):
        product_id = str(product.get("id") or "").strip()
        subject = product_id or str(product.get("productName") or f"product[{index}]")
        normalized_id = product_id.casefold()
        if not product_id:
            result.add("error", "PRODUCT_ID_MISSING", "Every public product needs a stable ID.", subject)
        elif normalized_id in product_ids:
            result.add(
                "error",
                "DUPLICATE_PRODUCT_ID",
                f"Duplicate product ID; first seen at {product_ids[normalized_id]}.",
                product_id,
            )
        else:
            product_ids[normalized_id] = subject

        pdf_value = product.get("pdfPath")
        pdf_target, pdf_error = validate_pdf_path(root, pdf_value)
        if pdf_error:
            result.add("error", pdf_error, "Product PDF path is missing, unsafe, or unavailable.", subject)
        else:
            result.stats["linkedProducts"] += 1
            pdf_key = normalize_key(pdf_value)
            if pdf_key in linked_pdf_keys:
                result.add(
                    "error",
                    "DUPLICATE_PRODUCT_PDF",
                    f"Two products link to one PDF; first product: {linked_pdf_keys[pdf_key]}.",
                    subject,
                )
            else:
                linked_pdf_keys[pdf_key] = subject
            file_name = str(product.get("fileName") or "").strip()
            if file_name and pdf_target and file_name != pdf_target.name:
                result.add(
                    "error",
                    "PRODUCT_FILENAME_MISMATCH",
                    f"fileName '{file_name}' does not match PDF '{pdf_target.name}'.",
                    subject,
                )

        override = find_override(product, override_lookup)
        if override is None:
            result.add(
                "error",
                "PRODUCT_OVERRIDE_MISSING",
                "Product has no matching automatic-summary/PDF record.",
                subject,
            )
        else:
            matched_override_ids.add(id(override))

        product_meta = publication(product)
        has_summary = summary_available(product)
        if has_summary:
            result.stats["automaticSummaryProducts"] += 1
        else:
            result.stats["pdfOnlyProducts"] += 1

        if product_meta:
            validation_status = str(product_meta.get("validationStatus") or "")
            validation_warnings = product_meta.get("validationWarnings")
            validation_warnings = validation_warnings if isinstance(validation_warnings, list) else []
            allowed_statuses = {"automatic", "automatic_with_warnings"} if has_summary else {"pdf_only"}
            if validation_status not in allowed_statuses:
                result.add(
                    "error",
                    "AUTOMATIC_SUMMARY_STATUS_INCONSISTENT",
                    "Summary availability and automatic validation status do not agree.",
                    subject,
                )
            if validation_status == "automatic" and validation_warnings:
                result.add(
                    "error",
                    "AUTOMATIC_SUMMARY_WARNING_STATUS_INCONSISTENT",
                    "A warning-free automatic status cannot contain validation warnings.",
                    subject,
                )
            for validation_warning in validation_warnings:
                code = str(validation_warning or "")
                if code == "REVISION_DATE_CONFLICT":
                    result.stats["dateConflicts"] += 1
                if code == "SIGNAL_WORD_INVALID":
                    result.stats["invalidSignalWords"] += 1
                result.add(
                    "warning",
                    f"NORMALIZED_{code or 'FIELD_WARNING'}",
                    "Questionable candidate field was excluded; remaining automatic summary stays available.",
                    subject,
                )

        issue_date = validate_date_field(result, product, "issueDate", subject)
        if issue_date is None and meaningful(product.get("preparationDate")):
            issue_date = validate_date_field(result, product, "preparationDate", subject)
        revision_date = validate_date_field(result, product, "revisionDate", subject)
        if issue_date and revision_date and issue_date > revision_date:
            result.add(
                "error",
                "ISSUE_DATE_AFTER_REVISION_DATE",
                "Initial issue date is later than final revision date.",
                subject,
            )

        product_signal = str(product.get("signalWord") or "").strip()
        if product_signal not in VALID_SIGNAL_WORDS:
            result.stats["invalidSignalWords"] += 1
            result.add(
                "error",
                "SIGNAL_WORD_INVALID",
                f"Published signal word is not allowed: {product_signal!r}.",
                subject,
            )

        if override is not None:
            candidate_revision_text = str(override.get("revisionDateCandidate") or "").strip()
            candidate_revision = None
            if candidate_revision_text:
                candidate_revision = parse_iso_date(candidate_revision_text)
                if candidate_revision is None:
                    result.add(
                        "error",
                        "CANDIDATE_REVISION_DATE_INVALID",
                        f"Invalid candidate date must be removed: {candidate_revision_text}",
                        subject,
                    )
            if revision_date and candidate_revision and revision_date != candidate_revision:
                result.stats["dateConflicts"] += 1
                result.add(
                    "error",
                    "REVISION_DATE_CONFLICT",
                    f"Conflicting candidate date must be removed; product revision is {revision_date}.",
                    subject,
                )

    # Validate public override isolation and every override PDF path.
    for override in overrides:
        subject = override_labels[id(override)]
        _, pdf_error = validate_pdf_path(root, override.get("sourcePdfPath"))
        if pdf_error:
            result.add("error", f"OVERRIDE_{pdf_error}", "Override PDF path is invalid.", subject)

        signal = str(override.get("signalWordCandidate") or "").strip()
        if signal not in VALID_SIGNAL_WORDS:
            result.stats["invalidSignalWords"] += 1
            result.add(
                "error",
                "SIGNAL_WORD_INVALID",
                f"Invalid candidate signal word must be removed: {signal!r}.",
                subject,
            )

        if id(override) not in matched_override_ids:
            key = normalize_key(override.get("sourcePdfPath"))
            if key not in KNOWN_NON_PRODUCT_PDFS:
                result.add(
                    "warning",
                    "UNMATCHED_PUBLIC_OVERRIDE",
                    "Public override is not linked to a public product.",
                    subject,
                )

    actual_pdfs = sorted(
        (path for path in (root / "pdf").rglob("*") if path.is_file() and path.suffix.casefold() == ".pdf"),
        key=lambda path: path.relative_to(root).as_posix().casefold(),
    )
    result.stats["pdfFiles"] = len(actual_pdfs)
    for path in actual_pdfs:
        key = normalize_key(path.relative_to(root).as_posix())
        if key not in linked_pdf_keys and key not in KNOWN_NON_PRODUCT_PDFS:
            result.stats["unlinkedPdfFiles"] += 1
            result.add(
                "error",
                "UNLINKED_PDF_FILE",
                "PDF exists in the public library but is not linked to a product.",
                path.relative_to(root).as_posix(),
            )

    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pdf_library_fingerprint(root: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    count = 0
    total_bytes = 0
    paths = sorted(
        (path for path in (root / "pdf").rglob("*") if path.is_file() and path.suffix.casefold() == ".pdf"),
        key=lambda path: path.relative_to(root).as_posix().casefold(),
    )
    for path in paths:
        relative = path.relative_to(root).as_posix()
        file_hash = sha256_file(path)
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\n")
        count += 1
        total_bytes += path.stat().st_size
    return {"count": count, "totalBytes": total_bytes, "sha256": digest.hexdigest()}


def current_commit(root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ""
    return completed.stdout.strip()


def build_release_manifest(
    root: Path,
    result: ValidationResult,
    products_path: Path = DEFAULT_PRODUCTS,
    overrides_path: Path = DEFAULT_OVERRIDES,
    data_cutoff_date: str = "",
    generated_at: str = "",
    commit_sha: str = "",
) -> dict[str, Any]:
    if result.errors:
        raise ValueError("cannot build a release manifest while validation errors exist")
    if not parse_iso_date(data_cutoff_date):
        raise ValueError("data cutoff date is required in YYYY-MM-DD format")

    products_file = root / products_path
    overrides_file = root / overrides_path
    generated_at = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    data_files = {
        products_path.as_posix(): {
            "bytes": products_file.stat().st_size,
            "sha256": sha256_file(products_file),
        },
        overrides_path.as_posix(): {
            "bytes": overrides_file.stat().st_size,
            "sha256": sha256_file(overrides_file),
        },
    }
    pdf_library = pdf_library_fingerprint(root)
    version_digest = hashlib.sha256(
        "\n".join(item["sha256"] for item in data_files.values()).encode("ascii")
        + pdf_library["sha256"].encode("ascii")
    ).hexdigest()
    manifest: dict[str, Any] = {
        "schemaVersion": 1,
        "version": f"msds-{data_cutoff_date.replace('-', '')}-{version_digest[:8]}",
        "generatedAt": generated_at,
        "dataGeneratedAt": generated_at,
        "dataCutoffDate": data_cutoff_date,
        "productCount": result.stats.get("products", 0),
        "pdfCount": result.stats.get("pdfFiles", 0),
        "automaticSummaryCount": result.stats.get("automaticSummaryProducts", 0),
        "pdfOnlyCount": result.stats.get("pdfOnlyProducts", 0),
        "dataFiles": data_files,
        "pdfLibrary": pdf_library,
        "validation": {"errorCount": 0, "warningCount": len(result.warnings)},
    }
    # A manifest committed in the same revision cannot truthfully contain that
    # commit's SHA (the file contents would change the SHA again). CI/deploy may
    # pass --commit-sha explicitly; local generation relies on the content hash
    # based version above.
    resolved_commit = commit_sha.strip()
    if resolved_commit:
        manifest["commitSha"] = resolved_commit
    return manifest


def check_release_manifest(
    root: Path,
    manifest_path: Path,
    expected: dict[str, Any],
    result: ValidationResult,
) -> None:
    path = root / manifest_path
    try:
        actual = read_json(path)
    except (OSError, json.JSONDecodeError) as error:
        result.add("error", "RELEASE_MANIFEST_UNREADABLE", str(error), manifest_path.as_posix())
        return

    required = (
        "schemaVersion",
        "version",
        "generatedAt",
        "dataCutoffDate",
        "productCount",
        "pdfCount",
        "automaticSummaryCount",
        "pdfOnlyCount",
        "dataFiles",
        "pdfLibrary",
        "validation",
    )
    missing = [field for field in required if not meaningful(actual.get(field))]
    if missing:
        result.add(
            "error",
            "RELEASE_MANIFEST_FIELDS_MISSING",
            "Missing manifest fields: " + ", ".join(missing),
            manifest_path.as_posix(),
        )
    if not parse_iso_date(actual.get("dataCutoffDate")):
        result.add(
            "error",
            "RELEASE_MANIFEST_CUTOFF_INVALID",
            "dataCutoffDate must use YYYY-MM-DD.",
            manifest_path.as_posix(),
        )

    for field in (
        "schemaVersion",
        "version",
        "productCount",
        "pdfCount",
        "automaticSummaryCount",
        "pdfOnlyCount",
        "dataFiles",
        "pdfLibrary",
        "validation",
    ):
        if actual.get(field) != expected.get(field):
            result.add(
                "error",
                "RELEASE_MANIFEST_STALE",
                f"Manifest field '{field}' does not match the current public release.",
                manifest_path.as_posix(),
            )


def print_result(result: ValidationResult, max_issues: int = 50) -> None:
    status = "PASS" if not result.errors else "FAIL"
    print(f"MSDS public release validation: {status}")
    print(
        f"- products={result.stats.get('products', 0)}, "
        f"linked={result.stats.get('linkedProducts', 0)}, "
        f"pdfs={result.stats.get('pdfFiles', 0)}, "
        f"automatic-summaries={result.stats.get('automaticSummaryProducts', 0)}, "
        f"pdf-only={result.stats.get('pdfOnlyProducts', 0)}"
    )
    print(f"- errors={len(result.errors)}, warnings={len(result.warnings)}")
    for issue in result.issues[:max_issues]:
        subject = f" [{issue.subject}]" if issue.subject else ""
        print(f"  {issue.severity.upper()} {issue.code}{subject}: {issue.message}")
    hidden = len(result.issues) - max_issues
    if hidden > 0:
        print(f"  ... {hidden} more issue(s); use --json for the complete result")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--products", type=Path, default=DEFAULT_PRODUCTS)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--app", type=Path, default=DEFAULT_APP)
    parser.add_argument("--expected-products", type=int, default=223)
    parser.add_argument("--strict-warnings", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print the full machine-readable result")
    parser.add_argument("--max-issues", type=int, default=50)
    manifest_group = parser.add_mutually_exclusive_group()
    manifest_group.add_argument("--check-manifest", type=Path)
    manifest_group.add_argument("--write-manifest", type=Path)
    parser.add_argument("--data-cutoff-date", default="")
    parser.add_argument("--commit-sha", default="")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    result = validate_public_release(
        root,
        products_path=args.products,
        overrides_path=args.overrides,
        app_path=args.app,
        expected_products=args.expected_products,
    )

    if args.check_manifest and not result.errors:
        try:
            existing = read_json(root / args.check_manifest)
            cutoff = args.data_cutoff_date or str(existing.get("dataCutoffDate") or "")
            expected = build_release_manifest(
                root,
                result,
                products_path=args.products,
                overrides_path=args.overrides,
                data_cutoff_date=cutoff,
                generated_at=str(existing.get("generatedAt") or ""),
                commit_sha=str(existing.get("commitSha") or ""),
            )
        except (OSError, json.JSONDecodeError, ValueError) as error:
            result.add("error", "RELEASE_MANIFEST_UNREADABLE", str(error), args.check_manifest.as_posix())
        else:
            check_release_manifest(root, args.check_manifest, expected, result)

    if args.write_manifest:
        if result.errors:
            result.add(
                "error",
                "RELEASE_MANIFEST_NOT_WRITTEN",
                "Fix validation errors before generating a release manifest.",
                args.write_manifest.as_posix(),
            )
        else:
            try:
                manifest = build_release_manifest(
                    root,
                    result,
                    products_path=args.products,
                    overrides_path=args.overrides,
                    data_cutoff_date=args.data_cutoff_date,
                    commit_sha=args.commit_sha,
                )
                write_json(root / args.write_manifest, manifest)
            except (OSError, ValueError) as error:
                result.add("error", "RELEASE_MANIFEST_WRITE_FAILED", str(error), args.write_manifest.as_posix())

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_result(result, max(0, args.max_issues))

    if result.errors or (args.strict_warnings and result.warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
