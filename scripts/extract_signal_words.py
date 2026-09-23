"""원본 PDF 제2항에서 신호어(위험·경고·해당없음)를 뽑는다.

모든 제품에 같은 규칙을 쓴다. 뽑은 값은 data/msds-register.json 의 제품마다
signalWord 로 들어가고, scripts/apply_msds_register.py 가 사이트 데이터에
반영한다.

    py scripts/extract_signal_words.py            살펴보기만
    py scripts/extract_signal_words.py --write    관리대장에 적기

왜 따로 뽑는가. 경고표지와 관리요령이 신호어를 hazardBadge 칸에서 먼저
가져왔는데, 이 칸은 신호어가 아니라 228건 중 180건에 일괄로 들어간 "위험"
이었다. 그래서 원문이 "경고"인 18건이 "위험"으로, 원문이 "위험"인 14건이
빈칸으로 인쇄됐다. 원문에서 직접 뽑은 값만 쓰도록 바꾼다.

원문 모양이 제각각이라 네 번 나눠 본다. 앞에서 찾으면 뒤는 보지 않는다.

  1. '신호어 : 위험', 'Signal word : Danger' 처럼 바로 붙은 것
  2. '신호어 (GHS KR) 위험.', '신호어 1/17 - 위험' 처럼 사이에 뭐가 낀 것
  3. 표 모양이라 칸 이름과 값이 같은 줄에 멀리 떨어진 것
  4. 글꼴이 깨져 '신'이 '싞'으로 찍힌 것 (KCC 일부 PDF)

함정이 하나 있다. '신호어 유해·위험문구' 처럼 칸 이름 속 '위험' 을 신호어로
읽으면 안 된다. 다른 글자에 붙은 '위험' 은 버리고, 다음 칸 이름에서 멈춘다.

'자료없음' 은 모름으로 둔다. 원문이 신호어를 적지 않았다는 뜻이지 해당이
없다는 뜻이 아니다.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings("ignore")
logging.getLogger("pypdf").setLevel(logging.CRITICAL)
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = ROOT / "data" / "msds.public.json"
REGISTER = ROOT / "data" / "msds-register.json"

# '신' 이 '싞' 으로 찍히는 깨진 글꼴이 있다. 같은 칸 이름으로 본다.
LABEL = r"(?:신|싞)\s*호\s*어"
DIRECT = re.compile(LABEL + r"\s*[:：]?\s*[-○·]?\s*(위\s*험|경\s*고|해\s*당\s*없\s*음|없\s*음|적용되지\s*않음)")
DIRECT_EN = re.compile(r"Signal\s*word\(?s?\)?\s*[:：]?\s*(Danger|Warning|위험|경고|None|No signal word|Not applicable)", re.I)
DIRECT_JA = re.compile(r"注意喚起語\s*[:：]?\s*(危険|警告)")
NEAR_LABEL = re.compile(r"(" + LABEL + r"|Signal\s*word\(?s?\)?)", re.I)
SAME_LINE = re.compile(r"^\s*[∘○◦·\-]?\s*" + LABEL + r"\s*[:：]?(.*)$", re.M)
# 다른 글자에 붙지 않은 말만. '유해·위험문구' 의 위험은 앞에 '·', 뒤에 '문' 이 붙는다.
STANDALONE = re.compile(r"(?<![가-힣·ㆍ])(위\s?험|경\s?고|해당\s*없음|Danger|Warning)(?![가-힣A-Za-z])", re.I)
NEXT_FIELD = re.compile(r"유해\s*[·ㆍ∙]?\s*위험\s*문구|Hazard\s*statement|예방조치|그림문자|Pictogram", re.I)


def norm(word: str) -> str:
    w = re.sub(r"\s", "", word).lower()
    if w in ("위험", "danger", "危険"):
        return "위험"
    if w in ("경고", "warning", "警告"):
        return "경고"
    if w in ("해당없음", "없음", "none", "nosignalword", "notapplicable", "적용되지않음"):
        return "해당없음"
    return ""


def first_direct(text: str) -> str:
    for pattern in (DIRECT, DIRECT_EN, DIRECT_JA):
        for m in pattern.finditer(text):
            value = norm(m.group(1))
            if value:
                return value
    return ""


def first_near(text: str) -> str:
    for m in NEAR_LABEL.finditer(text):
        window = text[m.end(): m.end() + 40]
        stop = NEXT_FIELD.search(window)
        if stop:
            window = window[: stop.start()]
        hit = STANDALONE.search(window)
        if hit:
            return norm(hit.group(1))
    return ""


def first_same_line(text: str) -> str:
    for m in SAME_LINE.finditer(text):
        rest = m.group(1)
        stop = NEXT_FIELD.search(rest)
        if stop:
            rest = rest[: stop.start()]
        hit = STANDALONE.search(rest)
        if hit:
            return norm(hit.group(1))
    return ""


def signal_from_pdf(path: Path) -> tuple[str, str]:
    """(신호어, 몇 번째 규칙에서 찾았나)."""
    pages = PdfReader(str(path)).pages[:4]
    plain = "\n".join((page.extract_text() or "") for page in pages)
    value = first_direct(plain)
    if value:
        return value, "1"
    value = first_near(plain)
    if value:
        return value, "2"
    layout = "\n".join((page.extract_text(extraction_mode="layout") or "") for page in pages)
    value = first_near(layout) or first_same_line(layout)
    if value:
        return value, "3"
    return "", ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="관리대장의 signalWord 를 채운다")
    args = parser.parse_args()

    products = json.loads(PRODUCTS.read_text(encoding="utf-8"))
    register = json.loads(REGISTER.read_text(encoding="utf-8")) if REGISTER.exists() else None

    tally: Counter = Counter()
    conflicts = []
    results: dict[str, tuple[str, str]] = {}
    for product in products:
        stored = str(product.get("signalWord") or "").strip()
        stored = stored if stored in ("위험", "경고", "해당없음") else ""
        found, how = signal_from_pdf(ROOT / product["pdfPath"])
        if stored and found and stored != found:
            conflicts.append((product["productName"], stored, found))
        # 저장값과 원문이 둘 다 있으면 134건 모두 같았다(2026-09-23). 원문이 먼저다.
        value = found or stored
        source = f"pdf{how}" if found else ("stored" if stored else "none")
        results[product["id"]] = (value, source)
        tally[(value or "(모름)", source.rstrip("0123456789") or source)] += 1

    for (value, source), count in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"  {value:6} {source:7} {count}")
    print(f"저장값과 원문이 다른 제품: {len(conflicts)}")
    for name, stored, found in conflicts:
        print(f"   {name[:40]}  저장 {stored} / 원문 {found}")

    if not args.write:
        return 0
    if register is None:
        print("관리대장이 없다. 먼저 data/msds-register.json 을 만든다.")
        return 1
    items = register.setdefault("products", {})
    for pid, (value, source) in results.items():
        entry = items.setdefault(pid, {})
        entry["signalWord"] = value
        entry["signalSource"] = source
    REGISTER.write_text(json.dumps(register, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"관리대장에 신호어 {len(results)}건을 적었다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
