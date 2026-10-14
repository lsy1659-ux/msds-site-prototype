"""MSDS 원본 PDF 표준 파일 이름: 회사명_제품명_MSDS_날짜.pdf (2026-10-14 사용자 결정).

- 회사명: data/company-short-names.json 의 짧은 이름(노루오토코팅 → NAC, KNK코팅스 → KNK …).
  공급사 표기가 깨진 제품("Produc", 이메일 주소)도 보관함 폴더 이름으로 맞춘다.
- 날짜: 최종 개정일, 없으면 최초 작성일, 둘 다 없으면 '날짜없음'. 원문에 표시가 없는 날짜는 쓰지 않는다.
- 제품명이 회사명으로 시작하면("3M PN3021 …") 앞의 회사명은 한 번만 쓴다.
- Windows 에서 못 쓰는 글자(\\ / : * ? " < > |)는 '-' 로 바꾼다.

공급사에서 받은 이름 그대로인 새 MSDS 를 정리할 때도 같은 규칙을 쓴다.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "data" / "company-short-names.json"


@lru_cache(maxsize=1)
def _rules() -> list[tuple[re.Pattern, str]]:
    data = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    return [(re.compile(pattern), short) for pattern, short in data["rules"]]


def short_company(supplier: str = "", folder: str = "") -> str:
    # 공급사 표기를 먼저 본다. 폴더 이름은 공급사 표기가 깨졌을 때("Produc", 이메일 주소)만 쓴다
    # ('나바켐, 남방CNA' 폴더의 남방CNA 제품이 나바켐으로 붙지 않게).
    for text in (supplier or "", folder or ""):
        for pattern, short in _rules():
            if pattern.search(text):
                return short
    cleaned = re.sub(r"\(주\)|㈜|주식회사|\(유\)|유한회사", "", supplier or "").strip()
    cleaned = re.sub(r"\s+(본사|\S*공장)$", "", cleaned)
    if cleaned:
        return cleaned
    return re.split(r"[(\\/]", folder or "")[-1].strip() or "회사미상"


def file_date(product: dict) -> str:
    for key in ("revisionDate", "issueDate"):
        digits = re.sub(r"\D", "", str(product.get(key) or ""))
        if len(digits) == 8:
            return digits
    return "날짜없음"


def safe(text: str) -> str:
    text = re.sub(r'[\\/:*?"<>|]', "-", str(text or ""))
    return re.sub(r"\s+", " ", text).strip().rstrip(".")


def standard_name(product: dict, folder: str = "") -> str:
    company = short_company(product.get("supplier", ""), folder)
    name = str(product.get("productName") or "").strip()
    if name.lower().startswith(company.lower() + " "):
        name = name[len(company) + 1:].strip()
    return f"{safe(company)}_{safe(name)}_MSDS_{file_date(product)}.pdf"
