from __future__ import annotations

import csv
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PDF_DIR = ROOT / "pdf"
REPORTS_DIR = ROOT / "reports"

LOCAL_DATA = DATA_DIR / "msds.local.json"

REPORT_JSON = REPORTS_DIR / "msds-basic-info-audit.local.json"
REPORT_CSV = REPORTS_DIR / "msds-basic-info-audit.local.csv"
PDF_BY_NAME: dict[str, Path] = {}


BAD_VALUE_TERMS = [
    "제품의 권고 용도",
    "사용상의 제한",
    "공급자 정보",
    "유해성",
    "위험성",
    "예방조치",
    "응급조치",
    "취급 및 저장",
    "구성성분",
    "그림문자",
    "자료없음",
    "해당없음",
]


def load_products() -> list[dict]:
    data = json.loads(LOCAL_DATA.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise TypeError("data/msds.local.json must contain a product list.")
    return data


def normalize_text(value: object) -> str:
    return re.sub(r"[\s\W_]+", "", str(value or "").lower())


def normalize_spaces(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def strip_after_keywords(value: str, keywords: list[str]) -> str:
    result = value
    for keyword in keywords:
        idx = result.find(keyword)
        if idx > 0:
            result = result[:idx]
    return normalize_spaces(result)


def clean_company(value: object) -> str:
    text = normalize_spaces(value)
    text = strip_after_keywords(text, ["주소", "긴급", "전화", "TEL", "Tel", "FAX", "Fax", "담당", "인터넷", "E-mail", "위험", "유해성"])
    text = re.sub(r"^(회사명|업체명|제조자|공급자|제조사|공급업체|Manufacturer|Supplier|Company)\s*[:：]?\s*", "", text, flags=re.I)
    text = re.sub(r"\(주\)|㈜|주식회사|\(주식회사\)", "", text).strip()
    text = re.sub(r"^(회사명\s*)", "", text).strip()
    text = normalize_spaces(text)
    if not text or len(text) > 40:
        return ""
    if re.search(r"(주소|TEL|FAX|http|www\.|@|\d{2,4}-\d{3,4}-\d{4}|제조회사의|정보와동일|/supplier|/distributor|위험|유해성|수입품|정보 기재|국내 공급자)", text, re.I):
        return ""
    if normalize_text(text) in {"정보", "제조자정보", "공급자정보"}:
        return ""
    if normalize_text(text) in {"케이씨씨", "kcc"}:
        return "KCC"
    return text


def clean_product_name(value: object) -> str:
    text = normalize_spaces(value)
    text = re.split(r"\s+[나-하]\.\s*", text)[0]
    text = strip_after_keywords(text, ["제품의 권고", "권고 용도", "사용상의 제한", "공급자 정보", "Section", "PAGE"])
    text = re.sub(r"^(가\.)?\s*(제품명|Product name|Product identifier|Product code|한글명|영문명)\s*[:：]?\s*", "", text, flags=re.I).strip()
    text = normalize_spaces(text)
    if not text or len(text) > 80:
        return ""
    if text.endswith(",") or text.endswith("/"):
        return ""
    if any(term in text for term in BAD_VALUE_TERMS):
        return ""
    if re.search(r"(주소|전화|TEL|FAX|http|www\.|@)", text, re.I):
        return ""
    if len(re.findall(r"[.:;,/|]", text)) >= 5:
        return ""
    return text


def clean_contact(value: object) -> str:
    text = normalize_spaces(value)
    text = re.sub(r"^(긴급전화번호|긴급 전화번호|전화번호|TEL|FAX|담당부서|Contact|Telephone|Emergency phone|Emergency telephone number)\s*[:：]?\s*", "", text, flags=re.I)
    text = strip_after_keywords(text, ["주소", "제품명", "제품의", "유해성", "위험성", "구성성분"])
    text = normalize_spaces(text)
    if not text:
        return ""
    if len(text) > 160:
        phones = re.findall(r"(?:TEL\s*[:：]?\s*)?(?:\+?\d{1,3}[-\s]?)?(?:\(?0\d{1,2}\)?[-\s]?)?\d{3,4}[-\s]\d{3,4}(?:~\d+)?", text, flags=re.I)
        text = " / ".join(dict.fromkeys(normalize_spaces(phone) for phone in phones[:2]))
    if "주소" in text and not re.search(r"\d{2,4}[)-]?\s*\d{3,4}[-)]?\s*\d{4}", text):
        return ""
    if not re.search(r"\d{2,4}[)-]?\s*\d{3,4}[-)]?\s*\d{3,4}", text):
        return ""
    return text[:120]


def clean_revision(value: object) -> str:
    text = normalize_spaces(value)
    if not text:
        return ""
    if "자료없음" in text or "해당없음" in text:
        return ""
    patterns = [
        r"\d{4}[./-]\s*\d{1,2}[./-]\s*\d{1,2}",
        r"\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일",
        r"\d{1,2}[/-]\d{1,2}[/-]\d{4}",
    ]
    dates = []
    for pattern in patterns:
        dates.extend(re.findall(pattern, text))
    if dates:
        return normalize_spaces(dates[-1])
    if re.search(r"(개정|작성|발행|Revision|Issue|Preparation)", text, re.I) and len(text) < 60:
        return text
    return ""


def resolve_pdf_path(product: dict) -> Path | None:
    candidates = [
        product.get("sourcePdfPath"),
        product.get("pdfPath"),
        product.get("relativePath"),
        product.get("fileName"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        value = str(candidate).replace("\\", "/").strip()
        value = value.removeprefix("/pdf/").removeprefix("pdf/")
        path = PDF_DIR / value
        if path.exists():
            return path
        fallback = PDF_BY_NAME.get(normalize_text(Path(value).name))
        if fallback and fallback.exists():
            return fallback
    return None


def extract_pdf_text(path: Path, max_pages: int = 3) -> str:
    reader = PdfReader(str(path))
    chunks = []
    for page in reader.pages[:max_pages]:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def candidate_after_label(line: str, labels: list[str]) -> str:
    for label in labels:
        pattern = rf"{label}\s*[:：]?\s*(.+)$"
        match = re.search(pattern, line, flags=re.I)
        if match:
            value = match.group(1)
            value = re.split(r"\s{2,}|(?=\s+[가-하]\.\s)|(?=주소\s*[:：])|(?=긴급전화번호)|(?=TEL\s*[:：])|(?=FAX\s*[:：])|(?=나\.)", value)[0]
            return value
    return ""


def extract_basic_info(text: str) -> dict:
    lines = [normalize_spaces(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    product_name = ""
    manufacturer = ""
    supplier = ""
    company = ""
    contacts = []
    revision_candidates = []
    issue_candidates = []

    for line in lines[:220]:
        if not product_name:
            product_name = clean_product_name(candidate_after_label(line, [
                r"(?:가\.)?\s*제품명",
                r"제품명\s*및\s*제품\s*코드",
                r"제품의\s*명칭",
                r"Product name",
                r"Product identifier",
                r"Product code",
            ]))

        manufacturer_value = candidate_after_label(line, [
            r"회사명\s*\(제조자\)",
            r"제조자\s*정보",
            r"제조자",
            r"제조사",
            r"Manufacturer",
        ])
        supplier_value = candidate_after_label(line, [
            r"회사명\s*\(공급자\)",
            r"공급자\s*정보",
            r"공급자",
            r"공급업체",
            r"유통업자",
            r"Supplier",
            r"Distributor",
        ])
        company_value = candidate_after_label(line, [
            r"업체명",
            r"회사명",
            r"Company",
            r"Responsible party",
        ])
        if manufacturer_value and not manufacturer:
            manufacturer = clean_company(manufacturer_value)
        if supplier_value and not supplier:
            supplier = clean_company(supplier_value)
        if company_value and not company:
            company = clean_company(company_value)

        if re.search(r"(긴급전화번호|긴급 전화번호|전화번호|TEL|FAX|담당부서|Emergency telephone|Emergency phone|Telephone|Contact)", line, re.I):
            contact = clean_contact(line)
            if contact and contact not in contacts:
                contacts.append(contact)

        if re.search(r"(개정일|개정일자|최종 개정|Revision date|Revised)", line, re.I):
            value = clean_revision(line)
            if value:
                revision_candidates.append(value)
        elif re.search(r"(작성일|작성일자|발행일|제정일|Issue date|Issued Date|Date of issue|Preparation date)", line, re.I):
            value = clean_revision(line)
            if value:
                issue_candidates.append(value)

    if manufacturer and supplier and normalize_text(manufacturer) != normalize_text(supplier):
        final_supplier = f"제조자: {manufacturer} / 공급자: {supplier}"
    else:
        final_supplier = supplier or manufacturer or company

    return {
        "productName": product_name,
        "supplier": final_supplier,
        "emergencyContact": " / ".join(contacts[:2]),
        "revisionDate": (revision_candidates[-1] if revision_candidates else (issue_candidates[-1] if issue_candidates else "")),
    }


def should_apply(field: str, old_value: object, pdf_value: str) -> bool:
    old = normalize_spaces(old_value)
    new = normalize_spaces(pdf_value)
    if not new:
        return False
    if field == "productName":
        if len(normalize_text(new)) <= 1:
            return False
        if old and not (
            normalize_text(old) in normalize_text(new)
            or normalize_text(new) in normalize_text(old)
            or len(normalize_text(old)) <= 3
        ):
            return False
    if field == "supplier" and re.search(r"(제조회사의|정보와동일|/supplier|/distributor|위험|유해성|수입품|정보 기재|국내 공급자)", new, re.I):
        return False
    if field == "emergencyContact" and len(new) > 140:
        return False
    if normalize_text(old) == normalize_text(new):
        return False
    if old == "-" and new:
        return True
    if not old:
        return True
    return True


def main() -> None:
    global PDF_BY_NAME
    REPORTS_DIR.mkdir(exist_ok=True)
    PDF_BY_NAME = {}
    for path in PDF_DIR.rglob("*.pdf"):
        PDF_BY_NAME.setdefault(normalize_text(path.name), path)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = DATA_DIR / f"msds.local.backup.{timestamp}.json"
    shutil.copy2(LOCAL_DATA, backup_path)

    products = load_products()
    report_rows = []
    corrected_counts = {
        "productName": 0,
        "supplier": 0,
        "emergencyContact": 0,
        "revisionDate": 0,
    }
    skipped_count = 0

    for product in products:
        pdf_path = resolve_pdf_path(product)
        row = {
            "id": product.get("id") or "",
            "pdfPath": str(pdf_path.relative_to(ROOT)) if pdf_path else "",
            "oldProductName": product.get("productName") or "",
            "pdfProductName": "",
            "finalProductName": product.get("productName") or "",
            "oldSupplier": product.get("supplier") or "",
            "pdfSupplier": "",
            "finalSupplier": product.get("supplier") or "",
            "oldEmergencyContact": product.get("emergencyContact") or "",
            "pdfEmergencyContact": "",
            "finalEmergencyContact": product.get("emergencyContact") or "",
            "oldRevisionDate": product.get("revisionDate") or "",
            "pdfRevisionDate": "",
            "finalRevisionDate": product.get("revisionDate") or "",
            "correctedFields": "",
            "autoApplied": "N",
            "holdReason": "",
        }

        if not pdf_path:
            row["holdReason"] = "PDF 파일을 찾지 못함"
            skipped_count += 1
            report_rows.append(row)
            continue

        try:
            info = extract_basic_info(extract_pdf_text(pdf_path))
        except Exception as error:
            row["holdReason"] = f"PDF 텍스트 추출 실패: {error}"
            skipped_count += 1
            report_rows.append(row)
            continue

        row["pdfProductName"] = info["productName"]
        row["pdfSupplier"] = info["supplier"]
        row["pdfEmergencyContact"] = info["emergencyContact"]
        row["pdfRevisionDate"] = info["revisionDate"]

        changed = []
        for field, key in [
            ("productName", "productName"),
            ("supplier", "supplier"),
            ("emergencyContact", "emergencyContact"),
            ("revisionDate", "revisionDate"),
        ]:
            pdf_value = info[field]
            if should_apply(field, product.get(key), pdf_value):
                product[key] = pdf_value
                corrected_counts[field] += 1
                changed.append(field)

        row["finalProductName"] = product.get("productName") or ""
        row["finalSupplier"] = product.get("supplier") or ""
        row["finalEmergencyContact"] = product.get("emergencyContact") or ""
        row["finalRevisionDate"] = product.get("revisionDate") or ""
        row["correctedFields"] = ", ".join(changed)
        row["autoApplied"] = "Y" if changed else "N"
        if not changed and not any(info.values()):
            row["holdReason"] = "PDF 핵심 필드 자동 확정값 없음"
        report_rows.append(row)

    LOCAL_DATA.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "timestamp": timestamp,
        "backupPath": str(backup_path.relative_to(ROOT)),
        "totalProducts": len(products),
        "correctedCounts": corrected_counts,
        "autoAppliedRows": sum(1 for row in report_rows if row["autoApplied"] == "Y"),
        "skippedCount": skipped_count,
        "rows": report_rows,
    }
    REPORT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(report_rows[0].keys()) if report_rows else [])
        if report_rows:
            writer.writeheader()
            writer.writerows(report_rows)

    print(json.dumps({key: summary[key] for key in ["backupPath", "totalProducts", "correctedCounts", "autoAppliedRows", "skippedCount"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
