"""MSDS 번호 관리대장(data/msds-register.json)을 사이트 데이터에 반영한다.

    py scripts/apply_msds_register.py            무엇이 바뀌는지 보기만
    py scripts/apply_msds_register.py --write    반영하기

왜 따로 두는가. 공개 데이터(msds.public.json)는 집 PC 가 로컬 데이터로 다시
만든다. 공개 데이터를 직접 고치면 다음 빌드 때 로컬 값으로 되돌아간다.
그래서 사람이 확인한 것은 관리대장에 적고, 사이트 데이터를 만들 때마다 이
스크립트가 관리대장을 덮어쓴다. build_public_data.py 가 끝에 이것을 부른다.

관리대장이 정하는 것.

  번호     msdsNo 에는 공단 번호(영문2+숫자5-숫자10)만 둔다. 'MSDS번호 미기재',
           '제품명기준-…' 같은 자리표시는 지우고, LB2982·문서그룹 42-2264-2 같은
           공급사 문서번호는 supplierDocNo 로 옮긴다.
  상태     msdsNoStatus 와 그 까닭·법적 근거·확인일. 번호가 비었을 때 화면이
           "정보 없음" 대신 "필요 없음(분류기준 비해당)" 같은 상태를 보여 준다.
  신호어   원문 제2항에서 뽑은 값(scripts/extract_signal_words.py).
  비해당   원문이 분류기준 비해당이라고 적은 제품은 hazardNotClassified 를 켜고
           그림문자·유해위험문구·예방조치문구를 비운다. 원문에 없는 그림문자가
           경고표지에 인쇄되던 것을 막는다. overrides 쪽도 같이 비운다. 관리요령이
           제품 쪽이 비면 overrides 에서 채워 넣기 때문이다.
  날짜     revisionDate·issueDate 를 적어 두면 그 값으로 바꾼다. 원문과 다르게
           들어간 개정일을 바로잡을 때 쓴다. datesCheckedSha256 이 있으면 그 PDF 일
           때만 바꾼다. 같은 자리에 새 판이 들어오면 옛 날짜로 덮지 않는다.
  재인쇄   history 에 labelReprint 로 적힌 제품에 labelReprint 를 붙인다. 경고표지
           화면이 "표지 다시 뽑기" 를 띄운다.
  구판     retired 로 적힌 제품은 목록에서 뺀다. 대신 새 판에 formerIds 로 옛 id 를
           남겨, 옛 QR 을 찍어도 새 판이 열리게 한다.

같이 하는 일. 2026-09-18 에 원본 PDF 와 대조해 고친 성분표 113행
(reports/ingredient_repair_log.json)도 여기서 다시 반영한다. 그것도 공개
데이터만 고쳐 둬서 다음 빌드 때 되돌아갈 처지였다. 지금 값이 고치기 전
값과 같을 때만 바꾸므로, 로컬 쪽에서 이미 고쳐졌으면 건드리지 않는다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "data" / "msds-register.json"
PRODUCTS_PATH = ROOT / "data" / "msds.public.json"
OVERRIDES_PATH = ROOT / "data" / "msds-overrides.public.json"
INGREDIENT_LOG_PATH = ROOT / "reports" / "ingredient_repair_log.json"

KOSHA_NO = re.compile(r"^[A-Z]{2}\d{5}-\d{10}$")
STATUSES = ("verified", "required", "not_required", "submission_exempt", "pending", "retired")
SIGNALS = ("위험", "경고", "해당없음")

HAZARD_LIST_FIELDS = ("ghsPictograms", "classificationGhsPictograms", "classificationGhsCodes",
                      "ghsCodes", "hazardStatements")
OVERRIDE_HAZARD_LIST_FIELDS = HAZARD_LIST_FIELDS + ("labelGhsPictograms", "labelGhsCodes")
EMPTY_PRECAUTIONS = {"prevention": [], "response": [], "storage": [], "disposal": []}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    # 배포 목록(release-manifest)이 이 파일들의 해시를 적는다. 윈도에서 CRLF 로
    # 쓰면 CI(리눅스)에서 잰 해시와 달라지므로 LF 로 고정한다.
    with path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def load_register(path: Path = REGISTER_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"products": {}, "legalBasis": {}}
    return read_json(path)


def _file_key(value: Any) -> str:
    return str(value or "").replace("\\", "/").split("/")[-1].strip()


def _override_matches(override: dict[str, Any], product: dict[str, Any]) -> bool:
    names = {_file_key(product.get("fileName")), _file_key(product.get("pdfPath"))} - {""}
    keys = {_file_key((override.get("match") or {}).get("fileName")),
            _file_key(override.get("sourcePdfPath")),
            _file_key(override.get("sourceRelativePath"))} - {""}
    return bool(names & keys)


_SHA_CACHE: dict[str, str] = {}


def _clear_settled_warnings(product: dict[str, Any], entry: dict[str, Any], dates_ok: bool) -> None:
    """집 PC 빌드가 남긴 경고 가운데 관리대장으로 풀린 것을 지운다.

    SIGNAL_WORD_INVALID  추출 후보 신호어가 이상하다는 뜻. 신호어는 관리대장이 원문에서
                         뽑은 값으로 정하므로 지금 신호어가 올바르면 풀린 것이다.
    REVISION_DATE_CONFLICT  제품 개정일과 추출 후보가 달랐다는 뜻. 관리대장이 그 PDF 로
                         날짜를 확인했으면(datesCheckedSha256) 풀린 것이다.
    """
    meta = product.get("publication")
    if not isinstance(meta, dict) or not isinstance(meta.get("validationWarnings"), list):
        return
    settled = set()
    if str(product.get("signalWord") or "") in SIGNALS:
        settled.add("SIGNAL_WORD_INVALID")
    if entry.get("datesCheckedSha256") and dates_ok:
        settled.add("REVISION_DATE_CONFLICT")
    left = [w for w in meta["validationWarnings"] if w not in settled]
    if left != meta["validationWarnings"]:
        meta["validationWarnings"] = left
        if not left and meta.get("validationStatus") == "automatic_with_warnings":
            meta["validationStatus"] = "automatic"


def _pdf_unchanged(product: dict[str, Any], expected: Any) -> bool:
    """관리대장에 적은 PDF 해시가 지금 PDF 와 같은가. 해시를 안 적었거나 파일이 없으면 참."""
    if not expected:
        return True
    path = ROOT / str(product.get("pdfPath") or "")
    if not path.is_file():
        return True
    key = str(path)
    if key not in _SHA_CACHE:
        _SHA_CACHE[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return _SHA_CACHE[key] == expected


def _legal_text(keys: list[str], legal: dict[str, str]) -> str:
    return "; ".join(legal.get(key, key) for key in keys or [])


def apply_register(
    products: list[dict[str, Any]],
    overrides: list[dict[str, Any]],
    register: dict[str, Any] | None = None,
    ingredient_log: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """관리대장을 반영한 새 목록을 돌려준다. 넘겨받은 목록은 건드리지 않는다."""
    register = register if register is not None else load_register()
    entries: dict[str, dict[str, Any]] = register.get("products") or {}
    legal: dict[str, str] = register.get("legalBasis") or {}
    products = deepcopy(products)
    overrides = deepcopy(overrides)
    report: dict[str, Any] = {"retired": [], "numbersSet": [], "notClassified": [], "signalChanged": [],
                              "ingredientsRestored": 0, "missingEntry": [], "datesFixed": [], "datesStale": [],
                              "labelReprint": []}

    # 1. 구판·중복을 뺀다. 새 판에 옛 id 를 남긴다.
    retired = {pid for pid, e in entries.items() if e.get("status") == "retired" or e.get("retired")}
    by_id = {p.get("id"): p for p in products}
    for pid in sorted(retired):
        gone = by_id.get(pid)
        if not gone:
            continue
        target = by_id.get(entries[pid].get("replacedBy"))
        if target is not None:
            former = target.setdefault("formerIds", [])
            if pid not in former:
                former.append(pid)
        overrides = [o for o in overrides if not _override_matches(o, gone)]
        report["retired"].append(pid)
    products = [p for p in products if p.get("id") not in retired]

    # 2. 제품마다 번호·상태·신호어·비해당을 반영한다.
    for product in products:
        entry = entries.get(product.get("id"))
        if entry is None:
            report["missingEntry"].append(product.get("id"))
            continue

        number = str(entry.get("msdsNo") or "").strip()
        if number and not KOSHA_NO.match(number):
            raise ValueError(f"관리대장의 번호 꼴이 틀렸다: {product.get('id')} {number}")
        if number and str(product.get("msdsNo") or "").strip() != number:
            report["numbersSet"].append(product.get("id"))
        product["msdsNo"] = number
        for field, key in (("supplierDocNo", "supplierDocNo"), ("msdsNoAsWritten", "msdsNoAsWritten")):
            if entry.get(key):
                product[field] = entry[key]
            else:
                product.pop(field, None)
        product["msdsNoStatus"] = entry.get("status", "pending")
        if entry.get("kind"):
            product["msdsNoKind"] = entry["kind"]
        else:
            product.pop("msdsNoKind", None)
        product["msdsNoReason"] = entry.get("reason", "")
        product["msdsNoLegalBasis"] = _legal_text(entry.get("basis") or [], legal)
        product["msdsNoCheckedOn"] = entry.get("checkedOn", "")

        # 원문과 다르게 들어간 날짜를 바로잡는다. 원문에서 확인한 날짜만 관리대장에 적는다.
        # 확인한 PDF 의 해시를 같이 적어 두었으니, 그 자리에 다른 PDF 가 들어왔으면
        # 옛 날짜로 덮어쓰지 않는다.
        dates_ok = _pdf_unchanged(product, entry.get("datesCheckedSha256"))
        if not dates_ok:
            report["datesStale"].append(product.get("id"))
        for field in ("revisionDate", "issueDate"):
            value = str(entry.get(field) or "").strip()
            if dates_ok and value and product.get(field) != value:
                product[field] = value
                report["datesFixed"].append(f"{product.get('id')} {field}")
                if field == "revisionDate":
                    for override in overrides:
                        if _override_matches(override, product) and "revisionDateCandidate" in override:
                            override["revisionDateCandidate"] = value

        signal = str(entry.get("signalWord") or "").strip()
        if entry.get("notClassified"):
            signal = "해당없음"
        if signal in SIGNALS:
            if str(product.get("signalWord") or "") != signal:
                report["signalChanged"].append(product.get("id"))
            product["signalWord"] = signal
        elif str(product.get("signalWord") or "").strip() not in SIGNALS:
            product["signalWord"] = ""

        _clear_settled_warnings(product, entry, dates_ok)

        if entry.get("notClassified"):
            product["hazardNotClassified"] = True
            for field in HAZARD_LIST_FIELDS:
                product[field] = []
            product["precautionaryStatements"] = deepcopy(EMPTY_PRECAUTIONS)
            for override in overrides:
                if _override_matches(override, product):
                    for field in OVERRIDE_HAZARD_LIST_FIELDS:
                        if field in override:
                            override[field] = []
                    if "precautionaryStatements" in override:
                        override["precautionaryStatements"] = deepcopy(EMPTY_PRECAUTIONS)
                    override["signalWordCandidate"] = "해당없음"
            report["notClassified"].append(product.get("id"))

    # 3. 표지를 다시 뽑아야 하는 제품. 이력에 labelReprint 로 적힌 가장 최근 것.
    by_id = {p.get("id"): p for p in products}
    for product in products:
        product.pop("labelReprint", None)
    for item in sorted(register.get("history") or [], key=lambda h: str(h.get("date") or "")):
        product = by_id.get(item.get("newId"))
        if product is not None and item.get("labelReprint"):
            product["labelReprint"] = {"date": item.get("date", ""), "reason": item.get("labelReprintReason", "")}
    report["labelReprint"] = [p.get("id") for p in products if p.get("labelReprint")]

    # 4. 원본 PDF 와 대조해 고친 성분표를 다시 반영한다.
    if ingredient_log is None and INGREDIENT_LOG_PATH.exists():
        ingredient_log = read_json(INGREDIENT_LOG_PATH)
    by_id = {p.get("id"): p for p in products}
    for fix in ingredient_log or []:
        product = by_id.get(fix.get("productId"))
        rows = (product or {}).get("ingredients") or []
        index = fix.get("index")
        if not isinstance(index, int) or index >= len(rows):
            continue
        row = rows[index]
        if str(row.get("casNo") or "").strip() != str(fix.get("cas") or "").strip():
            continue      # 표가 달라졌으면 손대지 않는다
        if str(row.get("chemicalName") or "") == str(fix.get("before") or ""):
            row["chemicalName"] = fix.get("after", "")
            report["ingredientsRestored"] += 1

    return products, overrides, report


def _coerce(payload: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    return list((payload or {}).get(key) or [])


def _rewrap(payload: Any, key: str, items: list[dict[str, Any]]) -> Any:
    if isinstance(payload, list):
        return items
    return {**payload, key: items}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    products_payload = read_json(PRODUCTS_PATH)
    overrides_payload = read_json(OVERRIDES_PATH)
    products, overrides, report = apply_register(_coerce(products_payload, "products"),
                                                 _coerce(overrides_payload, "overrides"))
    print(f"제품 {len(_coerce(products_payload, 'products'))} -> {len(products)}")
    print(f"  구판·중복 뺌        {len(report['retired'])}")
    print(f"  번호 새로 넣음/바꿈  {len(report['numbersSet'])}")
    print(f"  분류기준 비해당 정리 {len(report['notClassified'])}")
    print(f"  신호어 바뀜         {len(report['signalChanged'])}")
    print(f"  날짜 바로잡음       {len(report['datesFixed'])}")
    print(f"  날짜 확인 뒤 PDF 바뀜 {len(report['datesStale'])} {report['datesStale'][:5]}")
    print(f"  표지 다시 뽑기 표시 {len(report['labelReprint'])}")
    print(f"  성분표 되살림       {report['ingredientsRestored']}")
    print(f"  관리대장에 없는 제품 {len(report['missingEntry'])} {report['missingEntry'][:5]}")
    if args.write:
        write_json(PRODUCTS_PATH, _rewrap(products_payload, "products", products))
        write_json(OVERRIDES_PATH, _rewrap(overrides_payload, "overrides", overrides))
        print("반영했다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
