"""성분표에서 이름이 잘못 들어간 행을 찾아 원본 PDF 값으로 되돌린다.

MSDS 제3항 구성성분 표를 PDF 에서 긁을 때 두 가지가 어긋난다.

  가. 표 머리글이나 쪽 번호가 이름 칸에 들어간다.
      물질 이름 자리에 "번호:" 나 "( 3 / 14 )" 같은 것이 저장된다.
  나. 표의 행이 한 칸씩 밀려 이름과 CAS 의 짝이 어긋난다.
      톨루엔 자리에 아세톤 이름이 들어가는 식이다.

이 표가 작업환경측정과 특수건강진단 판단의 근거라 어긋난 채로 두면
결론이 틀린다.

옳고 그름을 아는 곳은 원본뿐이다. 그래서 제품마다 PDF 의 구성성분
표를 통째로 읽어 CAS 와 이름의 짝을 만들어 두고, 저장된 값을 그
짝과 맞춰 본다. 제품끼리 견주는 방법도 써 봤지만 표의 두 줄이 통째로
맞바뀐 경우는 양쪽 다 틀려서 걸러지지 않았다.

고치는 것은 저장된 이름이 같은 표의 "다른 CAS" 이름일 때뿐이다.
행이 밀렸다는 뜻이기 때문이다. 톨루엔과 Toluene 처럼 같은 물질을
달리 적은 것은 건드리지 않는다. 건드리면 멀쩡한 한글 이름이 영문으로
바뀐다. 업체마다 표기가 다른 것은 잘못이 아니다.

원본에서 확인되지 않거나 줄을 깔끔히 못 읽은 행도 손대지 않고
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

# 업체가 만든 PDF 가 제각각이라 pypdf 가 글꼴·참조 경고를 쏟아 낸다.
# 읽는 데는 지장이 없고, 정작 봐야 할 결과가 묻힌다.
import logging
logging.getLogger("pypdf").setLevel(logging.CRITICAL)

from pypdf import PdfReader

DATA = Path("data/msds.public.json")
REPORT_DIR = Path("reports")

CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")
CAS_IN_LINE = re.compile(r"\b\d{2,7}-\d{2}-\d\b")
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


def same_substance(source: str, current: str) -> bool:
    """원본 줄의 이름과 저장된 이름이 같은 물질을 가리키는가.

    글자가 똑같아야 같은 것은 아니다. 띄어쓰기, 괄호 안 영문, 사내
    코드가 붙고 떨어지는 것은 늘 있는 일이다. 알맹이가 한쪽에 들어
    있으면 같은 것으로 보고 손대지 않는다. 자일렌 자리에 아세트산
    뷰틸이 앉은 것처럼 알맹이가 아예 다를 때만 고친다.
    """
    here, there = name_core(current), name_core(source)
    if not here or not there:
        return False
    if here == there:
        return True
    shorter, longer = sorted((here, there), key=len)
    return len(shorter) >= 3 and shorter in longer


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


def read_cas_table(pages: list[str]) -> dict[str, tuple[int, str]]:
    """PDF 의 구성성분 표를 CAS 번호 -> (쪽, 이름) 으로 읽어 둔다.

    한 행만 보면 우리 값이 틀렸는지 알 수 없다. 같은 표에 어떤 짝들이
    있는지 함께 봐야 행이 밀렸는지 가릴 수 있다.
    """
    table: dict[str, tuple[int, str]] = {}
    for number, text in enumerate(pages, 1):
        for line in text.splitlines():
            for cas in set(CAS_IN_LINE.findall(line)):
                if cas in table:
                    continue
                name = tidy(name_from_line(line, cas))
                if name:
                    table[cas] = (number, name)
    return table


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

    # 나. CAS 가 있는 모든 행. 원본과 맞는지는 뒤에서 PDF 를 보고 가린다.
    #
    # 처음에는 제품끼리 견주어 수상한 행만 골랐다. 그런데 표의 두 줄이
    # 통째로 맞바뀐 경우는 그렇게 안 걸린다. 양쪽 다 틀려서 견줄 기준이
    # 없기 때문이다. 결국 옳고 그름을 아는 곳은 원본뿐이라, CAS 가 있는
    # 행은 모두 원본과 맞춰 본다.
    for row in rows:
        if not groupable_cas(row["cas"]):
            continue
        targets.setdefault((row["productId"], row["index"]), {**row, "kind": "원본과 대조"})

    return sorted(targets.values(), key=lambda r: (r["productId"], r["index"]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="확인된 행만 실제로 고친다")
    args = parser.parse_args()

    products = json.loads(DATA.read_text(encoding="utf-8"))
    targets = find_targets(products)

    cache: dict[str, list[str]] = {}
    table_cache: dict[str, dict[str, tuple[int, str]]] = {}
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

        if pdf not in table_cache:
            table_cache[pdf] = read_cas_table(cache[pdf])
        table = table_cache[pdf]
        page_no, source_name = table.get(cas, (None, ""))

        if not groupable_cas(cas):
            action = "손대지 않음 (CAS 없음)"
        elif (problem := unusable_source(source_name, target["name"])):
            action = f"손대지 않음 ({problem})"
        elif is_junk_name(source_name):
            action = "손대지 않음 (원본 줄도 깨끗하지 않음)"
        elif same_substance(source_name, target["name"]):
            action = "손대지 않음 (원본이 그렇게 적음)"
        elif is_junk_name(target["name"]):
            # 이름 자리에 표 머리글이나 쪽 번호가 들어온 행. 원본으로 채운다.
            action = "이름 교체"
        elif any(other != cas and same_substance(name, target["name"])
                 for other, (_, name) in table.items()):
            # 지금 이름이 같은 표의 다른 CAS 이름이다. 행이 밀렸다는 뜻이라
            # 원본의 짝으로 되돌린다. 이 조건이 아니면 손대지 않는다.
            # 톨루엔과 Toluene 처럼 같은 물질을 달리 적은 것까지 건드리면
            # 멀쩡한 한글 이름이 영문으로 바뀐다.
            action = "이름 교체"
        else:
            action = "손대지 않음 (원본과 표기만 다름)"

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
