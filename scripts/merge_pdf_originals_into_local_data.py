from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"

LOCAL_DATA = DATA_DIR / "msds.local.json"
OVERRIDES = DATA_DIR / "msds-overrides.local.json"
INVENTORY = DATA_DIR / "pdf-inventory.local.json"

IGNORED_SUPPLIER_FOLDERS = {"00_ 사출", "ggm 상주원", "pdf"}
SUPPLIER_BY_FILE_NAME = {
    "증류수(물).pdf": "삼전순약공업",
    "연기 감지기 MSDS.pdf": "동화엔지니어링",
}

BAD_NAME_TERMS = [
    "제품의권고용도",
    "권고용도",
    "사용상의제한",
    "제조자",
    "공급자",
    "전화번호",
    "긴급연락",
    "작성일자",
    "개정일자",
    "유해성",
    "위험성",
    "예방조치",
    "응급조치",
    "취급",
    "저장",
    "자기반응성",
    "제품명를기재",
    "제품명을기재",
    "화학제품과회사에관한정보",
    "구성성분",
    "그림문자",
    "제품형태",
    "혼합물",
    "완제품",
    "물질안전보건자료",
]


def load_items(path: Path, keys: tuple[str, ...]) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def normalize_text(value: object) -> str:
    return re.sub(r"[\s\W_]+", "", str(value or "").lower())


def basename(path: object) -> str:
    text = str(path or "").replace("\\", "/").strip()
    return text.rsplit("/", 1)[-1] if text else ""


def normalize_pdf_path(path: object) -> str:
    value = str(path or "").strip().replace("\\", "/")
    if not value:
        return ""
    if value.startswith("/pdf/"):
        return value[1:]
    if value.startswith("pdf/"):
        return value
    if value.startswith("/"):
        return value[1:]
    return f"pdf/{value.removeprefix('pdf/')}"


def identity_key(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if re.fullmatch(r"[a-fA-F0-9]{64}", text):
        return f"hash:{text.lower()}"
    return normalize_text(basename(text) or text)


def product_pdf_keys(product: dict) -> set[str]:
    keys = {
        identity_key(product.get("sha256")),
        identity_key(product.get("fileName")),
        identity_key(product.get("pdfPath")),
        identity_key(product.get("relativePath")),
        identity_key(product.get("sourceRelativePath")),
        identity_key(product.get("sourcePdfPath")),
    }
    return {key for key in keys if key}


def override_pdf_keys(override: dict) -> set[str]:
    match = override.get("match") or {}
    keys = {
        identity_key(match.get("fileName")),
        identity_key(match.get("relativePath")),
        identity_key(override.get("sourceRelativePath")),
        identity_key(override.get("sourcePdfPath")),
    }
    return {key for key in keys if key}


def inventory_pdf_keys(item: dict) -> set[str]:
    keys = {
        identity_key(item.get("sha256")),
        identity_key(item.get("firstPagesTextFingerprint")),
        identity_key(item.get("relativePath")),
        identity_key(item.get("pdfPath")),
        identity_key(item.get("fileName")),
        identity_key(item.get("normalizedFileName")),
    }
    return {key for key in keys if key}


def product_signature(product: dict) -> str:
    name = normalize_text(product.get("productName"))
    supplier = normalize_company(product.get("supplier") or product.get("manufacturer") or "")
    cas_values = []
    for component in product.get("components") or product.get("ingredients") or []:
        cas = str(component.get("casNo") or "").strip()
        if cas:
            cas_values.append(cas)
    cas_key = ",".join(sorted(cas_values[:5]))
    return "|".join([name, normalize_text(supplier), cas_key])


def should_exclude_pdf(item: dict) -> bool:
    text = " ".join(
        str(item.get(key) or "")
        for key in ["fileName", "relativePath", "pdfPath", "normalizedFileName", "inventoryStatus", "textExtractStatus"]
    ).lower()
    return any(token in text for token in ["qr", "non-msds", "nonmsds", "비msds", "제외"])


def is_reliable_name(value: object) -> bool:
    text = str(value or "").strip()
    normalized = normalize_text(text)
    if not text or len(text) > 80 or len(normalized) > 70:
        return False
    if not re.search(r"[0-9A-Za-z가-힣]", text) or len(normalized) <= 1:
        return False
    if any(term in normalized for term in BAD_NAME_TERMS):
        return False
    if re.search(r"(^|\s)([2-9]|1[0-6])\s*[.)]", text):
        return False
    if re.search(r"(^|\s)[가-하]\s*[.)]", text):
        return False
    if re.search(r"(TEL|FAX|E-?mail|http|www\.|주소|경기도|서울|전화|팩스|@)", text, re.I):
        return False
    if re.search(r"\d{2,4}[-.)]\d{2,4}[-.)]\d{2,4}", text):
        return False
    if re.search(r"[가-힣]{12,}", text) and " " not in text:
        return False
    if len(re.findall(r"[.:;,/|]", text)) >= 5:
        return False
    return True


def clean_name(value: object) -> str:
    text = str(value or "").strip()
    if not is_reliable_name(text):
        return ""
    return re.sub(r"\s+", " ", text).strip().rstrip(":：")


def bracket_prefix(text: str) -> str:
    match = re.match(r"^\[([^\]]+)\]\s*(.+)$", text)
    if not match:
        return text
    prefix, rest = match.groups()
    if normalize_text(rest).startswith(normalize_text(prefix)):
        return rest
    return f"{prefix} {rest}"


def clean_file_name(file_name: object) -> str:
    text = re.sub(r"\.pdf$", "", str(file_name or "").strip(), flags=re.I)
    text = bracket_prefix(text)
    text = text.replace("_", " ")
    text = re.sub(r"\b(MSDS|GHS|KOR|KOREAN|국문)\b", " ", text, flags=re.I)
    text = re.sub(r"\bmaterial\s+safety\s+data\s+sheet\b", " ", text, flags=re.I)
    text = re.sub(r"\d{8}", " ", text)
    text = re.sub(r"\d{4}[-_.]\d{1,2}[-_.]\d{1,2}", " ", text)
    text = re.sub(r"\d{2}[-_.]\d{1,2}[-_.]\d{1,2}", " ", text)
    text = re.sub(r"\d{4}\.\d{1,2}\.\d{1,2}\s*\([^)]*\)", " ", text)
    text = re.sub(r"\((?:최초|\d+\s*차|개정|rev\.?\s*\d*)\)", " ", text, flags=re.I)
    text = re.sub(r"\bver(?:sion)?\s*\d+[a-z]?\b", " ", text, flags=re.I)
    text = re.sub(r"\brev(?:ision)?\.?\s*\d+[a-z]?\b", " ", text, flags=re.I)
    text = re.sub(r"\d+\s*차\s*개정", " ", text)
    text = re.sub(r"\s+[-–—]\s+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    compact = normalize_text(text)
    if "캉가루구두약가정용" in compact:
        return "캉가루 구두약 (가정용)"
    if "피비원pb1" in compact:
        return "피비원(PB-1)"
    if "썬라이타가스" in compact or "썬라이터가스" in compact:
        return "썬 라이타 가스"

    text = re.sub(r"^.*?(GHP\s+[A-Z0-9][A-Z0-9\s.-]*\d(?:\s*\([^)]*\))?)$", r"\1", text, flags=re.I)
    text = re.sub(r"^.*?(S-\d{2,}(?:\.\d+[A-Z0-9]*)?)$", r"\1", text, flags=re.I)
    for term in ["구두약", "세척제", "접착제", "이형제", "방청제", "스프레이", "실리콘", "프라이머", "신너"]:
        text = re.sub(rf"([^\s(])({term})", rf"\1 \2", text)
    text = re.sub(r"\s+(가정용|공업용|업소용)$", r" (\1)", text)
    text = re.sub(r"\(([A-Za-z]+)\s+(\d+)\)", r"(\1-\2)", text)
    text = re.sub(r"\(\s*\)", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or str(file_name or "").strip()


def clean_supplier(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text or len(normalize_text(text)) <= 1:
        return ""
    if re.search(r"(유통업자 정보|수입품|긴급 연락|정보 기재|전화|팩스|TEL|FAX|주소|@|http)", text, re.I):
        return ""
    text = re.sub(r"^(회사명|회사명\s*:|정보\s*:)\s*", "", text).strip()
    if text in {"정보", "회사", "공급자", "제조자"}:
        return ""
    if len(text) > 60:
        return ""
    return normalize_company_display(text)


def supplier_from_file_name(file_name: object) -> str:
    text = str(file_name or "").strip()
    match = re.match(r"^\[([^\]]+)\]", text)
    if match:
        return normalize_company_display(match.group(1))
    return ""


def supplier_from_folder(path: object, file_name: object = "") -> str:
    value = str(path or "").replace("\\", "/").strip()
    folders = value.split("/")[:-1]
    for folder in reversed(folders):
        cleaned = normalize_company_display(folder)
        if cleaned and cleaned.lower() not in IGNORED_SUPPLIER_FOLDERS:
            return cleaned
    return supplier_from_file_name(file_name)


def normalize_company(value: object) -> str:
    text = str(value or "")
    text = re.sub(r"\(주\)|㈜|주식회사|\(주식회사\)", "", text)
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"\s+", "", text).lower()
    aliases = {
        "케이씨씨": "kcc",
        "kcc": "kcc",
        "한일루켐": "한일루켐",
        "현대종합금속": "현대종합금속",
    }
    return aliases.get(text, text)


def normalize_company_display(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    text = re.sub(r"\(주\)|㈜|주식회사|\(주식회사\)", "", text).strip()
    text = re.sub(r"\((?:그리스|구두약|파워피엔비|Bullsone)\)", "", text).strip()
    if normalize_company(text) == "kcc":
        return "KCC"
    return text


def clean_revision(value: object) -> str:
    text = str(value or "").strip()
    if not text or re.search(r"(개정횟수|최종\s*개정일자|작성일자|자료\s*없음)", text):
        return ""
    return text if len(text) < 40 else ""


def normalize_components(items: list[dict]) -> list[dict]:
    components = []
    for item in items or []:
        component = {
            "chemicalName": item.get("chemicalName") or "",
            "casNo": item.get("casNo") or "",
            "content": item.get("content") or "",
            "controlledSubstance": item.get("controlledSubstance") or item.get("managementTarget") or "",
            "workEnvironmentMeasurement": item.get("workEnvironmentMeasurement") or item.get("workplaceMonitoringTarget") or "",
            "specialHealthExam": item.get("specialHealthExam") or item.get("specialHealthCheckTarget") or "",
        }
        if any(component.values()):
            components.append(component)
    return components


def find_override_for_item(item: dict, overrides: list[dict]) -> dict | None:
    keys = inventory_pdf_keys(item)
    for override in overrides:
        if keys & override_pdf_keys(override):
            return override
    return None


def build_pdf_sources(inventory: list[dict], overrides: list[dict]) -> list[dict]:
    sources = list(inventory)
    for override in overrides:
        match = override.get("match") or {}
        source_path = override.get("sourceRelativePath") or override.get("sourcePdfPath") or match.get("relativePath") or match.get("fileName") or ""
        file_name = basename(source_path)
        if not file_name and not source_path:
            continue
        sources.append(
            {
                "fileName": file_name,
                "relativePath": source_path,
                "pdfPath": source_path,
                "normalizedFileName": file_name,
                "productNameCandidates": [override.get("productNameCandidate")] if override.get("productNameCandidate") else [],
                "msdsNoCandidates": [override.get("msdsNoCandidate")] if override.get("msdsNoCandidate") else [],
                "inventoryStatus": override.get("extractStatus") or "",
            }
        )
    return sources


def base_products_only(products: list[dict]) -> list[dict]:
    return [
        product
        for product in products
        if product.get("dataSource") != "msds_pdf" and not str(product.get("id") or "").startswith("msds-pdf-")
    ]


def best_product_name(item: dict, override: dict, file_name: str) -> str:
    override_name = clean_name(override.get("productNameCandidate"))
    if override_name:
        return override_name
    for name in item.get("productNameCandidates") or []:
        cleaned = clean_name(name)
        if cleaned:
            return cleaned
    return clean_file_name(file_name)


def build_absorbed_product(item: dict, override: dict | None, index: int) -> tuple[dict, dict]:
    override = override or {}
    file_name = item.get("fileName") or basename(item.get("relativePath") or item.get("pdfPath")) or f"MSDS {index + 1}"
    relative_path = item.get("relativePath") or item.get("pdfPath") or file_name
    product_name = best_product_name(item, override, file_name)
    supplier = (
        SUPPLIER_BY_FILE_NAME.get(file_name)
        or clean_supplier(override.get("supplierCandidate"))
        or supplier_from_folder(relative_path, file_name)
        or "업체 미확인"
    )
    revision_date = clean_revision(override.get("revisionDateCandidate"))
    components = normalize_components(override.get("ingredients") or [])
    sha = item.get("sha256") or hashlib.sha1(str(relative_path).encode("utf-8")).hexdigest()
    product = {
        "id": f"msds-pdf-{sha[:16]}",
        "productName": product_name,
        "erpName": "",
        "msdsNo": override.get("msdsNoCandidate") or (item.get("msdsNoCandidates") or [""])[0],
        "fileName": file_name,
        "pdfPath": normalize_pdf_path(relative_path),
        "relativePath": relative_path.removeprefix("/pdf/").removeprefix("pdf/"),
        "useCategory": "",
        "recommendedUse": "",
        "supplier": supplier,
        "emergencyContact": "",
        "hazardSummary": "",
        "dangerousGoods": "",
        "ppeSummary": "",
        "revisionDate": revision_date,
        "hazardBadge": "MSDS",
        "ghsCodes": override.get("ghsCodes") or [],
        "ghsPictograms": override.get("ghsPictograms") or [],
        "labelGhsCodes": override.get("labelGhsCodes") or [],
        "labelGhsPictograms": override.get("labelGhsPictograms") or [],
        "classificationGhsCodes": override.get("classificationGhsCodes") or [],
        "classificationGhsPictograms": override.get("classificationGhsPictograms") or [],
        "hazardStatements": override.get("hazardStatements") or [],
        "precautionaryStatements": override.get("precautionaryStatements") or {},
        "ppeCandidates": override.get("ppeCandidates") or [],
        "components": components,
        "ingredients": components,
        "dataSource": "msds_pdf",
        "sourcePdfPath": normalize_pdf_path(relative_path),
    }
    report = {
        "fileName": file_name,
        "relativePath": product["relativePath"],
        "productName": product_name,
        "supplier": supplier,
        "revisionDate": revision_date,
        "components": len(components),
        "ghsCount": len(product["ghsCodes"] or product["ghsPictograms"] or []),
        "hazardStatementCount": len(product["hazardStatements"]),
        "source": "absorbed_pdf",
    }
    return product, report


def main() -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    products = load_items(LOCAL_DATA, ("products",))
    base_products = base_products_only(products)
    overrides = load_items(OVERRIDES, ("overrides",))
    inventory = load_items(INVENTORY, ("items", "pdfs", "inventory"))
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = DATA_DIR / f"msds.local.backup.{timestamp}.json"
    shutil.copy2(LOCAL_DATA, backup_path)

    product_keys = set()
    product_signatures = set()
    for product in base_products:
        product_keys.update(product_pdf_keys(product))
        sig = product_signature(product)
        if sig.strip("|"):
            product_signatures.add(sig)

    seen_keys = set()
    absorbed = []
    absorbed_reports = []
    duplicate_reports = []
    uncertain_reports = []

    for item in build_pdf_sources(inventory, overrides):
        if should_exclude_pdf(item):
            continue
        keys = inventory_pdf_keys(item)
        if not keys:
            continue
        if keys & product_keys:
            duplicate_reports.append({"fileName": item.get("fileName"), "reason": "matched_existing_product_pdf"})
            continue
        if keys & seen_keys:
            duplicate_reports.append({"fileName": item.get("fileName"), "reason": "duplicate_pdf_source"})
            continue
        override = find_override_for_item(item, overrides)
        product, report = build_absorbed_product(item, override, len(absorbed))
        sig = product_signature(product)
        if sig.strip("|") and sig in product_signatures:
            duplicate_reports.append({"fileName": item.get("fileName"), "reason": "same_product_supplier_signature"})
            continue
        seen_keys.update(keys)
        product_keys.update(keys)
        if sig.strip("|"):
            product_signatures.add(sig)
        if product["supplier"] == "업체 미확인":
            uncertain_reports.append({"fileName": product["fileName"], "reason": "supplier_unresolved"})
        absorbed.append(product)
        absorbed_reports.append(report)

    merged_products = base_products + absorbed
    LOCAL_DATA.write_text(json.dumps(merged_products, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "timestamp": timestamp,
        "backupPath": str(backup_path.relative_to(ROOT)),
        "existingProductCount": len(base_products),
        "pdfInventoryCount": len(inventory),
        "absorbedPdfOnlyCount": len(absorbed),
        "duplicateExcludedCount": len(duplicate_reports),
        "finalProductCount": len(merged_products),
        "supplierUnresolvedCount": len(uncertain_reports),
        "absorbed": absorbed_reports,
        "duplicates": duplicate_reports,
        "uncertain": uncertain_reports,
        "companyNormalizationExamples": [
            {"from": "한일루켐(주) / 한일루켐 주식회사 / 한일루켐㈜", "to": "한일루켐"},
            {"from": "케이씨씨 / KCC", "to": "KCC"},
            {"from": "캉가루(구두약)", "to": "캉가루"},
        ],
    }
    report_json = REPORTS_DIR / "msds-pdf-merge.local.json"
    report_csv = REPORTS_DIR / "msds-pdf-merge.local.csv"
    report_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    with report_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "fileName",
                "relativePath",
                "productName",
                "supplier",
                "revisionDate",
                "components",
                "ghsCount",
                "hazardStatementCount",
                "source",
            ],
        )
        writer.writeheader()
        writer.writerows(absorbed_reports)

    print(
        json.dumps(
            {key: summary[key] for key in ["backupPath", "existingProductCount", "pdfInventoryCount", "absorbedPdfOnlyCount", "duplicateExcludedCount", "finalProductCount", "supplierUnresolvedCount"]},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
