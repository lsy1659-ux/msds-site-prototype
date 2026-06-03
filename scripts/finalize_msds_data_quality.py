from __future__ import annotations

import csv
import json
import re
import shutil
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PDF_DIR = ROOT / "pdf"
REPORTS_DIR = ROOT / "reports"

LOCAL_PRODUCTS_PATH = DATA_DIR / "msds.local.json"
LOCAL_OVERRIDES_PATH = DATA_DIR / "msds-overrides.local.json"
PUBLIC_PRODUCTS_PATH = DATA_DIR / "msds.public.json"
PUBLIC_OVERRIDES_PATH = DATA_DIR / "msds-overrides.public.json"

REPORT_JSON = REPORTS_DIR / "msds-final-data-quality.local.json"
REPORT_CSV = REPORTS_DIR / "msds-final-data-quality.local.csv"

DATE_YMD_RE = re.compile(
    r"(?P<year>19\d{2}|20\d{2})\s*(?:[.\-/]|년)\s*"
    r"(?P<month>\d{1,2})\s*(?:[.\-/]|월)\s*"
    r"(?P<day>\d{1,2})\s*(?:일)?"
)
DATE_DMY_RE = re.compile(
    r"(?P<day>\d{1,2})\s*(?:[.\-/])\s*"
    r"(?P<month>\d{1,2})\s*(?:[.\-/])\s*"
    r"(?P<year>19\d{2}|20\d{2})"
)
DATE_KR_MONTH_RE = re.compile(
    r"(?P<day>\d{1,2})\s*(?P<month>\d{1,2})\s*월\s*(?P<year>19\d{2}|20\d{2})"
)

INVALID_DATE_PATTERNS = [
    re.compile(r"^\s*$"),
    re.compile(r"^\s*-\s*$"),
    re.compile(r"자료\s*없음"),
    re.compile(r"해당\s*없음"),
    re.compile(r"^\s*자\s*:?\s*$"),
    re.compile(r"^\s*년\s*월\s*일\s*$"),
    re.compile(r"^\s*신규\s*생산일\s*$"),
    re.compile(r"^\s*신규생산일\s*$"),
    re.compile(r"^\s*개정\s*횟수\s*$"),
    re.compile(r"^\s*최종\s*개정일\s*$"),
    re.compile(r"개정\s*횟수\s*및\s*최종\s*개정일자"),
    re.compile(r"목록번호\s*최초\s*작성일자\s*최종\s*개정일자"),
]

INVALID_SUPPLIER_PATTERNS = [
    re.compile(r"^\s*$"),
    re.compile(r"^\s*[-.:/]*\s*$"),
    re.compile(r"자료\s*없음"),
    re.compile(r"^\s*정보\s*:?\s*$"),
    re.compile(r"유통업자\s*정보"),
    re.compile(r"공급자\s*/\s*유통업자\s*정보"),
    re.compile(r"권고\s*용도"),
    re.compile(r"보관하시오"),
    re.compile(r"safety\s+data\s+sheet", re.I),
    re.compile(r"information", re.I),
]

INVALID_PRODUCT_NAME_PATTERNS = [
    re.compile(r"권고\s*용도"),
    re.compile(r"사용상의\s*제한"),
    re.compile(r"제품의\s*권고\s*용도"),
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_spaces(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def normalize_key(value: Any) -> str:
    return re.sub(r"[\W_]+", "", str(value or "").lower())


def normalize_name_key(value: Any) -> str:
    return re.sub(r"[\s,，/\\_\-()（）]+", "", str(value or "").lower())


def normalize_path(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/").lstrip("/")


def to_pdf_path(value: Any) -> str:
    text = normalize_path(value)
    if not text:
        return ""
    if text.startswith(("http://", "https://")):
        return text
    return text if text.startswith("pdf/") else f"pdf/{text}"


def is_invalid_date(value: Any) -> bool:
    text = normalize_spaces(value)
    return any(pattern.search(text) for pattern in INVALID_DATE_PATTERNS) or not clean_date(text)


def clean_date(value: Any) -> str:
    text = normalize_spaces(value)
    if any(pattern.search(text) for pattern in INVALID_DATE_PATTERNS):
        return ""
    text = re.sub(r"^(?:최종\s*)?개정\s*일자?\s*[:：]?\s*", "", text)
    text = re.sub(r"^자\s*[:：]?\s*", "", text)

    matches: list[tuple[int, str]] = []

    for match in DATE_YMD_RE.finditer(text):
        matches.append((match.start(), format_date(match.group("year"), match.group("month"), match.group("day"))))
    for match in DATE_DMY_RE.finditer(text):
        matches.append((match.start(), format_date(match.group("year"), match.group("month"), match.group("day"))))
    for match in DATE_KR_MONTH_RE.finditer(text):
        matches.append((match.start(), format_date(match.group("year"), match.group("month"), match.group("day"))))

    if not matches:
        return ""

    return sorted(matches, key=lambda item: item[0])[-1][1]


def format_date(year: str, month: str, day: str) -> str:
    try:
        parsed = date(int(year), int(month), int(day))
        return parsed.isoformat()
    except ValueError:
        return ""


def is_clean_date(value: Any) -> bool:
    text = normalize_spaces(value)
    if not text:
        return True
    try:
        date.fromisoformat(text)
        return True
    except ValueError:
        return False


def is_valid_supplier(value: Any) -> bool:
    text = normalize_spaces(value)
    if len(text) > 80:
        return False
    return not any(pattern.search(text) for pattern in INVALID_SUPPLIER_PATTERNS)


def is_valid_product_name(value: Any) -> bool:
    text = normalize_spaces(value)
    if not text or len(text) > 90:
        return False
    return not any(pattern.search(text) for pattern in INVALID_PRODUCT_NAME_PATTERNS)


def build_pdf_index() -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in PDF_DIR.rglob("*.pdf"):
        keys = {
            normalize_key(path.name),
            normalize_key(path.stem),
            normalize_key(path.relative_to(PDF_DIR).as_posix()),
            normalize_key(f"pdf/{path.relative_to(PDF_DIR).as_posix()}"),
        }
        for key in keys:
            if key:
                index.setdefault(key, path)
    return index


def resolve_pdf_path(item: dict[str, Any], pdf_index: dict[str, Path]) -> Path | None:
    values = [
        item.get("pdfPath"),
        item.get("sourcePdfPath"),
        item.get("relativePath"),
        item.get("sourceRelativePath"),
        item.get("fileName"),
    ]
    match = item.get("match") if isinstance(item.get("match"), dict) else {}
    values.extend([match.get("fileName"), match.get("relativePath")])

    for value in values:
        raw = normalize_path(value)
        if not raw:
            continue
        candidates = [ROOT / raw, PDF_DIR / raw.removeprefix("pdf/")]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        key_values = [
            normalize_key(raw),
            normalize_key(Path(raw).name),
            normalize_key(Path(raw).stem),
        ]
        for key in key_values:
            if key in pdf_index:
                return pdf_index[key]
    return None


def extract_pdf_text(path: Path, max_pages: int = 4) -> str:
    try:
        reader = PdfReader(str(path))
        indexes = list(range(min(len(reader.pages), max_pages)))
        if len(reader.pages) > max_pages:
            indexes.append(len(reader.pages) - 1)
        chunks = []
        for index in dict.fromkeys(indexes):
            chunks.append(reader.pages[index].extract_text() or "")
        return "\n".join(chunks)
    except Exception:
        return ""


def extract_revision_date_from_pdf(path: Path | None) -> str:
    return extract_dates_from_pdf(path).get("revisionDate", "")


def extract_issue_date_from_pdf(path: Path | None) -> str:
    return extract_dates_from_pdf(path).get("issueDate", "")


def extract_dates_from_pdf(path: Path | None) -> dict[str, str]:
    if not path:
        return {"issueDate": "", "revisionDate": ""}
    text = extract_pdf_text(path, max_pages=999)
    if not text:
        return {"issueDate": "", "revisionDate": ""}
    lines = [normalize_spaces(line) for line in text.splitlines() if normalize_spaces(line)]
    issue_scored: list[tuple[int, int, str]] = []
    revision_scored: list[tuple[int, int, str]] = []

    for index, line in enumerate(lines[:260]):
        window = " ".join(lines[index:index + 4])
        date_value = clean_date(window)
        if not date_value:
            continue

        issue_score = 0
        revision_score = 0
        if re.search(r"최초\s*작성|최초작성|작성\s*일자|작성일|제정\s*일자|제정일|date\s+of\s+issue|issue\s+date|preparation\s+date", window, re.I):
            issue_score += 20
        if re.search(r"최종\s*개정|최종개정|개정\s*일자|개정일|revision\s+date|revised|revision", window, re.I):
            revision_score += 20

        # Table-style rows often place the label on the line before the date.
        prev = " ".join(lines[max(0, index - 2):index + 1])
        if re.search(r"최초\s*작성|최초작성|작성\s*일자|작성일|제정\s*일자|제정일", prev, re.I):
            issue_score += 10
        if re.search(r"최종\s*개정|최종개정|개정\s*일자|개정일", prev, re.I):
            revision_score += 10

        if issue_score:
            issue_scored.append((issue_score, index, date_value))
        if revision_score:
            revision_scored.append((revision_score, index, date_value))

    if not issue_scored:
        for index, line in enumerate(lines[:]):
            if not re.search(r"최초\s*작성|최초작성|작성\s*일자|작성일|제정\s*일자|제정일", line, re.I):
                continue
            for next_index in range(index, min(len(lines), index + 90)):
                date_value = clean_date(lines[next_index])
                if date_value:
                    issue_scored.append((30, next_index, date_value))
                    break
            if issue_scored:
                break

    if not revision_scored:
        for index, line in enumerate(lines[:]):
            if not re.search(r"최종\s*개정|최종개정|개정\s*일자|개정일", line, re.I):
                continue
            for next_index in range(index, min(len(lines), index + 8)):
                if re.fullmatch(r"0\s*회|0", lines[next_index]):
                    break
                date_value = clean_date(lines[next_index])
                if date_value:
                    revision_scored.append((30, next_index, date_value))
                    break
            if revision_scored:
                break

    issue_date = sorted(issue_scored, key=lambda item: (item[0], -item[1]))[-1][2] if issue_scored else ""
    revision_date = sorted(revision_scored, key=lambda item: (item[0], -item[1]))[-1][2] if revision_scored else ""
    return {"issueDate": issue_date, "revisionDate": revision_date}


def product_lookup_keys(item: dict[str, Any]) -> set[str]:
    keys = set()
    for field in ("fileName", "relativePath", "pdfPath", "sourcePdfPath", "sourceRelativePath"):
        value = normalize_path(item.get(field))
        if value:
            keys.add(normalize_key(value))
            keys.add(normalize_key(value.removeprefix("pdf/")))
            keys.add(normalize_key(Path(value).name))
            keys.add(normalize_key(Path(value).stem))
    return {key for key in keys if key}


def build_product_lookup(products: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for product in products:
        for key in product_lookup_keys(product):
            lookup.setdefault(key, product)
    return lookup


def find_product_for_override(override: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    for key in product_lookup_keys(override):
        if key in lookup:
            return lookup[key]
    return None


def backup(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = path.with_name(f"{path.stem}.backup.{timestamp}{path.suffix}")
    shutil.copy2(path, target)
    return target


def finalize_products(products: list[dict[str, Any]], pdf_index: dict[str, Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result = deepcopy(products)
    changes: list[dict[str, Any]] = []

    for product in result:
        pdf_path = resolve_pdf_path(product, pdf_index)
        pdf_dates: dict[str, str] | None = None

        before_erp = product.get("erpName", "")
        if before_erp and normalize_name_key(before_erp) == normalize_name_key(product.get("productName", "")):
            product["erpName"] = ""
            changes.append({
                "type": "product_erpName_duplicate",
                "productName": product.get("productName", ""),
                "fileName": product.get("fileName", ""),
                "before": before_erp,
                "after": "",
            })

        before_issue = product.get("issueDate") or product.get("preparationDate") or ""
        clean_issue = clean_date(before_issue)
        if before_issue and clean_issue and clean_issue != before_issue:
            product["issueDate"] = clean_issue
            changes.append({
                "type": "product_issueDate_format",
                "productName": product.get("productName", ""),
                "fileName": product.get("fileName", ""),
                "before": before_issue,
                "after": clean_issue,
            })
        elif not clean_issue:
            pdf_dates = pdf_dates or extract_dates_from_pdf(pdf_path)
            if pdf_dates.get("issueDate"):
                product["issueDate"] = pdf_dates["issueDate"]
                changes.append({
                    "type": "product_issueDate",
                    "productName": product.get("productName", ""),
                    "fileName": product.get("fileName", ""),
                    "before": before_issue,
                    "after": pdf_dates["issueDate"],
                })

        before_revision = product.get("revisionDate", "")
        clean_revision = clean_date(before_revision)
        if before_revision and not clean_revision:
            pdf_dates = pdf_dates or extract_dates_from_pdf(pdf_path)
            clean_revision = pdf_dates.get("revisionDate", "")
            product["revisionDate"] = clean_revision
            changes.append({
                "type": "product_revisionDate",
                "productName": product.get("productName", ""),
                "fileName": product.get("fileName", ""),
                "before": before_revision,
                "after": clean_revision,
            })
        elif not before_revision:
            pdf_dates = pdf_dates or extract_dates_from_pdf(pdf_path)
            if pdf_dates.get("revisionDate"):
                product["revisionDate"] = pdf_dates["revisionDate"]
                changes.append({
                    "type": "product_revisionDate",
                    "productName": product.get("productName", ""),
                    "fileName": product.get("fileName", ""),
                    "before": before_revision,
                    "after": pdf_dates["revisionDate"],
                })
        elif clean_revision and clean_revision != before_revision:
            product["revisionDate"] = clean_revision
            changes.append({
                "type": "product_revisionDate_format",
                "productName": product.get("productName", ""),
                "fileName": product.get("fileName", ""),
                "before": before_revision,
                "after": clean_revision,
            })

        before_supplier = product.get("supplier", "")
        if before_supplier and not is_valid_supplier(before_supplier):
            product["supplier"] = ""
            changes.append({
                "type": "product_supplier",
                "productName": product.get("productName", ""),
                "fileName": product.get("fileName", ""),
                "before": before_supplier,
                "after": "",
            })

    return result, changes


def finalize_overrides(
    overrides: list[dict[str, Any]],
    product_lookup: dict[str, dict[str, Any]],
    pdf_index: dict[str, Path],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result = deepcopy(overrides)
    changes: list[dict[str, Any]] = []

    for override in result:
        product = find_product_for_override(override, product_lookup)

        before_revision = override.get("revisionDateCandidate", "")
        clean_revision = clean_date(before_revision)
        if not clean_revision and product:
            clean_revision = clean_date(product.get("revisionDate", ""))
        if not clean_revision:
            clean_revision = extract_revision_date_from_pdf(resolve_pdf_path(override, pdf_index))
        if before_revision != clean_revision:
            override["revisionDateCandidate"] = clean_revision
            changes.append({
                "type": "override_revisionDateCandidate",
                "productName": override.get("productNameCandidate", "") or (product or {}).get("productName", ""),
                "fileName": (override.get("match") or {}).get("fileName", ""),
                "before": before_revision,
                "after": clean_revision,
            })

        before_supplier = override.get("supplierCandidate", "")
        after_supplier = before_supplier
        if not is_valid_supplier(before_supplier):
            after_supplier = (product or {}).get("supplier", "") if is_valid_supplier((product or {}).get("supplier", "")) else ""
        if before_supplier != after_supplier:
            override["supplierCandidate"] = after_supplier
            changes.append({
                "type": "override_supplierCandidate",
                "productName": override.get("productNameCandidate", "") or (product or {}).get("productName", ""),
                "fileName": (override.get("match") or {}).get("fileName", ""),
                "before": before_supplier,
                "after": after_supplier,
            })

        before_name = override.get("productNameCandidate", "")
        if before_name and not is_valid_product_name(before_name):
            after_name = (product or {}).get("productName", "")
            override["productNameCandidate"] = after_name
            changes.append({
                "type": "override_productNameCandidate",
                "productName": after_name,
                "fileName": (override.get("match") or {}).get("fileName", ""),
                "before": before_name,
                "after": after_name,
            })

    return result, changes


def normalize_public_products(products: list[dict[str, Any]], overrides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    override_lookup = build_product_lookup(overrides)
    output = []
    for product in products:
        item = deepcopy(product)
        override = None
        for key in product_lookup_keys(item):
            if key in override_lookup:
                override = override_lookup[key]
                break
        relative = ""
        if override:
            match = override.get("match") if isinstance(override.get("match"), dict) else {}
            relative = normalize_path(override.get("sourceRelativePath") or match.get("relativePath"))
        if not relative:
            relative = normalize_path(item.get("relativePath") or item.get("sourceRelativePath") or item.get("pdfPath") or item.get("fileName"))
        if relative:
            relative = relative.removeprefix("pdf/")
            item["relativePath"] = relative
            item["pdfPath"] = to_pdf_path(relative)
        output.append(item)
    return output


def normalize_public_overrides(overrides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for override in overrides:
        item = deepcopy(override)
        for field in ("pdfPath", "sourcePdfPath"):
            if item.get(field):
                item[field] = to_pdf_path(item[field])
        for field in ("relativePath", "sourceRelativePath"):
            if item.get(field):
                item[field] = normalize_path(item[field]).removeprefix("pdf/")
        match = item.get("match")
        if isinstance(match, dict):
            item["match"] = deepcopy(match)
            if item["match"].get("relativePath"):
                item["match"]["relativePath"] = normalize_path(item["match"]["relativePath"]).removeprefix("pdf/")
        output.append(item)
    return output


def write_report(changes: list[dict[str, Any]], backups: list[str], counts: dict[str, Any]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "backups": backups,
        "counts": counts,
        "changes": changes,
    }
    write_json(REPORT_JSON, payload)
    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["type", "productName", "fileName", "before", "after"])
        writer.writeheader()
        for change in changes:
            writer.writerow({key: change.get(key, "") for key in writer.fieldnames})


def count_bad_dates(items: list[dict[str, Any]], field: str) -> int:
    return sum(1 for item in items if normalize_spaces(item.get(field, "")) and (is_invalid_date(item.get(field, "")) or not is_clean_date(item.get(field, ""))))


def count_duplicate_erp_names(items: list[dict[str, Any]]) -> int:
    return sum(
        1
        for item in items
        if normalize_spaces(item.get("erpName", ""))
        and normalize_name_key(item.get("erpName", "")) == normalize_name_key(item.get("productName", ""))
    )


def count_missing_issue_dates(items: list[dict[str, Any]]) -> int:
    return sum(1 for item in items if not normalize_spaces(item.get("issueDate") or item.get("preparationDate") or ""))


def main() -> int:
    products = read_json(LOCAL_PRODUCTS_PATH)
    overrides = read_json(LOCAL_OVERRIDES_PATH)
    if not isinstance(products, list) or not isinstance(overrides, list):
        raise TypeError("Expected data/msds.local.json and data/msds-overrides.local.json to be lists.")

    pdf_index = build_pdf_index()
    backups = [str(backup(LOCAL_PRODUCTS_PATH).relative_to(ROOT)), str(backup(LOCAL_OVERRIDES_PATH).relative_to(ROOT))]

    finalized_products, product_changes = finalize_products(products, pdf_index)
    product_lookup = build_product_lookup(finalized_products)
    finalized_overrides, override_changes = finalize_overrides(overrides, product_lookup, pdf_index)
    public_products = normalize_public_products(finalized_products, finalized_overrides)
    public_overrides = normalize_public_overrides(finalized_overrides)

    write_json(LOCAL_PRODUCTS_PATH, finalized_products)
    write_json(LOCAL_OVERRIDES_PATH, finalized_overrides)
    write_json(PUBLIC_PRODUCTS_PATH, public_products)
    write_json(PUBLIC_OVERRIDES_PATH, public_overrides)

    all_changes = product_changes + override_changes
    counts = {
        "products": len(finalized_products),
        "overrides": len(finalized_overrides),
        "publicProducts": len(public_products),
        "duplicateErpNamesAfter": count_duplicate_erp_names(finalized_products),
        "missingIssueDatesAfter": count_missing_issue_dates(finalized_products),
        "badProductRevisionDatesAfter": count_bad_dates(finalized_products, "revisionDate"),
        "badOverrideRevisionDatesAfter": count_bad_dates(finalized_overrides, "revisionDateCandidate"),
        "productChanges": len(product_changes),
        "overrideChanges": len(override_changes),
    }
    write_report(all_changes, backups, counts)

    print("MSDS final data quality pass complete")
    for key, value in counts.items():
        print(f"- {key}: {value}")
    print(f"- report: {REPORT_JSON.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
