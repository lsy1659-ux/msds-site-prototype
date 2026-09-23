"""공개 데이터의 문구 꼴을 고르고, 원본 PDF 와 대조해 확인한 보완을 반영한다.

    py scripts/normalize_public_content.py            무엇이 바뀌는지 보기만
    py scripts/normalize_public_content.py --write    반영하기

왜 따로 두는가. 공개 데이터는 집 PC 가 로컬 데이터로 다시 만든다. 공개 JSON 을
직접 고치면 다음 빌드 때 되돌아가므로, build_public_data.py 가 관리대장 반영
뒤에 이것을 부른다. 몇 번을 돌려도 결과가 같다.

하는 일.

  문구 꼴   유해·위험문구와 예방조치문구 앞에 붙은 것을 떼고 "코드 문구" 꼴로 맞춘다.
            "- H226 …", "예방 P210 …", "유해·위험문구 H225 …", "P201 : …" 같은 것.
            앞 문구의 꼬리("받으시오.")가 다음 줄 앞에 붙어 있으면 앞 문구로 돌려준다.
            같은 코드에 문구가 있는 줄과 분류만 적힌 줄("호흡기 과민성, 구분 1 H334")이
            함께 있으면 분류 줄을 뺀다. 문구 글자는 바꾸지 않는다.
  칸 나누기 예방조치문구를 코드 번호로 나눈다. P1·P2 예방, P3 대응, P4 저장, P5 폐기.
            대응 문구가 예방 칸에 들어가 있으면 관리요령의 사고 시 칸이 비기 때문이다.
            코드가 없는 줄은 원래 칸에 둔다.
  보완      data/msds-content-repairs.json 에 적힌, 원본 PDF 에서 다시 읽어 확인한 것.
            응급조치의 빠진 칸 채우기, 깨진 성분 이름 바로잡기, 빠진 유해·위험문구
            채우기, MSDS 번호 조각이 들어간 긴급전화번호 바로잡기, 응급조치에 섞인 쪽
            머리글·꼬리글 빼기, 중간에서 잘린 문구를 원문 문구로 채우기(꼴을 고른 뒤 비교). 지금 값이 적어 둔 '고치기 전' 값과 같을 때만 바꿔, 다른 곳에서
            이미 고쳤으면 건드리지 않는다.
  hazardBadge 칸을 뺀다. 신호어가 아닌데 228건 중 180건에 일괄로 "위험"이 들어 있어
            신호어로 오해받았다. 신호어는 signalWord 하나만 쓴다.
"""

from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_PATH = ROOT / "data" / "msds.public.json"
OVERRIDES_PATH = ROOT / "data" / "msds-overrides.public.json"
REPAIRS_PATH = ROOT / "data" / "msds-content-repairs.json"

GROUPS = ("prevention", "response", "storage", "disposal")
GROUP_BY_DIGIT = {"1": "prevention", "2": "prevention", "3": "response", "4": "storage", "5": "disposal"}
CODE = re.compile(r"[HP]\d{3}[A-Za-z]?(?:\s*\+\s*[HP]\d{3}[A-Za-z]?)*")
BULLET = re.compile(r"^[\s\-–•·ㆍ∙▪○●◦*]+")
# 항목 이름. "예 방" 처럼 글자 사이가 벌어진 PDF 도 있어 글자 사이 빈칸을 허용한다.
LABEL_WORDS = ("유해위험문구", "예방조치문구", "예방", "대응", "저장", "폐기", "문구")
CATEGORY = re.compile(r"구분\s*[:：]?\s*\d|Category|;\s*$", re.I)
SENTENCE_TAIL = re.compile(r"^[가-힣\s·,()]{1,20}(?:시오|것|음|함|됨|다)\s*\.?$")
PAGE_MARK = re.compile(r"\d+\s*/\s*\d+\s*$")


def _is_label(head: str) -> bool:
    head = re.sub(r"^\s*(?:\(?\d{1,2}[).．]|[가-하][.)．])\s*", "", head)   # "3)", "가." 같은 번호
    flat = re.sub(r"[^가-힣A-Za-z]", "", head)   # 가운뎃점은 PDF 마다 글자가 달라(·ㆍᆞ·•) 모두 뗀다
    if not flat:
        return True
    while flat:
        for word in LABEL_WORDS:
            if flat.startswith(word):
                flat = flat[len(word):]
                break
        else:
            return False
    return True


def _clean(raw: str) -> tuple[str, str, str]:
    """(코드, 문구, 앞에 남은 것). 코드가 없으면 코드 자리는 빈 문자열."""
    text = re.sub(r"\s+", " ", str(raw or "")).strip()
    text = BULLET.sub("", text)
    match = CODE.search(text)
    if not match:
        return "", text, ""
    head = text[:match.start()].strip()
    code = re.sub(r"\s", "", match.group(0))
    # 코드 뒤 구분표(" - ", " : ")만 뗀다. 마침표는 두어야 "P321 … 처치를 하시오" 가 줄지 않는다.
    body = re.sub(r"^\s*[-–:：;]\s*", "", text[match.end():]).strip()
    return code, body, head


def _normalize_list(items: list[str]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """[(코드, 한 줄)] 과 분류만 적힌 줄 [(코드, 원래 줄)] 을 돌려준다."""
    out: list[tuple[str, str]] = []
    class_only: list[tuple[str, str]] = []
    for raw in items:
        code, body, head = _clean(raw)
        if not code:
            # 쪽 꼬리글("CALS Corp.1/13")은 뺀다. 한글 문장이 든 줄은 코드가 없어도 둔다.
            if body and not (PAGE_MARK.search(body) and not re.search(r"[가-힣]", body)):
                out.append(("", body))
            continue
        if head and not _is_label(head):
            if CATEGORY.search(head):
                if not body:
                    class_only.append((code, re.sub(r"\s+", " ", str(raw)).strip()))
                    continue
            elif SENTENCE_TAIL.match(head) and out:
                prev_code, prev = out[-1]
                out[-1] = (prev_code, f"{prev} {head}".strip())
            else:
                out.append((code, BULLET.sub("", re.sub(r"\s+", " ", str(raw)).strip())))
                continue
        out.append((code, f"{code} {body}".strip()))
    return out, class_only


def normalize_statements(record: dict[str, Any]) -> bool:
    """record 의 hazardStatements·precautionaryStatements 를 고친다. 바뀌면 True."""
    before = json.dumps([record.get("hazardStatements"), record.get("precautionaryStatements")], ensure_ascii=False)
    hazards, h_class = _normalize_list(record.get("hazardStatements") or [])
    prec_in = record.get("precautionaryStatements") or {}
    groups: dict[str, list[str]] = {g: [] for g in GROUPS}
    moved_h: list[tuple[str, str]] = []
    for group in list(GROUPS) + [g for g in prec_in if g not in GROUPS]:
        rows, _ = _normalize_list(prec_in.get(group) or [])
        for code, line in rows:
            if code.startswith("H"):
                moved_h.append((code, line))
                continue
            target = GROUP_BY_DIGIT.get(code[1:2], group if group in GROUPS else "prevention") if code else (
                group if group in GROUPS else "prevention")
            if line not in groups[target]:
                groups[target].append(line)

    lines: list[str] = []
    seen_codes = set()
    for code, line in hazards + moved_h:
        if line in lines:
            continue
        if code and code in seen_codes and line == code:
            continue
        lines.append(line)
        if code:
            seen_codes.add(code)
    # 분류만 적힌 줄은 같은 코드의 문구가 없을 때만 남긴다. 문구를 지어 넣지 않는다.
    for code, raw in h_class:
        if code not in seen_codes and raw not in lines:
            lines.append(raw)

    if record.get("hazardStatements") is not None or lines:
        record["hazardStatements"] = lines
    if record.get("precautionaryStatements") is not None or any(groups.values()):
        record["precautionaryStatements"] = groups
    after = json.dumps([record.get("hazardStatements"), record.get("precautionaryStatements")], ensure_ascii=False)
    return before != after


def _codes(lines: list[str]) -> list[str]:
    return sorted({re.sub(r"\s", "", m.group(0)) for line in lines or [] for m in [CODE.search(line)] if m})


def _file_key(value: Any) -> str:
    return str(value or "").replace("\\", "/").split("/")[-1].strip()


def _matching_overrides(overrides: list[dict[str, Any]], product: dict[str, Any]) -> list[dict[str, Any]]:
    names = {_file_key(product.get("fileName")), _file_key(product.get("pdfPath"))} - {""}
    return [o for o in overrides
            if names & ({_file_key((o.get("match") or {}).get("fileName")), _file_key(o.get("sourcePdfPath")),
                         _file_key(o.get("sourceRelativePath"))} - {""})]


def apply_repairs(products: list[dict[str, Any]], overrides: list[dict[str, Any]],
                  repairs: dict[str, Any], report: dict[str, Any]) -> None:
    by_id = {p.get("id"): p for p in products}

    for pid, fix in (repairs.get("firstAid") or {}).items():
        product = by_id.get(pid)
        if not product:
            continue
        current = product.get("firstAid") or {}
        added = {key: items for key, items in (fix.get("fill") or {}).items() if items and not current.get(key)}
        if added:
            product["firstAid"] = {**current, **added}
            report["firstAidFilled"].append(pid)

    for pid, fix in (repairs.get("firstAidRemove") or {}).items():
        product = by_id.get(pid)
        first_aid = (product or {}).get("firstAid")
        if not isinstance(first_aid, dict):
            continue
        for key, items in fix.items():
            if key in first_aid:
                kept = [item for item in first_aid[key] if item not in items]
                report["firstAidRemoved"] += len(first_aid[key]) - len(kept)
                if kept:
                    first_aid[key] = kept
                else:
                    del first_aid[key]

    for pid, fix in (repairs.get("emergencyContact") or {}).items():
        product = by_id.get(pid)
        if product and product.get("emergencyContact") == fix.get("before"):
            product["emergencyContact"] = fix.get("after", "")
            report["emergencyContact"] += 1

    for fix in repairs.get("ingredientNames") or []:
        rows = (by_id.get(fix.get("productId")) or {}).get("ingredients") or []
        index = fix.get("index")
        if not isinstance(index, int) or index >= len(rows):
            continue
        row = rows[index]
        if str(row.get("casNo") or "").strip() == str(fix.get("cas") or "").strip() and row.get("chemicalName") == fix.get("before"):
            row["chemicalName"] = fix.get("after", "")
            report["ingredientNames"] += 1

    for pid, fix in (repairs.get("hazardStatements") or {}).items():
        product = by_id.get(pid)
        if not product or product.get("hazardNotClassified"):
            continue
        if _codes(product.get("hazardStatements")) == sorted(fix.get("beforeCodes") or []):
            product["hazardStatements"] = list(fix.get("after") or [])
            for override in _matching_overrides(overrides, product):
                if _codes(override.get("hazardStatements")) == sorted(fix.get("beforeCodes") or []):
                    override["hazardStatements"] = list(fix.get("after") or [])
            report["hazardStatementsFilled"].append(pid)


def complete_statements(products: list[dict[str, Any]], overrides: list[dict[str, Any]],
                        repairs: dict[str, Any], report: dict[str, Any]) -> None:
    """중간에서 잘린 문구를 원문 문구로 바꾼다. 꼴을 고른 뒤의 줄과 똑같을 때만."""
    by_id = {p.get("id"): p for p in products}
    for pid, pairs in (repairs.get("statementText") or {}).items():
        product = by_id.get(pid)
        if not product:
            continue
        swap = {pair["before"]: pair["after"] for pair in pairs if pair.get("before") and pair.get("after")}
        for record in [product] + _matching_overrides(overrides, product):
            lists = [record.get("hazardStatements") or []]
            lists += list((record.get("precautionaryStatements") or {}).values())
            for items in lists:
                for index, line in enumerate(items):
                    if line in swap:
                        items[index] = swap[line]
                        if record is product:
                            report["statementsCompleted"] += 1


def normalize_content(
    products: list[dict[str, Any]],
    overrides: list[dict[str, Any]],
    repairs: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """고친 새 목록을 돌려준다. 넘겨받은 목록은 건드리지 않는다."""
    if repairs is None:
        repairs = json.loads(REPAIRS_PATH.read_text(encoding="utf-8")) if REPAIRS_PATH.exists() else {}
    products = deepcopy(products)
    overrides = deepcopy(overrides)
    report: dict[str, Any] = {"statementsProducts": 0, "statementsOverrides": 0, "firstAidFilled": [],
                              "ingredientNames": 0, "hazardStatementsFilled": [], "hazardBadgeRemoved": 0,
                              "emergencyContact": 0, "firstAidRemoved": 0, "statementsCompleted": 0}

    apply_repairs(products, overrides, repairs, report)
    for product in products:
        report["statementsProducts"] += normalize_statements(product)
        if "hazardBadge" in product:
            del product["hazardBadge"]
            report["hazardBadgeRemoved"] += 1
    for override in overrides:
        report["statementsOverrides"] += normalize_statements(override)
    complete_statements(products, overrides, repairs, report)
    return products, overrides, report


def write_json(path: Path, data: Any) -> None:
    # 배포 목록(release-manifest)이 해시를 적으므로 LF 로 고정한다.
    with path.open("w", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    products = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    products, overrides, report = normalize_content(products, overrides)
    print(f"문구 꼴·칸 고침      제품 {report['statementsProducts']} / 추출 후보 {report['statementsOverrides']}")
    print(f"응급조치 빈 칸 채움   {len(report['firstAidFilled'])}")
    print(f"성분 이름 바로잡음    {report['ingredientNames']}")
    print(f"유해·위험문구 채움    {len(report['hazardStatementsFilled'])}")
    print(f"긴급전화번호 바로잡음 {report['emergencyContact']}")
    print(f"응급조치 머리글 뺌    {report['firstAidRemoved']}")
    print(f"잘린 문구 채움        {report['statementsCompleted']}")
    print(f"hazardBadge 뺌       {report['hazardBadgeRemoved']}")
    if args.write:
        write_json(PRODUCTS_PATH, products)
        write_json(OVERRIDES_PATH, overrides)
        print("반영했다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
