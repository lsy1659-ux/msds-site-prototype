#!/usr/bin/env python
"""Verify selected latest PDF updates against site products and mark their overrides reviewed."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from .finalize_msds_data_quality import build_pdf_index, extract_dates_from_pdf, resolve_pdf_path
except ImportError:  # 직접 스크립트로 실행할 때
    from finalize_msds_data_quality import build_pdf_index, extract_dates_from_pdf, resolve_pdf_path


ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_PATH = ROOT / "data" / "msds.local.json"
OVERRIDES_PATH = ROOT / "data" / "msds-overrides.local.json"
CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


def read_list(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return payload
    for key in ("products", "overrides", "items"):
        if isinstance(payload, dict) and isinstance(payload.get(key), list):
            return payload[key]
    raise ValueError(f"JSON 목록을 찾을 수 없습니다: {path}")


def norm(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file-name", action="append", required=True, help="검증할 PDF 파일명; 여러 번 지정 가능")
    parser.add_argument("--apply", action="store_true", help="검증에 통과한 override를 검토완료 처리")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    products = read_list(PRODUCTS_PATH)
    overrides = read_list(OVERRIDES_PATH)
    pdf_index = build_pdf_index()
    results: list[dict[str, Any]] = []
    selected_overrides: list[dict[str, Any]] = []

    for file_name in args.file_name:
        matching_products = [item for item in products if item.get("fileName") == file_name]
        matching_overrides = [item for item in overrides if (item.get("match") or {}).get("fileName") == file_name]
        errors: list[str] = []
        if not matching_products:
            errors.append("제품 데이터 없음")
        if len(matching_overrides) != 1:
            errors.append(f"override 수량 오류: {len(matching_overrides)}")
        if errors:
            results.append({"fileName": file_name, "status": "failed", "errors": errors})
            continue

        product = matching_products[0]
        override = matching_overrides[0]
        pdf_dates = extract_dates_from_pdf(resolve_pdf_path(product, pdf_index))
        if norm(product.get("issueDate")) != norm(pdf_dates.get("issueDate")):
            errors.append("제품/PDF 최초 작성일 불일치")
        if norm(product.get("revisionDate")) != norm(pdf_dates.get("revisionDate")):
            errors.append("제품/PDF 최종 개정일 불일치")
        if norm(product.get("revisionDate")) != norm(override.get("revisionDateCandidate")):
            errors.append("제품/override 개정일 불일치")
        if not override.get("hazardStatements"):
            errors.append("유해위험문구 없음")
        product_ghs = set(product.get("ghsCodes") or [])
        override_ghs = set(override.get("ghsCodes") or [])
        if not (override_ghs or product_ghs):
            errors.append("GHS 그림문자 정보 없음")

        override_by_cas = {
            str(item.get("casNo") or "").strip(): item
            for item in (override.get("ingredients") or [])
            if isinstance(item, dict)
        }
        for ingredient in product.get("ingredients") or []:
            cas = str(ingredient.get("casNo") or "").strip()
            if not CAS_RE.fullmatch(cas):
                continue
            candidate = override_by_cas.get(cas)
            if not candidate:
                errors.append(f"PDF 추출 성분 누락: {cas}")
                continue
            if norm(ingredient.get("content")) != norm(candidate.get("content")):
                errors.append(f"함유량 불일치: {cas}")

        cumene = override_by_cas.get("98-82-8")
        if not cumene:
            errors.append("큐멘(98-82-8) 누락")

        status = "passed" if not errors else "failed"
        results.append({
            "fileName": file_name,
            "status": status,
            "productCount": len(matching_products),
            "issueDate": product.get("issueDate", ""),
            "revisionDate": product.get("revisionDate", ""),
            "productGhsCodes": sorted(product_ghs),
            "overrideGhsCodes": sorted(override_ghs),
            "ingredientCount": len(product.get("ingredients") or []),
            "cumeneContent": (cumene or {}).get("content", ""),
            "errors": errors,
        })
        if status == "passed":
            selected_overrides.append(override)

    print(json.dumps({"mode": "apply" if args.apply else "dry-run", "results": results}, ensure_ascii=False, indent=2))
    failed = [item for item in results if item["status"] != "passed"]
    if failed:
        return 1
    if not args.apply:
        return 0

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = OVERRIDES_PATH.with_name(f"{OVERRIDES_PATH.stem}.backup.verified-update.{timestamp}{OVERRIDES_PATH.suffix}")
    shutil.copy2(OVERRIDES_PATH, backup)
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    for override in selected_overrides:
        override["reviewStatus"] = "검토완료"
        override["reviewedAt"] = reviewed_at
        override["reviewedBy"] = "Codex 데이터 대조 검토"
        override["reviewedNote"] = "최신 PDF 원문, 등록대장 참고값, 사이트 제품정보의 개정일·CAS·함유량·GHS·유해위험문구 대조 완료"
    OVERRIDES_PATH.write_text(json.dumps(overrides, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"백업: {backup}")
    print(f"검토완료: {len(selected_overrides)}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
