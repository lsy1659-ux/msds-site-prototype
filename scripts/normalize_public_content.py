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
            채우기, 비었거나 MSDS 번호 조각이 들어간 긴급전화번호와 빈 공급자 주소 채우기, 응급조치에 섞인 쪽
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
GHS_LABELS = {"GHS01": "폭발성", "GHS02": "인화성", "GHS03": "산화성", "GHS04": "고압가스", "GHS05": "부식성",
              "GHS06": "급성독성", "GHS07": "유해/자극성", "GHS08": "건강유해성", "GHS09": "환경유해성"}
GROUP_BY_DIGIT = {"1": "prevention", "2": "prevention", "3": "response", "4": "storage", "5": "disposal"}
CODE = re.compile(r"[HP]\d{3}[A-Za-z]?(?:\s*\+\s*[HP]\d{3}[A-Za-z]?)*")
BULLET = re.compile(r"^[\s\-–•·ㆍ∙▪○●◦*]+")
# 항목 이름. "예 방" 처럼 글자 사이가 벌어진 PDF 도 있어 글자 사이 빈칸을 허용한다.
LABEL_WORDS = ("유해위험문구", "예방조치문구", "예방", "대응", "저장", "폐기", "문구")
CATEGORY = re.compile(r"구분\s*[:：]?\s*\d|Category|;\s*$", re.I)
SENTENCE_TAIL = re.compile(r"^[가-힣\s·,()]{1,20}(?:시오|것|음|함|됨|다)\s*\.?$")
PAGE_MARK = re.compile(r"\d+\s*/\s*\d+\s*$")
# 글자 사이가 벌어진 항목 이름("유 해 위 험 문 구·", "대 응").
SPACED_LABEL = re.compile(r"^(?:유\s*해\s*[·ㆍᆞ·,]?\s*위\s*험\s*문\s*구|예\s*방\s*조\s*치\s*문\s*구|예\s*방|대\s*응|저\s*장|폐\s*기)"
                          r"\s*[·ㆍᆞ·:：]?\s*")
# 조사 앞에 끼어든 빈칸("스프레이 의 흡입을", "물 로 씻으시오"). 조사는 앞말에 붙여 쓴다.
PARTICLE_GAP = re.compile(r"(?<=[가-힣)]) (을|를|의|로|으로|에|에서|에게)(?=[\s.,)·/]|$)")
# 한자어 동작 명사와 "하다" 사이 빈칸("실시 하시오", "방지 할 것", "제거 하시오"). 앞말이 조사나
# 어미로 끝나면("…도록 하시오", "처치를 하시오") 띄어 쓰는 것이 맞아 건드리지 않는다.
VERB_GAP = re.compile(r"(?<=[가-힣])(?<![을를이가은는도게록고서며면와과로에의])"
                      r" (?=(?:하시오|할 것|하십시오|하여야|하세요|한다|하여)(?:[\s.,)]|$))")


def _single(token: str) -> bool:
    return len(re.sub(r"[^가-힣]", "", token)) == 1


def _letter_spaced(text: str) -> bool:
    """"사 용 전 취 급 설 명 서 를" 처럼 한 글자마다 띄운 글."""
    tokens = [t for t in text.split() if re.search(r"[가-힣]", t)]
    if len(tokens) < 6 or sum(_single(t) for t in tokens) / len(tokens) < 0.5:
        return False
    run = best = 0
    for token in tokens:   # "방지 할 것" 처럼 한 글자 낱말이 두셋 있는 보통 글과 가르려고 넷 이상 잇달아야 한다
        run = run + 1 if _single(token) else 0
        best = max(best, run)
    return best >= 4


def _oddly_spaced(text: str) -> bool:
    """한 글자 낱말이 셋 이상 잇달아 나오는 글("조 언 ·주 의 를"). 일부만 벌어진 것도 잡는다.

    둘까지는 "할 수 있음", "및 그 밖의" 처럼 보통 글에도 흔해 넣지 않는다.
    """
    run = 0
    for token in text.split():
        run = run + 1 if _single(token) else 0
        if run >= 3:
            return True
    return False


def _close_letter_gaps(text: str) -> str:
    """한 글자씩 띄운 글에서 한 글자 낱말이 잇달아 나오는 토막을 한 낱말로 붙인다.

    다른 문구에서 띄어쓰기를 빌려 올 수 없을 때만 쓴다. 어디서 띄울지는 알 수 없어
    토막 안은 붙여 쓴다("흡 입 을 피 하 시 오" → "흡입을피하시오"). 글자는 그대로다.
    """
    out: list[str] = []
    joining = False
    for token in text.split():
        glue = out and (token.startswith(("·", ".", ",", ")")) or out[-1].endswith(("·", "(")))
        if out and ((joining and _single(token)) or glue):
            out[-1] += token
        else:
            out.append(token)
        joining = _single(token) or (joining and glue)
    return " ".join(out)


def _run_together(text: str) -> bool:
    """띄어쓰기가 거의 없는 글("극인화성가스", "가열하면폭발할수있음"). 한글 낱말 평균이 다섯 글자를 넘으면.

    이렇게 걸린 글은 빈칸을 뺀 글자가 똑같은 다른 제품 문구가 있을 때만 그 띄어쓰기를 빌린다.
    """
    tokens = [re.sub(r"[^가-힣]", "", t) for t in text.split()]
    tokens = [t for t in tokens if t]
    return bool(tokens) and sum(map(len, tokens)) >= 6 and sum(map(len, tokens)) / len(tokens) > 5


def _corpus_key(body: str) -> str:
    return re.sub(r"\s", "", body).rstrip(".")


def _fix_spacing(line: str, corpus: dict[str, dict[str, str]]) -> str:
    """띄어쓰기만 고친다. 글자는 바꾸지 않는다.

    벌어진 문구는 다른 제품의 같은 코드 문구 가운데 빈칸을 뺀 글자가 똑같은 것의 띄어쓰기를
    쓴다. 그런 문구가 없고 글 전체가 한 글자씩 벌어졌으면 한 글자끼리의 빈칸만 붙인다.
    그다음 조사 앞 빈칸을 뗀다.
    """
    match = CODE.match(line)
    body = line[match.end():].strip() if match else line
    if match and (_letter_spaced(body) or _oddly_spaced(body) or _run_together(body)):
        same = corpus.get(re.sub(r"\s", "", match.group(0)), {}).get(_corpus_key(body))
        if same:
            if body.rstrip().endswith(".") and not same.endswith("."):
                same += "."   # 원래 글의 마침표는 둔다
            return f"{re.sub(r'\s', '', match.group(0))} {same}"
    if _letter_spaced(body):
        body = _close_letter_gaps(body)
        line = f"{re.sub(r'\s', '', match.group(0))} {body}" if match else body
    return VERB_GAP.sub("", PARTICLE_GAP.sub(r"\1", line))


def _statement_corpus(records: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    corpus: dict[str, dict[str, str]] = {}
    for record in records:
        lines = list(record.get("hazardStatements") or [])
        lines += [x for items in (record.get("precautionaryStatements") or {}).values() for x in items]
        for line in lines:
            match = CODE.match(line)
            body = line[match.end():].strip() if match else ""
            if match and body and not _letter_spaced(body) and not _oddly_spaced(body) and not _run_together(body):
                body = PARTICLE_GAP.sub(r"\1", body)
                corpus.setdefault(re.sub(r"\s", "", match.group(0)), {}).setdefault(_corpus_key(body), body)
    return corpus


def fix_spacing(products: list[dict[str, Any]], overrides: list[dict[str, Any]], report: dict[str, Any]) -> None:
    corpus = _statement_corpus(products + overrides)
    product_ids = {id(p) for p in products}
    for record in products + overrides:
        is_product = id(record) in product_ids
        lists = [record.get("hazardStatements") or []] + list((record.get("precautionaryStatements") or {}).values())
        if is_product:
            lists += list((record.get("firstAid") or {}).values())
        for items in lists:
            for index, line in enumerate(items):
                fixed = _fix_spacing(line, corpus)
                if fixed != line:
                    items[index] = fixed
                    report["spacingFixed"] += is_product


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
            elif not re.search(r"[가-힣A-Za-z]", body) and len(re.findall(r"[가-힣]", head)) >= 2:
                # 문구 뒤에 코드를 단 꼴("졸음 또는 현기증을 일으킬 수 있음H336"). 코드를 앞으로.
                out.append((code, f"{code} {SPACED_LABEL.sub('', head).strip()}"))
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


def _flat(text: Any) -> str:
    """빈칸을 뺀 글. 띄어쓰기를 고친 뒤에도 같은 줄로 알아보려고 쓴다."""
    return re.sub(r"\s", "", str(text or ""))


def drop_uncoded_precautions(record: dict[str, Any], product: dict[str, Any] | None = None) -> int:
    """추출 후보(overrides)의 예방조치 칸에서 코드 없는 줄을 뺀다. 코드 있는 줄이 있을 때만.

    예전 추출이 6·7·8항(누출·취급·보호구) 글까지 예방조치 칸에 넣었다("가. 인체를 보호하기 위해
    필요한 조치사항…", "구를 착용하시오"). 코드 있는 문구가 있는 기록에서 코드 없는 줄은 그런 찌꺼기다.
    코드가 하나도 없는 옛 꼴 MSDS 는 건드리지 않는다. 제품 쪽 데이터도 건드리지 않는다.
    """
    groups = record.get("precautionaryStatements") or {}
    if (product or {}).get("hazardNotClassified"):
        # 분류기준 비해당 제품에는 예방조치문구가 없다. 후보에 남은 것은 다른 절에서 딸려 온 글이다.
        dropped = sum(len(items) for items in groups.values())
        if dropped:
            record["precautionaryStatements"] = {g: [] for g in GROUPS}
            record["hazardStatements"] = []
        return dropped
    # 6~8항의 소항목 머리("나. 환경을 보호하기 위해 필요한 조치사항 …", "가. 안전취급요령 …")로 시작하는
    # 줄은 코드 꼴이 아닌 MSDS 에서도 예방조치문구가 아니다.
    other_section = re.compile(r"^\s*[가-하]\s*[.．]\s*(?:인체를\s*보호|환경을\s*보호|정화\s*또는\s*제거|안전\s*취급|"
                               r"안전한\s*저장|화학물질의\s*노출|적절한\s*공학|개인\s*보호구)")
    early = 0
    for group, items in groups.items():
        kept = [line for line in items if not other_section.match(line)]
        early += len(items) - len(kept)
        groups[group] = kept
    coded = any(CODE.match(line) for items in groups.values() for line in items)
    # 추출 후보에 코드가 없어도 짝인 제품 쪽에 코드 있는 문구가 있으면 그 칸은 코드 꼴 MSDS 다.
    coded = coded or any(CODE.match(line) for items in ((product or {}).get("precautionaryStatements") or {}).values()
                         for line in items)
    if not coded:
        return early
    dropped = early
    for group, items in groups.items():
        kept = [line for line in items if CODE.match(line)]
        dropped += len(items) - len(kept)
        groups[group] = kept
    return dropped


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
                drop = {_flat(item) for item in items}
                kept = [item for item in first_aid[key] if _flat(item) not in drop]
                report["firstAidRemoved"] += len(first_aid[key]) - len(kept)
                if kept:
                    first_aid[key] = kept
                else:
                    del first_aid[key]

    # 끊기거나 잘린 응급조치 줄. 머리글을 뺀 뒤의 줄 목록이 적어 둔 것과 똑같을 때만 바꾼다.
    for pid, fix in (repairs.get("firstAidText") or {}).items():
        first_aid = (by_id.get(pid) or {}).get("firstAid")
        if not isinstance(first_aid, dict):
            continue
        for key, change in fix.items():
            if [_flat(x) for x in first_aid.get(key) or []] == [_flat(x) for x in change.get("before") or []]:
                first_aid[key] = list(change.get("after") or [])
                report["firstAidJoined"] += 1

    for pid, fix in (repairs.get("emergencyContact") or {}).items():
        product = by_id.get(pid)
        if product and str(product.get("emergencyContact") or "") == str(fix.get("before") or ""):
            product["emergencyContact"] = fix.get("after", "")
            report["emergencyContact"] += 1

    for pid, fix in (repairs.get("supplierAddress") or {}).items():
        product = by_id.get(pid)
        if product is not None and str(product.get("supplierAddress") or "") == str(fix.get("before") or ""):
            product["supplierAddress"] = fix.get("after", "")
            report["supplierAddress"] += 1

    for fix in repairs.get("ingredientNames") or []:
        rows = (by_id.get(fix.get("productId")) or {}).get("ingredients") or []
        index = fix.get("index")
        if not isinstance(index, int) or index >= len(rows):
            continue
        row = rows[index]
        if str(row.get("casNo") or "").strip() == str(fix.get("cas") or "").strip() and row.get("chemicalName") == fix.get("before"):
            row["chemicalName"] = fix.get("after", "")
            report["ingredientNames"] += 1

    for pid, fix in (repairs.get("precautionaryStatements") or {}).items():
        product = by_id.get(pid)
        if not product or product.get("hazardNotClassified"):
            continue
        probe = {"precautionaryStatements": deepcopy(product.get("precautionaryStatements") or {})}
        normalize_statements(probe)
        now = _codes([x for items in probe["precautionaryStatements"].values() for x in items])
        if now == sorted(fix.get("beforeCodes") or []):
            product["precautionaryStatements"] = deepcopy(fix.get("after") or {})
            for override in _matching_overrides(overrides, product):
                override["precautionaryStatements"] = deepcopy(fix.get("after") or {})
            report["precautionsFilled"].append(pid)

    # 그림문자. 원문 제2항 그림을 눈으로 확인해 적은 것. 지금 값이 적어 둔 '고치기 전' 값일 때만.
    for pid, fix in (repairs.get("ghsCodes") or {}).items():
        product = by_id.get(pid)
        if not product or sorted(product.get("ghsCodes") or []) != sorted(fix.get("before") or []):
            continue
        codes = list(fix.get("after") or [])
        pictograms = [{"code": code, "label": GHS_LABELS.get(code, code)} for code in codes]
        for field, value in (("ghsCodes", codes), ("classificationGhsCodes", codes),
                             ("ghsPictograms", pictograms), ("classificationGhsPictograms", pictograms)):
            product[field] = deepcopy(value)
        for override in _matching_overrides(overrides, product):
            for field in ("ghsCodes", "labelGhsCodes", "classificationGhsCodes"):
                override[field] = list(codes)
            for field in ("ghsPictograms", "labelGhsPictograms", "classificationGhsPictograms"):
                override[field] = deepcopy(pictograms)
        report["pictogramsFixed"].append(pid)

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
        swap = {_flat(pair["before"]): pair["after"] for pair in pairs if pair.get("before") and pair.get("after")}
        for record in [product] + _matching_overrides(overrides, product):
            lists = [record.get("hazardStatements") or []]
            lists += list((record.get("precautionaryStatements") or {}).values())
            for items in lists:
                for index, line in enumerate(items):
                    if _flat(line) in swap:
                        items[index] = swap[_flat(line)]
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
                              "emergencyContact": 0, "firstAidRemoved": 0, "statementsCompleted": 0,
                              "firstAidJoined": 0, "spacingFixed": 0,
                              "supplierAddress": 0, "precautionsFilled": [], "pictogramsFixed": [],
                              "uncodedDropped": 0}

    apply_repairs(products, overrides, repairs, report)
    for product in products:
        report["statementsProducts"] += normalize_statements(product)
        if "hazardBadge" in product:
            del product["hazardBadge"]
            report["hazardBadgeRemoved"] += 1
    owner = {id(o): p for p in products for o in _matching_overrides(overrides, p)}
    for override in overrides:
        report["statementsOverrides"] += normalize_statements(override)
        report["uncodedDropped"] += drop_uncoded_precautions(override, owner.get(id(override)))
    complete_statements(products, overrides, repairs, report)
    fix_spacing(products, overrides, report)
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
    print(f"공급자 주소 채움      {report['supplierAddress']}")
    print(f"예방조치문구 채움     {len(report['precautionsFilled'])}")
    print(f"그림문자 바로잡음     {len(report['pictogramsFixed'])}")
    print(f"추출 후보 찌꺼기 뺌   {report['uncodedDropped']}")
    print(f"응급조치 머리글 뺌    {report['firstAidRemoved']}")
    print(f"잘린 문구 채움        {report['statementsCompleted']}")
    print(f"응급조치 끊긴 줄 이음 {report['firstAidJoined']}")
    print(f"띄어쓰기 고침         {report['spacingFixed']}")
    print(f"hazardBadge 뺌       {report['hazardBadgeRemoved']}")
    if args.write:
        write_json(PRODUCTS_PATH, products)
        write_json(OVERRIDES_PATH, overrides)
        print("반영했다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
