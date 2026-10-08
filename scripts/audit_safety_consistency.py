"""화면에 나가는 안전문구가 서로 맞는지 본다. 추출이 됐다고 내용이 맞는 것은 아니다.

    py scripts/audit_safety_consistency.py            규칙 점검만(빠름)
    py scripts/audit_safety_consistency.py --pdf      원본 PDF 에 그 문장이 있는지도 본다(몇 분)
    py scripts/audit_safety_consistency.py --json     결과를 reports/safety-consistency.local.json 에 적는다

규칙 점검은 원문을 읽지 않고, 사이트가 보여 주는 값끼리 맞는지만 본다.

  구토        H304(흡인 유해성)·H314(피부 부식)·P331(토하게 하지 마시오)가 있는데
              응급조치(삼켰을 때)가 구토를 시키라고 하면 서로 어긋난다.
  신호어      '위험'에만 쓰는 H코드(H225·H304·H314·H334 …)가 있는데 신호어가 '경고'.
  그림문자    H코드가 요구하는 그림문자가 없다. 우선순위 규칙(해골이 있으면 느낌표를
              빼는 것 등)은 따른다.
  문구 짝     같은 H코드인데 다른 제품들과 문장이 딴판이다(코드와 문장이 엇갈려
              읽혔을 수 있다).

여기서 걸린 것은 '틀렸다'가 아니라 '원문을 눈으로 볼 것'이다. 원문을 보고
  - 사이트가 잘못 읽었으면 scripts/repair_from_pdf.py 쪽에서 고친다.
  - 원문 자체가 이상하면 사이트 문장은 그대로 두고 관리대장(data/msds-register.json)
    그 제품에 sourceIssue(우리 메모)·sourceIssueAsk(공급사에 물을 말)를 적는다.
    관리대장 화면의 '요청 문안 복사'로 공급사에 최신판을 요청한다.
관리대장에 sourceIssue 가 적힌 제품의 걸림은 '요청함'으로 따로 센다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = ROOT / "data" / "msds.public.json"
OVERRIDES = ROOT / "data" / "msds-overrides.public.json"
REGISTER = ROOT / "data" / "msds-register.json"
REPORT = ROOT / "reports" / "safety-consistency.local.json"

# 삼켰을 때 구토를 시키라는 말. "구토를 유도하지 마시오" 같은 부정은 뺀다.
INDUCE_VOMIT = re.compile(r"(구토|토하)\S{0,3}\s*(유도|시키|일으키|하게\s*하|하도록)")
NEGATED = re.compile(r"(유도|시키|일으키|하게\s*하|하도록)\S{0,4}\s*(지\s*마|지\s*말|말\s*것|않|금지|안\s*됨|안\s*된다|불가)")
NO_VOMIT_CODES = {"H304": "흡인 유해성(H304)", "H314": "피부 부식성(H314)"}

# '위험' 신호어에만 쓰는 H코드(구분에 따라 갈리는 코드는 넣지 않는다).
DANGER_ONLY = {
    "H220", "H222", "H224", "H225", "H230", "H231", "H250", "H260", "H270", "H271",
    "H300", "H301", "H304", "H310", "H311", "H314", "H318", "H330", "H331", "H334",
    "H340", "H350", "H360", "H370", "H372",
}

# H코드 → 그림문자. 「화학물질의 분류·표시 및 물질안전보건자료에 관한 기준」 별표 2 기준.
PICTOGRAM_FOR = {}
for codes, ghs in (
    (("H200", "H201", "H202", "H203", "H204", "H240", "H241"), "GHS01"),
    (("H220", "H221", "H222", "H223", "H224", "H225", "H226", "H228", "H242", "H250", "H251", "H252",
      "H260", "H261"), "GHS02"),
    (("H270", "H271", "H272"), "GHS03"),
    (("H280", "H281"), "GHS04"),
    (("H290", "H314", "H318"), "GHS05"),
    (("H300", "H301", "H310", "H311", "H330", "H331"), "GHS06"),
    (("H302", "H312", "H332", "H315", "H317", "H319", "H335", "H336"), "GHS07"),
    (("H304", "H334", "H340", "H341", "H350", "H351", "H360", "H361", "H370", "H371", "H372", "H373"), "GHS08"),
    (("H400", "H410", "H411"), "GHS09"),
):
    for code in codes:
        PICTOGRAM_FOR[code] = ghs
GHS_NAMES = {"GHS01": "폭발성", "GHS02": "인화성", "GHS03": "산화성", "GHS04": "고압가스", "GHS05": "부식성",
             "GHS06": "급성독성", "GHS07": "유해/자극성", "GHS08": "건강유해성", "GHS09": "환경유해성"}


def codes_in(texts) -> set[str]:
    return {f"H{m}" for text in texts or [] for m in re.findall(r"H(\d{3})", str(text))}


def p_codes_in(precautions) -> set[str]:
    values = precautions.values() if isinstance(precautions, dict) else precautions or []
    return {f"P{m}" for group in values for text in (group or []) for m in re.findall(r"P(\d{3})", str(text))}


def required_pictograms(h_codes: set[str]) -> set[str]:
    needed = {PICTOGRAM_FOR[c] for c in h_codes if c in PICTOGRAM_FOR}
    # 우선순위: 해골(GHS06)이 있으면 급성독성 느낌표를 빼고, 부식성(GHS05)이 있으면
    # 피부·눈 자극 느낌표를 뺀다. 남는 느낌표 근거가 없으면 GHS07 은 필수가 아니다.
    if "GHS07" in needed:
        reasons = {c for c in h_codes if PICTOGRAM_FOR.get(c) == "GHS07"}
        if "GHS06" in needed:
            reasons -= {"H302", "H312", "H332"}
        if "GHS05" in needed:
            reasons -= {"H315", "H319"}
        if "GHS08" in needed and "H334" in h_codes:
            reasons -= {"H317"}
        if not reasons:
            needed.discard("GHS07")
    return needed


def normalize(text: str) -> str:
    return re.sub(r"[\s\W_]+", "", str(text or "")).lower()


def bigrams(text: str) -> set[str]:
    t = normalize(re.sub(r"[HP]\d{3}", "", text))
    return {t[i:i + 2] for i in range(len(t) - 1)}


def load():
    products = json.loads(PRODUCTS.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    by_file = {}
    for item in overrides:
        name = str(item.get("sourcePdfPath") or item.get("sourceRelativePath") or "").split("/")[-1]
        if name:
            by_file.setdefault(name, item)
    register = json.loads(REGISTER.read_text(encoding="utf-8"))["products"]
    return products, by_file, register


def shown(product: dict, override: dict) -> dict:
    """조회 화면이 보여 주는 값(app.js getDetailData·getDisplayGhsPictograms 와 같은 차례)."""
    hazards = override.get("hazardStatements") or product.get("hazardStatements") or []
    precautions = override.get("precautionaryStatements") if any((override.get("precautionaryStatements") or {}).values()) \
        else product.get("precautionaryStatements") or {}
    ghs = product.get("ghsCodes") or override.get("labelGhsCodes") or override.get("ghsCodes") or []
    return {"hazards": hazards, "precautions": precautions, "ghs": set(ghs), "firstAid": product.get("firstAid") or {}}


def check_rules(products, by_file, register):
    findings = []
    phrase_by_code = defaultdict(Counter)
    statements = []
    for product in products:
        if product.get("hazardNotClassified"):
            continue
        view = shown(product, by_file.get(product.get("fileName"), {}))
        for text in view["hazards"]:
            for code in re.findall(r"H\d{3}", str(text)):
                body = re.sub(r"^[\s\W]*(?:H\d{3}[\s+·,]*)+", "", str(text)).strip()
                if body:
                    phrase_by_code[code][normalize(body)] += 1
                    statements.append((product, code, body))

    for product in products:
        if product.get("hazardNotClassified"):
            continue
        entry = register.get(product["id"], {})
        view = shown(product, by_file.get(product.get("fileName"), {}))
        h = codes_in(view["hazards"])
        p = p_codes_in(view["precautions"])

        def add(rule, level, message):
            findings.append({"id": product["id"], "productName": product["productName"],
                             "supplier": product.get("supplier", ""), "pdfPath": product.get("pdfPath", ""),
                             "rule": rule, "level": level, "message": message,
                             "acknowledged": bool(entry.get("sourceIssue"))})

        ingestion = " ".join(view["firstAid"].get("ingestion") or [])
        sentences = [s for s in re.split(r"(?<=[.다오함])\s+", ingestion) if INDUCE_VOMIT.search(s) and not NEGATED.search(s)]
        if sentences:
            reasons = [name for code, name in NO_VOMIT_CODES.items() if code in h]
            if "P331" in p:
                reasons.append("예방조치 P331(토하게 하지 마시오)")
            if reasons:
                add("구토", "높음", f"{', '.join(reasons)} 이(가) 있는데 응급조치(삼켰을 때)가 구토를 시키라고 함: "
                                    f"\"{sentences[0][:60]}\"")

        signal = str(product.get("signalWord") or "")
        danger = sorted(h & DANGER_ONLY)
        if signal == "경고" and danger:
            add("신호어", "높음", f"신호어가 '경고'인데 '위험'에만 쓰는 {', '.join(danger)} 이(가) 있음")

        missing = sorted(required_pictograms(h) - view["ghs"])
        if missing and view["ghs"]:
            add("그림문자", "보통", "H코드가 요구하는 그림문자가 없음: "
                + ", ".join(f"{g}({GHS_NAMES[g]})" for g in missing))

    for product, code, body in statements:
        # 영문 원문(시약 등)은 다른 제품의 한글 문장과 비교하지 않는다.
        if len(re.findall(r"[A-Za-z]", body)) > len(re.findall(r"[가-힣]", body)):
            continue
        counts = phrase_by_code[code]
        if sum(counts.values()) < 4:
            continue
        common, n = counts.most_common(1)[0]
        if normalize(body) == common or n < 3:
            continue
        ref = {common[i:i + 2] for i in range(len(common) - 1)}
        mine = bigrams(body)
        if not ref or not mine:
            continue
        similarity = len(ref & mine) / len(ref | mine)
        if similarity < 0.2:
            entry = register.get(product["id"], {})
            findings.append({"id": product["id"], "productName": product["productName"],
                             "supplier": product.get("supplier", ""), "pdfPath": product.get("pdfPath", ""),
                             "rule": "문구 짝", "level": "보통",
                             "message": f"{code} 문장이 다른 제품들과 딴판: \"{body[:50]}\"",
                             "acknowledged": bool(entry.get("sourceIssue"))})
    return findings


def check_evidence(products, register):
    """관리대장에 원문 확인을 적은 뒤 그 자리의 PDF 가 바뀌었으면 다시 볼 것으로 올린다."""
    import hashlib

    by_id = {p["id"]: p for p in products}
    findings = []
    for pid, entry in register.items():
        evidence = entry.get("sourceIssueEvidence") or {}
        product = by_id.get(pid)
        if not evidence.get("sha256") or not product:
            continue
        path = ROOT / str(product.get("pdfPath") or "")
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() != evidence["sha256"]:
            findings.append({"id": pid, "productName": product["productName"], "supplier": product.get("supplier", ""),
                             "pdfPath": product.get("pdfPath", ""), "rule": "원문 바뀜", "level": "높음",
                             "message": f"{evidence.get('checkedOn', '')} 에 원문 확인을 적은 뒤 PDF 가 바뀌었음. "
                                        "새 판에서 그 문제가 풀렸는지 보고 관리대장을 고칠 것",
                             "acknowledged": False})
    return findings


def check_pdf(products, by_file):
    """화면 문장이 원본 PDF 글자층에 있는지. 띄어쓰기·문장부호는 빼고 맞춘다."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import msds_pdf_text as T  # noqa: E402

    findings = []
    for product in products:
        path = ROOT / str(product.get("pdfPath") or "")
        if not path.is_file() or product.get("hazardNotClassified"):
            continue
        try:
            pdf = normalize("".join(T.page_texts(path)))
        except Exception:  # 읽히지 않는 PDF 는 건너뛴다
            continue
        view = shown(product, by_file.get(product.get("fileName"), {}))
        lines = [("유해·위험문구", t) for t in view["hazards"]]
        lines += [("예방조치문구", t) for group in (view["precautions"] or {}).values() for t in group or []]
        lines += [("응급조치", t) for group in view["firstAid"].values() for t in group or []]
        checked = []
        for kind, text in lines:
            body = normalize(re.sub(r"[HP]\d{3}(?:\s*\+\s*[HP]\d{3})*", "", str(text)))
            if len(body) >= 8:
                checked.append((kind, text, body[:40] in pdf))
        if not checked:
            continue
        missing = [(kind, text) for kind, text, ok in checked if not ok]
        if len(missing) > len(checked) * 0.6:
            findings.append({"id": product["id"], "productName": product["productName"], "rule": "PDF 대조",
                             "level": "참고", "message": f"원문 글자층이 깨져 대조하지 못함({len(missing)}/{len(checked)}줄)",
                             "pdfPath": product.get("pdfPath", ""), "acknowledged": False})
            continue
        for kind, text in missing:
            findings.append({"id": product["id"], "productName": product["productName"], "rule": "PDF 대조",
                             "level": "보통", "message": f"{kind} 문장을 원문에서 못 찾음: \"{str(text)[:60]}\"",
                             "pdfPath": product.get("pdfPath", ""), "acknowledged": False})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pdf", action="store_true", help="원본 PDF 에 그 문장이 있는지도 본다")
    parser.add_argument("--json", action="store_true", help=f"결과를 {REPORT.relative_to(ROOT).as_posix()} 에 적는다")
    parser.add_argument("--strict", action="store_true", help="관리대장에 안 적힌 '높음' 이 있으면 실패")
    args = parser.parse_args()

    products, by_file, register = load()
    findings = check_rules(products, by_file, register) + check_evidence(products, register)
    if args.pdf:
        findings += check_pdf(products, by_file)

    order = {"높음": 0, "보통": 1, "참고": 2}
    findings.sort(key=lambda f: (order.get(f["level"], 9), f["rule"], f["productName"]))
    counts = Counter((f["rule"], f["level"], f["acknowledged"]) for f in findings)
    print(f"제품 {len(products)}건 점검")
    for (rule, level, acknowledged), n in sorted(counts.items(), key=lambda x: (order.get(x[0][1], 9), x[0][0])):
        print(f"  [{level}] {rule:6} {n}건{' (공급사 확인 요청함)' if acknowledged else ''}")
    for f in findings:
        if f["level"] != "참고" and not f["acknowledged"]:
            print(f"    - {f['rule']} · {f['productName'][:28]} ({f['id']}): {f['message']}")

    if args.json:
        REPORT.parent.mkdir(exist_ok=True)
        REPORT.write_text(json.dumps(findings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"적었다: {REPORT.relative_to(ROOT).as_posix()}")
    open_high = [f for f in findings if f["level"] == "높음" and not f["acknowledged"]]
    if args.strict and open_high:
        print(f"!! 관리대장에 안 적힌 '높음' {len(open_high)}건. 원문을 보고 고치거나 sourceIssue 를 적으세요.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
