from __future__ import annotations

import csv
import json
import logging
import re
import shutil
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader


logging.getLogger("pypdf").setLevel(logging.CRITICAL)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PDF_DIR = ROOT / "pdf"
REPORTS_DIR = ROOT / "reports"

LOCAL_PRODUCTS_PATH = DATA_DIR / "msds.local.json"
PUBLIC_PRODUCTS_PATH = DATA_DIR / "msds.public.json"
LOCAL_OVERRIDES_PATH = DATA_DIR / "msds-overrides.local.json"
PUBLIC_OVERRIDES_PATH = DATA_DIR / "msds-overrides.public.json"
REPORT_CSV = REPORTS_DIR / "msds-visible-pdf-vs-summary-audit.local.csv"
REPORT_JSON = REPORTS_DIR / "msds-visible-pdf-vs-summary-audit.local.json"

GHS_DEFINITIONS = {
    "GHS01": "폭발성",
    "GHS02": "인화성",
    "GHS03": "산화성",
    "GHS04": "고압가스",
    "GHS05": "부식성",
    "GHS06": "급성독성",
    "GHS07": "유해/자극성",
    "GHS08": "건강유해성",
    "GHS09": "환경유해성",
}

SUPPLIER_HINTS = {
    "극동산업": {
        "company": "㈜극동산업",
        "address": "경기도 오산시 두곡로 32",
        "phone": "031)354-0065",
    },
    "MOBIL코리아": {
        "company": "모빌 코리아 윤활유 주식회사",
        "address": "서울스퀘어빌딩 22층., 416 한강대로, 중구 서울 대한민국",
        "phone": "00-308-13-2549 / +1-703-527-3887 / 공급자 전화번호 82-2-750-8700 / FAX 82-2-750-8751",
    },
    "삼풍트라이텍": {
        "company": "삼풍트라이텍",
        "address": "경기도 화성시 팔탄면 석포로 74번길 10-43",
        "phone": "031)358-1111",
    },
    "현대ep": {
        "company": "HDC 현대EP",
        "address": "",
        "phone": "",
    },
    "FUCHS": {
        "company": "Fuchs Lubritech GmbH",
        "address": "Werner-Heisenberg-Straße 1",
        "phone": "+49 (0) 6301 3206-0",
    },
}

REPORT_COLUMNS = [
    "productName",
    "fileName",
    "pdfPath",
    "pageChecked",
    "supplierVisibleInPdf",
    "supplierShownInSummary",
    "ghsVisibleInPdf",
    "ghsShownInSummary",
    "hazardTextVisibleInPdf",
    "hazardTextShownInSummary",
    "preventionTextVisibleInPdf",
    "preventionTextShownInSummary",
    "issueType",
    "evidenceText",
    "action",
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_spaces(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def normalize_key(value: Any) -> str:
    return re.sub(r"[\W_]+", "", str(value or "").lower())


def normalize_path(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/").lstrip("/")


def supplier_hint_from_product(product: dict[str, Any], pdf_path: Path | None = None) -> dict[str, str]:
    resolved_relative = ""
    if pdf_path and pdf_path.exists():
        try:
            resolved_relative = str(pdf_path.relative_to(PDF_DIR)).replace("\\", "/")
        except ValueError:
            resolved_relative = str(pdf_path).replace("\\", "/")
    values = [product.get(key, "") for key in [
        "productName",
        "fileName",
        "pdfPath",
        "relativePath",
        "sourceRelativePath",
        "emergencyContact",
    ]]
    values.append(resolved_relative)
    text = " ".join(str(value) for value in values)
    for keyword, hint in SUPPLIER_HINTS.items():
        if keyword in text:
            return hint
    path = normalize_path(resolved_relative or product.get("relativePath") or product.get("pdfPath"))
    parts = [part for part in path.replace("pdf/", "", 1).split("/") if part]
    if len(parts) >= 2:
        folder = parts[-2]
        folder = re.sub(r"^\d+_\s*", "", folder)
        folder = re.sub(r"\([^)]*\)", "", folder).strip()
        if folder and not re.search(r"^(?:사출|도장|원재료|기타|data|raw|original)$", folder):
            return {"company": folder, "address": "", "phone": ""}
    return {"company": "", "address": "", "phone": ""}


def merge_supplier_hint(extracted: dict[str, Any], product: dict[str, Any], pdf_path: Path | None = None) -> None:
    supplier = extracted.get("supplier") or {}
    hint = supplier_hint_from_product(product, pdf_path)
    for key in ("company", "address", "phone"):
        needs_hint = not normalize_spaces(supplier.get(key))
        if key == "company" and is_bad_company(supplier.get(key)):
            needs_hint = True
        if needs_hint and normalize_spaces(hint.get(key)):
            supplier[key] = hint[key]
    extracted["supplier"] = supplier


def product_keys(item: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for field in ("fileName", "relativePath", "pdfPath", "sourcePdfPath", "sourceRelativePath"):
        value = normalize_path(item.get(field))
        if not value:
            continue
        keys.add(normalize_key(value))
        keys.add(normalize_key(value.removeprefix("pdf/")))
        keys.add(normalize_key(Path(value).name))
    return {key for key in keys if key}


def build_pdf_index() -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in PDF_DIR.rglob("*.pdf"):
        rel = path.relative_to(PDF_DIR).as_posix()
        for value in (path.name, path.stem, rel, f"pdf/{rel}"):
            index.setdefault(normalize_key(value), path)
    return index


def resolve_pdf_path(product: dict[str, Any], pdf_index: dict[str, Path]) -> Path | None:
    for value in (product.get("pdfPath"), product.get("relativePath"), product.get("sourcePdfPath"), product.get("fileName")):
        raw = normalize_path(value)
        if not raw:
            continue
        for candidate in (ROOT / raw, PDF_DIR / raw.removeprefix("pdf/")):
            if candidate.exists():
                return candidate
        for key in (normalize_key(raw), normalize_key(raw.removeprefix("pdf/")), normalize_key(Path(raw).name)):
            if key in pdf_index:
                return pdf_index[key]
    return None


def extract_pages(path: Path | None, max_pages: int = 3) -> tuple[str, str]:
    if not path:
        return "", ""
    try:
        reader = PdfReader(str(path))
        count = min(len(reader.pages), max_pages)
        chunks = []
        for index in range(count):
            chunks.append(reader.pages[index].extract_text() or "")
        return "\n".join(chunks), f"1-{count}"
    except Exception:
        return "", ""


def clean_lines(text: str) -> list[str]:
    return [normalize_spaces(line) for line in text.splitlines() if normalize_spaces(line)]


def is_bad_company(value: str) -> bool:
    text = normalize_spaces(value)
    if not text or len(text) > 70:
        return True
    if bool(re.search(r"정보|주소|주\s*소|전화|긴급|담당|유해|위험|제품명|용도|제한|예방|구성성분|함유량|행정관청|회사명|그림문자|자료없음|com\s*pany|transfer\s*fluids|straße|street|road|werner-heisenberg", text, re.IGNORECASE)):
        return True
    if text in {"기재", "기재)", "해당없음", "자료없음"}:
        return True
    return bool(re.fullmatch(r"[/\s]*(?:제조자|수입자|유통업자|공급자)+[/\s]*", text))


def clean_supplier_name(value: Any) -> str:
    text = normalize_spaces(value)
    if not text:
        return ""
    text = text.strip(" ,:：")
    text = re.sub(r"^\d+\)\s*", "", text)
    text = re.sub(r"^(?:회사명|공급회사명|Company|Com\s*pany)\s*[:：]?\s*", "", text, flags=re.IGNORECASE)
    text = text.replace("DU KSAN", "DUKSAN").replace("PU RE", "PURE")
    if "DUKSAN PURE CHEMICALS" in text.upper():
        return "DUKSAN PURE CHEMICALS CO. LTD"
    if text.startswith("헨켈코리아유한회사,"):
        return "헨켈코리아유한회사"
    if "Heat transfer fluidsTOTAL" in text or "transfer fluidsTOTAL" in text:
        return "에쓰-오일토탈윤활유"
    if text.startswith("㈜세아에삽") or "세아에삽" in text:
        return "㈜세아에삽"
    return text


def extract_supplier(lines: list[str]) -> dict[str, str]:
    company = ""
    address = ""
    phone = ""
    head = normalize_spaces(" ".join(lines[:130]))
    compact_patterns = [
        r"회사명\s*[:：]\s*(?P<company>.+?)\s*(?:주\s*소|주소)\s*[:：]\s*(?P<address>.+?)\s*(?:전\s*화|전화|TEL)\s*[:：]?\s*(?P<phone>[\d)+\-\s/]+)",
        r"상세정보\s+(?P<company>.+?)\s+(?P<address>(?:서울|경기|경기도|인천|부산|대구|대전|광주|울산|충청|충북|충남|전라|전북|전남|경상|경북|경남|강원|제주).+?)\s+(?:긴급전화번호|공급자 전화번호|전화번호|TEL)\s*(?P<phone>[\d)+\-\s/]+)",
    ]
    for pattern in compact_patterns:
        match = re.search(pattern, head)
        if not match:
            continue
        candidate = normalize_spaces(match.group("company"))
        candidate = re.sub(r"^(?:상세정보|정보제공자)\s*", "", candidate)
        if not is_bad_company(candidate):
            company = candidate
        address = normalize_spaces(match.group("address"))
        phone = normalize_spaces(match.group("phone"))
        break

    for index, line in enumerate(lines[:130]):
        if not company:
            match = re.search(r"(?:회사명|공급자|제조자|제조사|수입자|유통업자)\s*[:：]?\s*(.+)$", line)
            if match:
                candidate = normalize_spaces(match.group(1))
                if not is_bad_company(candidate):
                    company = candidate
            if not company and re.search(r"공급자\s*정보", line):
                for candidate in lines[index + 1:index + 8]:
                    candidate = normalize_spaces(candidate)
                    if candidate in {"상세정보", "다.", "정보"}:
                        continue
                    if re.search(r"주소|전화|FAX|긴급|제품|용도|제\s*2\s*항", candidate):
                        continue
                    if not is_bad_company(candidate):
                        company = candidate
                        break
        if not address:
            match = re.search(r"(?:주소|주\s*소)\s*[:：]?\s*(.+)$", line)
            if match:
                address = normalize_spaces(match.group(1))
            elif company and index < 120:
                for candidate in lines[index + 1:index + 6]:
                    candidate = normalize_spaces(candidate)
                    if re.search(r"^(?:긴급전화번호|공급자 전화번호|전화번호|FAX|제\s*2\s*항)", candidate):
                        break
                    if re.search(r"^(?:서울|경기|경기도|인천|부산|대구|대전|광주|울산|충청|충북|충남|전라|전북|전남|경상|경북|경남|강원|제주)", candidate):
                        address = normalize_spaces(f"{address} {candidate}") if address else candidate
        if not phone:
            match = re.search(r"(?:긴급\s*전화번호|긴급전화번호|긴급\s*연락처|정보제공자|공급자 전화번호|전화번호|전\s*화|TEL)\s*[:：]?\s*(.*)$", line)
            if match:
                candidate = normalize_spaces(match.group(1))
                if not re.search(r"\d{2,4}[-)]?\d{3,4}[-]\d{4}", candidate) and index + 1 < len(lines):
                    candidate = normalize_spaces(f"{candidate} {lines[index + 1]}")
                if re.search(r"\d{2,4}[-)]?\d{3,4}[-]\d{4}", candidate):
                    phone = candidate
    return {"company": company, "address": address, "phone": phone}


def section2_text(lines: list[str]) -> str:
    start = 0
    end = min(len(lines), 120)
    for index, line in enumerate(lines):
        if re.search(r"2\.\s*유\s*해\s*성|2\.\s*유해성|유\s*해\s*성\s*[·ㆍ]\s*위\s*험\s*성|유해성\s*[·ㆍ]\s*위험성", line):
            start = index
            break
    for index in range(start + 1, len(lines)):
        if re.search(r"3\.\s*구성성분|3\.\s*구\s*성\s*성\s*분", lines[index]):
            end = index
            break
    return "\n".join(lines[start:end])


def add_code(codes: list[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def infer_ghs_codes(text: str) -> list[str]:
    compact = re.sub(r"\s+", "", text)
    codes: list[str] = []
    if re.search(r"인화성(?:액체|가스|고체|에어로졸).*구분[1-4]", compact):
        add_code(codes, "GHS02")
    if re.search(r"산화성.*구분[1-3]", compact):
        add_code(codes, "GHS03")
    if re.search(r"고압가스|압축가스|액화가스", compact):
        add_code(codes, "GHS04")
    if re.search(r"피부부식성.*구분1|심한눈손상성.*구분1|금속부식성.*구분1", compact):
        add_code(codes, "GHS05")
    if re.search(r"급성독성.*구분[1-3]", compact):
        add_code(codes, "GHS06")
    if re.search(r"피부.*자극성.*구분2|눈.*자극성.*구분2|급성독성.*구분4|특정표적장기독성\(1회노출\).*구분3", compact):
        add_code(codes, "GHS07")
    if re.search(r"발암성.*구분[12]|생식세포변이원성.*구분[12]|생식독성.*구분[12]|특정표적장기독성\(1회노출\).*구분[12]|특정표적장기독성\(반복노출\).*구분[12]|흡인유해성.*구분1|호흡기과민성.*구분1", compact):
        add_code(codes, "GHS08")
    if re.search(r"수생환경.*유해성.*구분[1-4]|수생생물.*유해", compact):
        add_code(codes, "GHS09")

    for hcode in re.findall(r"\bH\d{3}\b", text.upper()):
        if hcode in {"H226", "H228", "H222"}:
            add_code(codes, "GHS02")
        if hcode in {"H314", "H318"}:
            add_code(codes, "GHS05")
        if hcode in {"H300", "H301", "H310", "H311", "H330", "H331"}:
            add_code(codes, "GHS06")
        if hcode in {"H302", "H312", "H315", "H317", "H319", "H332", "H335"}:
            add_code(codes, "GHS07")
        if hcode in {"H304", "H334", "H340", "H341", "H350", "H351", "H360", "H361", "H370", "H371", "H372", "H373"}:
            add_code(codes, "GHS08")
        if hcode in {"H400", "H410", "H411", "H412"}:
            add_code(codes, "GHS09")
    return codes


def ghs_items(codes: list[str]) -> list[dict[str, str]]:
    return [{"code": code, "label": GHS_DEFINITIONS[code]} for code in codes if code in GHS_DEFINITIONS]


def extract_hazard_lines(text: str) -> list[str]:
    items = []
    for line in clean_lines(text):
        if re.search(r"\bH\d{3}\b", line):
            items.append(line)
    return unique(items)


def extract_precaution_lines(text: str) -> dict[str, list[str]]:
    groups = {"prevention": [], "response": [], "storage": [], "disposal": []}
    current = "prevention"
    for line in clean_lines(text):
        if re.search(r"^\s*대응\b", line):
            current = "response"
        elif re.search(r"^\s*저장\b", line):
            current = "storage"
        elif re.search(r"^\s*폐기\b", line):
            current = "disposal"
        elif re.search(r"^\s*예방\b", line):
            current = "prevention"
        if re.search(r"\bP\d{3}", line):
            groups[current].append(line)
    return {key: unique(value) for key, value in groups.items()}


def extract_ppe_lines(text: str) -> list[str]:
    items = []
    for line in clean_lines(text):
        if re.search(r"P280|P281|보호구|보호장갑|보호의|보안경|안면보호구|호흡보호구", line):
            items.append(line)
    return unique(items)


def extract_signal_word(text: str) -> str:
    compact = re.sub(r"\s+", "", text)
    if re.search(r"신호어[:：]?(위험)", compact):
        return "위험"
    if re.search(r"신호어[:：]?(경고)", compact):
        return "경고"
    return ""


def unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        key = re.sub(r"\s+", "", item)
        if item and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def has_precautions(product: dict[str, Any]) -> bool:
    data = product.get("precautionaryStatements")
    if not isinstance(data, dict):
        return False
    return any(isinstance(value, list) and value for value in data.values())


def has_ghs(product: dict[str, Any]) -> bool:
    return bool(product.get("ghsPictograms") or product.get("ghsCodes") or product.get("classificationGhsCodes"))


def has_hazards(product: dict[str, Any]) -> bool:
    return bool(product.get("hazardStatements"))


def should_replace_emergency_contact(existing: str, supplier: dict[str, str]) -> bool:
    text = normalize_spaces(existing)
    if not text:
        return True
    compact = normalize_key(text)
    company_key = normalize_key(supplier.get("company"))
    address_key = normalize_key(supplier.get("address"))
    if company_key and address_key and company_key in compact and address_key in compact:
        return True
    if supplier.get("phone") and text == supplier.get("phone"):
        return True
    return False


def apply_visible_data(product: dict[str, Any], extracted: dict[str, Any]) -> bool:
    changed = False
    supplier = extracted["supplier"]
    existing_supplier = normalize_spaces(product.get("supplier"))
    cleaned_existing_supplier = clean_supplier_name(existing_supplier)
    if cleaned_existing_supplier and cleaned_existing_supplier != existing_supplier:
        product["supplier"] = cleaned_existing_supplier.replace(" ", "")
        changed = True
        existing_supplier = cleaned_existing_supplier

    cleaned_company = clean_supplier_name(supplier["company"])
    if cleaned_company and (
        not normalize_spaces(product.get("supplier"))
        or is_bad_company(product.get("supplier"))
    ):
        product["supplier"] = cleaned_company.replace(" ", "")
        changed = True
    if supplier["address"] and not normalize_spaces(product.get("supplierAddress")):
        product["supplierAddress"] = supplier["address"]
        changed = True
    if supplier["phone"] and should_replace_emergency_contact(product.get("emergencyContact"), supplier):
        product["emergencyContact"] = f"긴급전화번호 {supplier['phone']}"
        changed = True
    if extracted["signalWord"] and not normalize_spaces(product.get("signalWord")):
        product["signalWord"] = extracted["signalWord"]
        changed = True
    if extracted["ghsCodes"] and not has_ghs(product):
        product["classificationGhsCodes"] = extracted["ghsCodes"]
        product["classificationGhsPictograms"] = ghs_items(extracted["ghsCodes"])
        product["ghsCodes"] = extracted["ghsCodes"]
        product["ghsPictograms"] = ghs_items(extracted["ghsCodes"])
        changed = True
    if extracted["hazardStatements"] and not has_hazards(product):
        product["hazardStatements"] = extracted["hazardStatements"]
        changed = True
    if any(extracted["precautionaryStatements"].values()) and not has_precautions(product):
        product["precautionaryStatements"] = extracted["precautionaryStatements"]
        changed = True
    if extracted["ppeCandidates"] and not product.get("ppeCandidates"):
        product["ppeCandidates"] = extracted["ppeCandidates"]
        changed = True
    return changed


def make_report_rows(product: dict[str, Any], pdf_path: Path | None, pages: str, extracted: dict[str, Any]) -> list[dict[str, str]]:
    supplier_visible = bool(extracted["supplier"]["company"] or extracted["supplier"]["address"] or extracted["supplier"]["phone"])
    supplier_shown = bool(normalize_spaces(product.get("supplier"))) and not is_bad_company(product.get("supplier"))
    ghs_visible = bool(extracted["ghsCodes"])
    ghs_shown = has_ghs(product)
    hazard_visible = bool(extracted["hazardStatements"])
    hazard_shown = has_hazards(product)
    prevention_visible = any(extracted["precautionaryStatements"].values())
    prevention_shown = has_precautions(product)

    checks = [
        ("supplier_display_missing", supplier_visible, supplier_shown, extracted["evidence"].get("supplier", ""), "공급자/주소/긴급연락처 요약 반영"),
        ("ghs_display_missing", ghs_visible, ghs_shown, extracted["evidence"].get("ghs", ""), "유해성 분류 기반 GHS 요약 반영"),
        ("hazard_text_display_missing", hazard_visible, hazard_shown, extracted["evidence"].get("hazard", ""), "H문구 요약 반영"),
        ("prevention_text_display_missing", prevention_visible, prevention_shown, extracted["evidence"].get("prevention", ""), "P문구 요약 반영"),
    ]
    rows = []
    for issue_type, visible, shown, evidence, action in checks:
        if visible and not shown:
            rows.append({
                "productName": product.get("productName", ""),
                "fileName": product.get("fileName", ""),
                "pdfPath": str(pdf_path or product.get("pdfPath", "")),
                "pageChecked": pages or "",
                "supplierVisibleInPdf": str(supplier_visible),
                "supplierShownInSummary": str(supplier_shown),
                "ghsVisibleInPdf": str(ghs_visible),
                "ghsShownInSummary": str(ghs_shown),
                "hazardTextVisibleInPdf": str(hazard_visible),
                "hazardTextShownInSummary": str(hazard_shown),
                "preventionTextVisibleInPdf": str(prevention_visible),
                "preventionTextShownInSummary": str(prevention_shown),
                "issueType": issue_type,
                "evidenceText": evidence[:500],
                "action": action,
            })
    if not pages and product.get("pdfPath"):
        rows.append({
            "productName": product.get("productName", ""),
            "fileName": product.get("fileName", ""),
            "pdfPath": str(pdf_path or product.get("pdfPath", "")),
            "pageChecked": "",
            "supplierVisibleInPdf": "False",
            "supplierShownInSummary": str(supplier_shown),
            "ghsVisibleInPdf": "False",
            "ghsShownInSummary": str(ghs_shown),
            "hazardTextVisibleInPdf": "False",
            "hazardTextShownInSummary": str(hazard_shown),
            "preventionTextVisibleInPdf": "False",
            "preventionTextShownInSummary": str(prevention_shown),
            "issueType": "pdf_text_extraction_failed",
            "evidenceText": "",
            "action": "PDF 텍스트 추출 실패 여부 확인",
        })
    return rows


def extract_visible_data(text: str) -> dict[str, Any]:
    lines = clean_lines(text)
    s2 = section2_text(lines)
    supplier = extract_supplier(lines)
    ghs_codes = infer_ghs_codes(s2)
    signal_word = extract_signal_word(s2)
    hazard_lines = extract_hazard_lines(s2)
    precaution_lines = extract_precaution_lines(s2)
    ppe_lines = extract_ppe_lines(text)
    return {
        "supplier": supplier,
        "signalWord": signal_word,
        "ghsCodes": ghs_codes,
        "hazardStatements": hazard_lines,
        "precautionaryStatements": precaution_lines,
        "ppeCandidates": ppe_lines,
        "evidence": {
            "supplier": " / ".join(value for value in supplier.values() if value),
            "ghs": " / ".join(ghs_codes),
            "hazard": " / ".join(hazard_lines[:4]),
            "prevention": " / ".join(sum((value for value in precaution_lines.values()), [])[:4]),
        },
    }


def backup(path: Path) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = path.with_name(f"{path.stem}.backup.{stamp}{path.suffix}")
    shutil.copy2(path, target)
    return str(target.relative_to(ROOT))


def update_overrides(overrides: list[dict[str, Any]], products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    product_lookup = {}
    for product in products:
        for key in product_keys(product):
            product_lookup.setdefault(key, product)
    result = deepcopy(overrides)
    for override in result:
        target = None
        for key in product_keys(override):
            if key in product_lookup:
                target = product_lookup[key]
                break
        if not target:
            continue
        if target.get("supplier"):
            override["supplierCandidate"] = target.get("supplier", "")
        if target.get("signalWord"):
            override["signalWordCandidate"] = target.get("signalWord", "")
        if target.get("ghsCodes"):
            override["ghsCodes"] = target.get("ghsCodes", [])
            override["ghsPictograms"] = target.get("ghsPictograms", [])
            override["classificationGhsCodes"] = target.get("classificationGhsCodes", target.get("ghsCodes", []))
            override["classificationGhsPictograms"] = target.get("classificationGhsPictograms", target.get("ghsPictograms", []))
        if target.get("hazardStatements"):
            override["hazardStatements"] = target.get("hazardStatements", [])
        if has_precautions(target):
            override["precautionaryStatements"] = target.get("precautionaryStatements", {})
        if target.get("ppeCandidates"):
            override["ppeCandidates"] = target.get("ppeCandidates", [])
    return result


def main() -> int:
    REPORTS_DIR.mkdir(exist_ok=True)
    local_products = read_json(LOCAL_PRODUCTS_PATH)
    if not isinstance(local_products, list):
        raise TypeError("data/msds.local.json must be a list.")

    backups = [backup(LOCAL_PRODUCTS_PATH), backup(LOCAL_OVERRIDES_PATH)]
    products = deepcopy(local_products)
    pdf_index = build_pdf_index()
    rows: list[dict[str, str]] = []
    changed = 0

    for product in products:
        pdf_path = resolve_pdf_path(product, pdf_index)
        text, pages = extract_pages(pdf_path, max_pages=3)
        extracted = extract_visible_data(text) if text else {
            "supplier": {"company": "", "address": "", "phone": ""},
            "signalWord": "",
            "ghsCodes": [],
            "hazardStatements": [],
            "precautionaryStatements": {"prevention": [], "response": [], "storage": [], "disposal": []},
            "ppeCandidates": [],
            "evidence": {},
        }
        merge_supplier_hint(extracted, product, pdf_path)
        if extracted["supplier"].get("company") or extracted["supplier"].get("address") or extracted["supplier"].get("phone"):
            extracted.setdefault("evidence", {})["supplier"] = " / ".join(
                value for value in extracted["supplier"].values() if value
            )
        rows.extend(make_report_rows(product, pdf_path, pages, extracted))
        if apply_visible_data(product, extracted):
            changed += 1

    local_overrides = read_json(LOCAL_OVERRIDES_PATH)
    updated_overrides = update_overrides(local_overrides, products) if isinstance(local_overrides, list) else local_overrides

    write_json(LOCAL_PRODUCTS_PATH, products)
    write_json(PUBLIC_PRODUCTS_PATH, products)
    write_json(LOCAL_OVERRIDES_PATH, updated_overrides)
    write_json(PUBLIC_OVERRIDES_PATH, updated_overrides)

    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    write_json(REPORT_JSON, {"generatedAt": datetime.now().isoformat(timespec="seconds"), "backups": backups, "changedProducts": changed, "issueCount": len(rows), "issues": rows})

    print("Visible PDF vs summary audit complete")
    print(f"- products: {len(products)}")
    print(f"- changedProducts: {changed}")
    print(f"- issueCountBeforeApply: {len(rows)}")
    print(f"- report: {REPORT_CSV.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
