"""성분표에서 이름이 잘못 들어간 행을 찾아 원본 PDF 값으로 되돌린다.

MSDS 제3항 구성성분 표를 PDF 에서 긁을 때 두 가지가 어긋난다.

  가. 표 머리글이나 쪽 번호가 이름 칸에 들어간다.
      물질 이름 자리에 "번호:" 나 "( 3 / 14 )" 같은 것이 저장된다.
  나. 표의 행이 한 칸씩 밀려 이름과 CAS 의 짝이 어긋난다.
      톨루엔 자리에 아세톤 이름이 들어가는 식이다.

이 표가 작업환경측정과 특수건강진단 판단의 근거라 어긋난 채로 두면
결론이 틀린다.

고칠 때는 원본 PDF 에서 그 CAS 가 적힌 줄을 찾아 같은 줄의 이름을
쓴다. 다수결로 덮어쓰지 않는다. 업체마다 같은 물질을 다르게 적는
일이 흔해서, 다수결을 정답으로 삼으면 멀쩡한 동의어를 지운다.

원본에서 확인되지 않거나 줄을 깔끔히 못 읽은 행은 손대지 않고
사람이 볼 수 있게 남긴다.

    py scripts/repair_ingredient_rows.py            살펴보기만
    py scripts/repair_ingredient_rows.py --apply    확인된 것만 고치기
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import warnings
from datetime import date
from pathlib import Path

warnings.filterwarnings("ignore")
from pypdf import PdfReader

DATA = Path("data/msds.public.json")
REPORT_DIR = Path("reports")

CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")
NOT_A_CAS = ("미기재", "영업비밀", "비공개", "해당없음", "없음", "mixture", "혼합물")

# 물질 이름으로 볼 수 없는 값. 표 머리글과 쪽 번호가 대부분이다.
HEADER_ONLY = re.compile(
    r"^(cas|casno|cas번호|번호|물질명|화학물질명|명칭|성분명|구성성분|관용명|이명|함유량|[\s\-·.:;()/])*$",
    re.I,
)
PAGE_MARK = re.compile(r"\(\s*\d+\s*/\s*\d+\s*\)")
NUMBERS_ONLY = re.compile(r"^[\d\s\-./%~]+$")

# 한 글자여도 물질 이름인 것들. 규칙으로 거르면 이것까지 걸린다.
SHORT_BUT_REAL = {"물", "납", "철", "은", "금", "황", "인"}

# 표 한 줄을 칸으로 나누는 기준. 칸 사이는 넉넉히 벌어져 있고,
# 한 칸 안에서도 글자가 벌어지지만 그보다는 좁다.
COLUMN_GAP = re.compile(r"\s{4,}")

# 이름 칸 뒤에 붙는 이명(異名) 칸의 길이 한도. 이보다 길면 이름이
# 접혀 넘어온 것으로 보고 떼지 않는다.
ALIAS_MAX = 60
TRAILING_AMOUNT = re.compile(r"\s*\d+(\.\d+)?\s*[~\-–]\s*\d+(\.\d+)?\s*%?\s*$")


def tidy(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" .·|-")


def is_junk_name(name: str) -> str | None:
    """이름으로 쓸 수 없는 값이면 그 까닭을 돌려준다."""
    if not name.strip():
        return "빈칸"
    flat = re.sub(r"[\s()（）]", "", name)
    if HEADER_ONLY.match(flat):
        return "표 머리글"
    if PAGE_MARK.search(name):
        return "쪽 번호 섞임"
    if NUMBERS_ONLY.match(name):
        return "숫자만"
    if len(flat) < 2 and flat not in SHORT_BUT_REAL:
        return "너무 짧음"
    return None


def name_core(raw: str) -> str:
    text = re.sub(r"[(（].*?[)）]", " ", raw)
    text = re.split(r"[/;,]", text)[0]
    return re.sub(r"[\s\-·]", "", text).lower()


def groupable_cas(cas: str) -> bool:
    return bool(CAS_RE.match(cas)) and not any(w in cas.lower() for w in NOT_A_CAS)


def read_pages(path: str) -> list[str]:
    pages = []
    for page in PdfReader(path).pages:
        try:
            pages.append(page.extract_text(extraction_mode="layout") or "")
        except Exception:
            pages.append(page.extract_text() or "")
    return pages


def name_from_line(line: str, cas: str) -> str:
    """CAS 가 적힌 줄에서 물질 이름 칸만 떼어 낸다.

    줄 모양은 보통 이렇다.

        물질명            이명          CAS 번호      함유량

    CAS 앞쪽을 칸으로 나눈 뒤 마지막 칸(이명)을 떼면 이름이 남는다.
    이명 칸이 없는 표도 있어서, 떼고 나서 남는 게 없으면 되돌린다.
    """
    head = TRAILING_AMOUNT.sub("", line.split(cas)[0])
    columns = [tidy(part) for part in COLUMN_GAP.split(head) if tidy(part)]
    if not columns:
        return ""
    if len(columns) >= 2 and len(columns[-1]) <= ALIAS_MAX:
        trimmed = " ".join(columns[:-1])
        if len(re.sub(r"\s", "", trimmed)) >= 2:
            return trimmed
    return " ".join(columns)


def unusable_source(source: str, current: str) -> str | None:
    """PDF 에서 떼어 낸 이름을 쓰면 안 되는 경우.

    표가 여러 줄로 접히거나 칸이 어긋나면 이름의 뒤쪽만 잡히거나
    옆 칸이 딸려 온다. 그런 값으로 덮어쓰면 지금보다 나빠진다.
    걸러낸 행은 고치지 않고 사람이 보도록 남긴다.
    """
    if not source:
        return "원본에서 못 찾음"
    if source[0] in "()/,·":
        return "원본 줄에서 이름 칸을 놓침"
    if source.count("(") != source.count(")"):
        return "원본 줄이 중간에서 잘림"
    if "%" in source:
        return "원본 줄에 함유량이 섞임"
    flat = re.sub(r"\s", "", source)
    if len(flat) < 3 and flat not in SHORT_BUT_REAL:
        return "원본 줄에서 이름이 너무 적게 잡힘"
    # 지금 이름의 꼬리만 잡힌 경우. 접힌 줄의 둘째 줄을 읽은 것이다.
    here = re.sub(r"\s", "", current)
    if here and flat != here and here.endswith(flat):
        return "지금 이름의 뒷부분만 잡힘"
    return None


def find_targets(products: list[dict]) -> list[dict]:
    rows = []
    for product in products:
        for index, ingredient in enumerate(product.get("ingredients") or []):
            rows.append({
                "productId": product["id"],
                "productName": product.get("productName", ""),
                "pdfPath": product.get("pdfPath", ""),
                "index": index,
                "cas": (ingredient.get("casNo") or "").strip(),
                "name": (ingredient.get("chemicalName") or "").strip(),
            })

    # 가. 이름 자리에 쓰레기가 들어간 행
    targets = {}
    for row in rows:
        reason = is_junk_name(row["name"])
        if reason:
            targets[(row["productId"], row["index"])] = {**row, "kind": reason}

    # 나. 이름이 다른 CAS 의 통상 이름인 행 (표가 밀린 자취)
    usable = [r for r in rows if groupable_cas(r["cas"]) and r["name"]]
    by_cas: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for row in usable:
        by_cas[row["cas"]][name_core(row["name"])] += 1
    consensus = {cas: names.most_common(1)[0][0] for cas, names in by_cas.items()}
    owner: dict[str, set[str]] = collections.defaultdict(set)
    for cas, core in consensus.items():
        owner[core].add(cas)

    for row in usable:
        core = name_core(row["name"])
        if core == consensus[row["cas"]]:
            continue
        if not (owner.get(core, set()) - {row["cas"]}):
            continue
        key = (row["productId"], row["index"])
        targets.setdefault(key, {**row, "kind": "다른 물질 이름"})

    return sorted(targets.values(), key=lambda r: (r["productId"], r["index"]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="확인된 행만 실제로 고친다")
    args = parser.parse_args()

    products = json.loads(DATA.read_text(encoding="utf-8"))
    targets = find_targets(products)

    cache: dict[str, list[str]] = {}
    today = date.today().isoformat()
    findings = []

    for target in targets:
        cas, pdf = target["cas"], target["pdfPath"]
        if pdf not in cache:
            try:
                cache[pdf] = read_pages(pdf)
            except Exception as error:
                cache[pdf] = []
                print(f"!! PDF 읽기 실패 {pdf}: {error}")

        page_no, source_name = None, ""
        if groupable_cas(cas):
            for number, text in enumerate(cache[pdf], 1):
                hit = next((line for line in text.splitlines() if cas in line), None)
                if hit:
                    page_no, source_name = number, name_from_line(hit, cas)
                    break

        source_name = tidy(source_name)
        squashed = lambda text: re.sub(r"\s", "", text).lower()

        if not groupable_cas(cas):
            action = "손대지 않음 (CAS 없음)"
        elif (problem := unusable_source(source_name, target["name"])):
            action = f"손대지 않음 ({problem})"
        elif is_junk_name(source_name):
            action = "손대지 않음 (원본 줄도 깨끗하지 않음)"
        elif squashed(source_name) == squashed(target["name"]):
            action = "손대지 않음 (원본이 그렇게 적음)"
        else:
            action = "이름 교체"

        findings.append({
            **target,
            "pdfPage": page_no,
            "sourceName": source_name,
            "action": action,
            "checkedOn": today,
        })

    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / "ingredient_repair_review.json").write_text(
        json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")

    with (REPORT_DIR / "ingredient_repair_review.csv").open(
            "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["제품", "제품번호", "원본 PDF", "PDF 쪽", "CAS",
                         "원본 값", "현재 값", "왜 걸렸나", "조치", "확인일"])
        for row in findings:
            writer.writerow([row["productName"], row["productId"], row["pdfPath"],
                             row["pdfPage"] or "", row["cas"], row["sourceName"],
                             row["name"], row["kind"], row["action"], row["checkedOn"]])

    tally = collections.Counter(row["action"] for row in findings)
    print(f"살펴본 행 {len(findings)}개")
    for action, count in tally.most_common():
        print(f"  {action:<40} {count}행")

    if not args.apply:
        print("\n고치려면 --apply 를 붙여 다시 실행한다.")
        return 0

    changes = [row for row in findings if row["action"] == "이름 교체"]
    index = {product["id"]: product for product in products}
    for row in changes:
        index[row["productId"]]["ingredients"][row["index"]]["chemicalName"] = row["sourceName"]

    DATA.write_text(json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 한 번 고치면 다수결이 바뀌어 다음 판에 또 걸리는 행이 나온다.
    # 그래서 이력은 덮어쓰지 않고 쌓는다. 나중에 왜 바꿨는지 되짚을 수 있어야 한다.
    log_path = REPORT_DIR / "ingredient_repair_log.json"
    history = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
    history.extend(changes)
    log_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(changes)}행을 원본 값으로 고쳤다. 기록은 reports/ingredient_repair_log.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
