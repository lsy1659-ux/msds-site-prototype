from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PRODUCTS_PATH = ROOT / "data" / "msds.local.json"
LOCAL_OVERRIDES_PATH = ROOT / "data" / "msds-overrides.local.json"
PUBLIC_PRODUCTS_PATH = ROOT / "data" / "msds.public.json"
PUBLIC_OVERRIDES_PATH = ROOT / "data" / "msds-overrides.public.json"

PDF_PATH_FIELDS = ("pdfPath", "sourcePdfPath")
PDF_RELATIVE_FIELDS = ("relativePath", "sourceRelativePath")
MATCH_FIELDS = ("fileName", "relativePath")

REVIEW_COMPLETE = "검토완료"
VALID_REVIEW_STATUSES = {"검토필요", REVIEW_COMPLETE, "수정필요", "제외"}
VALID_SIGNAL_WORDS = {"", "위험", "경고", "해당없음"}

# Public data is intentionally an allowlist. New local-only fields must never be
# published merely because they were added to the local source JSON.
PUBLIC_PRODUCT_IDENTITY_FIELDS = (
    "id",
    "productName",
    "erpName",
    "msdsNo",
    "fileName",
    "pdfPath",
    "category",
    "recommendedUse",
    "supplier",
    "siteLabel",
    "issueDate",
    "revisionDate",
)
PUBLIC_PRODUCT_REVIEWED_FIELDS = (
    "emergencyContact",
    "supplierAddress",
    "hazardClassification",
    "dangerousGoods",
    "ppeSummary",
    "ingredients",
    "hazardBadge",
    "signalWord",
    "ghsPictograms",
    "hazardStatements",
    "precautionaryStatements",
    "classificationGhsCodes",
    "classificationGhsPictograms",
    "ghsCodes",
    "ppeCandidates",
    "ghsSource",
)
PUBLIC_OVERRIDE_IDENTITY_FIELDS = (
    "sourcePdfPath",
    "sourceRelativePath",
    "pdfRegistrationType",
)
PUBLIC_OVERRIDE_REVIEWED_FIELDS = (
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
)
PUBLIC_PAYLOAD_META_FIELDS = ("schemaVersion", "generatedAt", "dataCutoffDate")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def to_pdf_path(value: Any) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return ""
    if text.startswith(("http://", "https://")):
        return text
    text = text.lstrip("/")
    if text.startswith("pdf/"):
        return text
    return f"pdf/{text}"


def to_pdf_relative_path(value: Any) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return ""
    text = text.lstrip("/")
    if text.startswith("pdf/"):
        return text[4:]
    return text


def normalize_pdf_fields(item: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(item)

    for field in PDF_PATH_FIELDS:
        if result.get(field):
            result[field] = to_pdf_path(result[field])

    for field in PDF_RELATIVE_FIELDS:
        if result.get(field):
            result[field] = to_pdf_relative_path(result[field])

    match = result.get("match")
    if isinstance(match, dict):
        match = deepcopy(match)
        if match.get("relativePath"):
            match["relativePath"] = to_pdf_relative_path(match["relativePath"])
        result["match"] = match

    return result


def normalize_overrides(overrides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for override in overrides:
        item = normalize_pdf_fields(override)
        relative = item.get("sourceRelativePath") or item.get("match", {}).get("relativePath")
        if relative and not item.get("sourcePdfPath"):
            item["sourcePdfPath"] = to_pdf_path(relative)
        normalized.append(item)
    return normalized


def normalize_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("\\", "/").lstrip("/")


def select_fields(item: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: deepcopy(item[field]) for field in fields if field in item}


def normalize_review_status(value: Any) -> str:
    status = str(value or "").strip()
    return status if status in VALID_REVIEW_STATUSES else "검토필요"


def parse_iso_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def validate_pdf_path(value: Any, root: Path = ROOT) -> str | None:
    """Return an error code when a public PDF path is unsafe or unavailable."""

    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return "PDF_PATH_MISSING"
    if text.startswith(("http://", "https://")):
        return "PDF_PATH_INVALID"

    relative = text.lstrip("/")
    parts = Path(relative).parts
    if not relative.startswith("pdf/") or ".." in parts or "." in parts or Path(relative).suffix.lower() != ".pdf":
        return "PDF_PATH_INVALID"

    target = (root / relative).resolve()
    pdf_root = (root / "pdf").resolve()
    try:
        target.relative_to(pdf_root)
    except ValueError:
        return "PDF_PATH_INVALID"
    if not target.is_file():
        return "PDF_FILE_NOT_FOUND"
    return None


def validate_publication(
    product: dict[str, Any],
    override: dict[str, Any] | None,
    root: Path = ROOT,
) -> tuple[bool, list[str], str]:
    """Validate whether reviewed summary values are safe to publish.

    A human review status is necessary but not sufficient. A reviewed record
    with a date conflict, invalid signal word, or bad PDF path is blocked rather
    than falling back to an extracted candidate.
    """

    review_status = normalize_review_status((override or {}).get("reviewStatus"))
    errors: list[str] = []

    pdf_error = validate_pdf_path(product.get("pdfPath"), root)
    if pdf_error:
        errors.append(pdf_error)

    issue_text = str(product.get("issueDate") or "").strip()
    revision_text = str(product.get("revisionDate") or "").strip()
    issue_date = parse_iso_date(issue_text)
    revision_date = parse_iso_date(revision_text)
    if issue_text and not issue_date:
        errors.append("ISSUE_DATE_INVALID")
    if revision_text and not revision_date:
        errors.append("REVISION_DATE_INVALID")
    if issue_date and revision_date and issue_date > revision_date:
        errors.append("ISSUE_DATE_AFTER_REVISION_DATE")

    if override:
        override_pdf_error = validate_pdf_path(override.get("sourcePdfPath"), root)
        if override_pdf_error:
            errors.append(f"OVERRIDE_{override_pdf_error}")

        candidate_revision = str(override.get("revisionDateCandidate") or "").strip()
        if candidate_revision and not parse_iso_date(candidate_revision):
            errors.append("CANDIDATE_REVISION_DATE_INVALID")
        if candidate_revision and revision_text and candidate_revision != revision_text:
            errors.append("REVISION_DATE_CONFLICT")

        signal_word = str(override.get("signalWordCandidate") or "").strip()
        if signal_word not in VALID_SIGNAL_WORDS:
            errors.append("SIGNAL_WORD_INVALID")

    errors = list(dict.fromkeys(errors))
    approved = review_status == REVIEW_COMPLETE and not errors
    if approved:
        validation_status = "passed"
    elif errors:
        validation_status = "blocked"
    else:
        validation_status = "not_reviewed"
    return approved, errors, validation_status


def build_publication_status(
    override: dict[str, Any] | None,
    approved: bool,
    errors: list[str],
    validation_status: str,
) -> dict[str, Any]:
    status = {
        "reviewStatus": normalize_review_status((override or {}).get("reviewStatus")),
        "approvedForDisplay": approved,
        "validationStatus": validation_status,
        "validationErrors": errors,
    }
    reviewed_at = str((override or {}).get("reviewedAt") or "").strip()
    if approved and reviewed_at:
        status["reviewedAt"] = reviewed_at
    return status


def build_override_lookup(overrides: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for override in overrides:
        match = override.get("match") if isinstance(override.get("match"), dict) else {}
        values = [
            match.get("fileName"),
            match.get("relativePath"),
            override.get("sourceRelativePath"),
            override.get("sourcePdfPath"),
        ]
        for value in values:
            key = normalize_key(value)
            if key:
                lookup.setdefault(key, override)
            if key.startswith("pdf/"):
                lookup.setdefault(key[4:], override)
    return lookup


def find_matching_override(product: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    values = [
        product.get("fileName"),
        product.get("relativePath"),
        product.get("sourceRelativePath"),
        product.get("pdfPath"),
        product.get("sourcePdfPath"),
    ]
    for value in values:
        key = normalize_key(value)
        if key in lookup:
            return lookup[key]
        if key.startswith("pdf/") and key[4:] in lookup:
            return lookup[key[4:]]
    return None


def normalize_products(products: list[dict[str, Any]], overrides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lookup = build_override_lookup(overrides)
    normalized = []

    for product in products:
        item = normalize_pdf_fields(product)
        override = find_matching_override(item, lookup)
        override_relative = None
        if override:
            override_relative = override.get("sourceRelativePath") or override.get("match", {}).get("relativePath")

        if override_relative:
            item["relativePath"] = to_pdf_relative_path(override_relative)
            item["pdfPath"] = to_pdf_path(override_relative)
        elif item.get("relativePath"):
            item["pdfPath"] = to_pdf_path(item["relativePath"])
        elif item.get("pdfPath"):
            item["pdfPath"] = to_pdf_path(item["pdfPath"])
        elif item.get("fileName"):
            item["pdfPath"] = to_pdf_path(item["fileName"])

        normalized.append(item)

    return normalized


def sanitize_match(value: Any) -> dict[str, Any]:
    match = value if isinstance(value, dict) else {}
    return select_fields(match, MATCH_FIELDS)


def build_public_records(
    products: list[dict[str, Any]],
    overrides: list[dict[str, Any]],
    root: Path = ROOT,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    """Create least-privilege public records from local products and overrides."""

    normalized_overrides = normalize_overrides(overrides)
    normalized_products = normalize_products(products, normalized_overrides)
    override_lookup = build_override_lookup(normalized_overrides)
    public_products: list[dict[str, Any]] = []
    public_overrides: list[dict[str, Any]] = []
    emitted_override_ids: set[int] = set()
    stats = {
        "approved": 0,
        "notReviewed": 0,
        "blocked": 0,
        "unmatchedOverridesExcluded": 0,
    }

    for product in normalized_products:
        override = find_matching_override(product, override_lookup)
        approved, errors, validation_status = validate_publication(product, override, root)
        publication = build_publication_status(override, approved, errors, validation_status)

        product_fields = PUBLIC_PRODUCT_IDENTITY_FIELDS
        if approved:
            product_fields += PUBLIC_PRODUCT_REVIEWED_FIELDS
            stats["approved"] += 1
        elif validation_status == "blocked":
            stats["blocked"] += 1
        else:
            stats["notReviewed"] += 1

        public_product = select_fields(product, product_fields)
        if any(error in errors for error in ("PDF_PATH_INVALID", "PDF_FILE_NOT_FOUND", "PDF_PATH_MISSING")):
            public_product.pop("pdfPath", None)
        public_product["publication"] = publication
        public_products.append(public_product)

        if not override or id(override) in emitted_override_ids:
            continue
        emitted_override_ids.add(id(override))
        override_fields = PUBLIC_OVERRIDE_IDENTITY_FIELDS
        if approved:
            override_fields += PUBLIC_OVERRIDE_REVIEWED_FIELDS
        public_override = select_fields(override, override_fields)
        public_override["match"] = sanitize_match(override.get("match"))
        public_override["reviewStatus"] = publication["reviewStatus"]
        public_override["publication"] = deepcopy(publication)
        if any(error.startswith("OVERRIDE_PDF_") for error in errors):
            public_override.pop("sourcePdfPath", None)
            public_override.pop("sourceRelativePath", None)
        public_overrides.append(public_override)

    stats["unmatchedOverridesExcluded"] = len(normalized_overrides) - len(emitted_override_ids)
    return public_products, public_overrides, stats


def coerce_list(data: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return data[key]
    raise ValueError(f"Expected a list or an object with '{key}'.")


def build_payload(source: Any, key: str, items: list[dict[str, Any]]) -> Any:
    if not isinstance(source, dict):
        return items
    payload = {field: deepcopy(source[field]) for field in PUBLIC_PAYLOAD_META_FIELDS if field in source}
    payload[key] = items
    return payload


def main() -> int:
    products_source = read_json(LOCAL_PRODUCTS_PATH)
    overrides_source = read_json(LOCAL_OVERRIDES_PATH)

    products = coerce_list(products_source, "products")
    overrides = coerce_list(overrides_source, "overrides")

    public_products, public_overrides, stats = build_public_records(products, overrides)
    products_payload = build_payload(products_source, "products", public_products)
    overrides_payload = build_payload(overrides_source, "overrides", public_overrides)

    write_json(PUBLIC_PRODUCTS_PATH, products_payload)
    write_json(PUBLIC_OVERRIDES_PATH, overrides_payload)

    print("Public data build complete")
    print(f"- Products: {len(public_products)} -> {PUBLIC_PRODUCTS_PATH.relative_to(ROOT).as_posix()}")
    print(f"- Overrides: {len(public_overrides)} -> {PUBLIC_OVERRIDES_PATH.relative_to(ROOT).as_posix()}")
    print(f"- Approved summaries: {stats['approved']}")
    print(f"- Not reviewed summaries (identity only): {stats['notReviewed']}")
    print(f"- Blocked summaries (identity only): {stats['blocked']}")
    print(f"- Unmatched overrides excluded: {stats['unmatchedOverridesExcluded']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
