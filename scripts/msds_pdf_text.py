"""MSDS 원문 PDF 에서 절(항)을 나누고 H·P 문구, 분류, 성분, 응급조치, 날짜를 읽는다.

제조사마다 글자 배치가 다르다. 코드가 문장 앞에 오는 곳도 뒤에 오는 곳도 있고,
쪽 머리글이 문장 사이에 끼고, 절 순서가 글자층에서 뒤바뀐 PDF 도 있다. 제품마다
따로 맞추지 않고 모든 PDF 에 같은 규칙을 쓴다. 읽지 못한 칸은 비워 두고 채워
넣지 않는다.
"""
import re
from collections import Counter

from pypdf import PdfReader

CODE = re.compile(r"[HP]\d{3}[A-Za-z]?(?:\s*\+\s*[HP]\d{3}[A-Za-z]?)*")
HANGUL = re.compile(r"[가-힣]")
GROUP_LABEL = re.compile(r"^[\s·ㆍ∙•\-▪○]*(?:유해\s*[·ㆍ∙▪]?\s*위험\s*문구|예방\s*조치\s*문구|예방|대응|저장|폐기)\s*[:：]?\s*")
STOP_LINE = re.compile(
    r"^[\s·ㆍ∙•\-▪]*(?:[OoＯ○●◎]\s|[가-하]\s*[.．]|\d+(?:\.\d+)*\s*[.．]|예방|대응|저장|폐기|신\s*호\s*어|그림\s*문자"
    r"|심볼|유해|해당\s*없음|자료\s*없음)|분류\s*기준에\s*포함되지\s*않는|NFPA|\(GHS\s*KR\)")
CATEGORY = re.compile(r"구분\s*[:：]?\s*\d")
CAS = re.compile(r"\b\d{2,7}-\d{2}-\d\b")
AMOUNT = re.compile(r"(\d+(?:\.\d+)?)\s*[~\-–]\s*(\d+(?:\.\d+)?)|([<>≤≥]\s*\d+(?:\.\d+)?)|(?<![\d\-.])(\d+(?:\.\d+)?)\s*%")
# 절 제목. 번호와 제목이 함께 있어야 절 머리로 본다. 본문에 "응급조치" 가 나와도 걸리지 않게.
SECTION_TITLES = {
    1: r"화학\s*제품|identification",
    2: r"유해\s*성?\s*[·ㆍ∙.]?\s*위험\s*성|hazards?\s*identification",
    3: r"구성\s*성분|composition|information\s*on\s*ingredients",
    4: r"응급\s*조치|first[\s-]*aid",
    5: r"폭발|화재|fire[\s-]*fighting",
    6: r"누출|accidental\s*release",
    7: r"취급|handling",
    8: r"노출\s*방지|exposure\s*controls?",
    9: r"물리\s*화학|physical",
    10: r"안정성|stability",
    11: r"독성|toxicolog",
    12: r"환경|ecolog",
    13: r"폐기|disposal",
    14: r"운송|transport",
    15: r"법적|법규|regulatory",
    16: r"그\s*밖의|기타\s*참고|other\s*information",
}
HEADINGS = {
    n: re.compile(rf"^\s*(?:제\s*)?(?:section\s*)?(?<!\d){n}(?!\d)\s*(?:[.．:\-–]|항)?\s*[.．:\-–]?\s*(?:{title})", re.I)
    for n, title in SECTION_TITLES.items()
}

SECTION_WORDS = ("화학제품", "유해성", "유해 위험성", "구성성분", "응급조치", "폭발", "화재", "누출", "취급", "노출방지",
                 "물리화학", "안정성", "독성", "환경", "폐기", "운송", "법적", "그 밖의")
TRAILING_NUMBER = re.compile(r"^(?P<title>\D{2,40}?)\s*(?P<num>\d{1,2})\s*[.．]\s*[·ㆍ]?\s*$")
DISPLACED_DOT = re.compile(r"^(?P<mark>[가-하])\s+(?P<label>\S.*?)\s+[.．]\s+(?P<rest>.*)$")


def repair_line(line):
    """글자층에서 절 번호와 마침표가 뒤로 밀려 난 줄을 제자리로 돌린다.

    "응급조치요령 4." -> "4. 응급조치요령", "가 눈에 들어갔을 때 . 긴급…" -> "가. 눈에 들어갔을 때 긴급…"
    그렇게 만들어진 PDF 에서만 걸리고, 보통 PDF 의 줄은 이 모양이 아니라 그대로 남는다.
    """
    m = TRAILING_NUMBER.match(line.strip())
    title = m.group("title").strip() if m else ""
    if m and title.startswith(SECTION_WORDS) and ":" not in title and "구분" not in title:
        return f"{m.group('num')}. {title}"
    m = DISPLACED_DOT.match(line.strip())
    if m:
        return f"{m.group('mark')}. {m.group('label')} {m.group('rest')}"
    return line


def page_texts(path):
    pages = [(p.extract_text() or "") for p in PdfReader(str(path)).pages]
    return ["\n".join(repair_line(l) for l in text.splitlines()) for text in pages]


def page_texts_alt(path):
    """두 번째 글자 읽기(PyMuPDF, 위치 순). 두 칸 표 PDF 에서 pypdf 가 순서를 뒤섞을 때 쓴다.

    설치돼 있지 않으면 None. 없어도 다른 기능은 그대로 돈다.
    """
    try:
        import pymupdf
    except ImportError:
        return None
    with pymupdf.open(str(path)) as doc:
        pages = [page.get_text("text", sort=True) or "" for page in doc]
    return ["\n".join(repair_line(l) for l in text.splitlines()) for text in pages]


def statements_from(pages):
    """쪽 글에서 2항 문구를 읽는다. (유해문구, 예방조치 칸)"""
    lines = "\n".join(pages).splitlines()
    section2 = section(lines, 2)
    return parse_statements(section2, boilerplate(pages)) if section2 else ([], {})


def flat(text):
    return re.sub(r"\s+", " ", text).strip()


def key(line):
    """머리글·꼬리글 비교용. 쪽 번호가 달라도 같은 줄로 본다."""
    return re.sub(r"\d+", "#", flat(line))


def boilerplate(pages):
    """쪽마다 되풀이되는 머리글·꼬리글. 문장 사이에 끼어도 이어 붙이지 않는다."""
    seen = Counter()
    for text in pages:
        seen.update({key(l) for l in text.splitlines() if l.strip()})
    limit = max(2, len(pages) // 2)
    return {l for l, n in seen.items() if n >= limit}


def skip(line, junk):
    return not line or key(line) in junk or line.startswith("페이지") or set(line) <= set("_-= ")


def section(lines, number):
    """number 절의 줄들. 절 머리부터 다른 절 머리 앞까지.

    글자층에서 절 순서가 뒤바뀐 PDF 가 있어, 다음 번호가 아니라 아무 다른 절
    머리에서 멈춘다. 절 머리를 못 찾으면 빈 목록을 돌려준다.
    """
    joined = [flat(l) for l in lines]
    start = next((i for i, l in enumerate(joined) if HEADINGS[number].match(l)), -1)
    if start < 0:
        return []
    end = next((i for i in range(start + 1, len(joined))
                if any(h.match(joined[i]) for n, h in HEADINGS.items() if n != number)), len(joined))
    return lines[start:end]


def tidy_text(text):
    # 글자층에서 떨어져 나온 문장부호 찌꺼기("( ) .", " , ,")는 뺀다.
    text = re.sub(r"\(\s*\)", " ", flat(text))
    text = re.sub(r"(?:\s+[,.]+)+\s*$", "", text)
    return flat(text).strip(" ;:：-·ㆍ∙,○●◦•▪")


def ends_sentence(text):
    text = text.rstrip(" .)")
    if not text:
        return True
    last = text[-1]
    batchim_m = 0 <= ord(last) - 0xAC00 < 11172 and (ord(last) - 0xAC00) % 28 == 16
    return batchim_m or text.endswith(("시오", "것", "다")) or not HANGUL.match(last)


def join_wrapped(prev, prev_raw, raw):
    """접힌 줄을 잇는다. 한글 낱말 한가운데서 접혔으면 붙이고, 아니면 띄운다."""
    line = flat(raw)
    spaced = (prev_raw.endswith((" ", "\t")) or raw[:1].isspace() or ends_sentence(prev)
              or not HANGUL.match(line[0]))
    return tidy_text(prev + (" " if spaced else "") + line)


def parse_statements(lines, junk):
    """H·P 문구를 읽는다. 코드가 문장 앞에 오든 뒤에 오든 같은 규칙으로 읽는다.

    - 한 줄에 코드가 있으면 코드 뒤 글을 문구로 본다. 뒤에 한글이 없으면 앞 글을 본다.
    - "구분 1" 이 든 글은 분류 줄이라 문구로 치지 않는다.
    - 코드가 없는 줄은 앞 문구가 이어진 것으로 본다. 항목 이름이나 새 절로 시작하면 멈춘다.
    - 쪽마다 되풀이되는 머리글·꼬리글은 건너뛴다.
    """
    items, last, prev_raw = {}, None, ""
    for raw in lines:
        line = flat(raw)
        if skip(line, junk):
            continue
        found = list(CODE.finditer(line))
        if not found:
            # "인화성 액체 : 구분2" 같은 분류 줄은 이어지는 문장이 아니다. 두 칸 표에서 문구 뒤에
            # 분류 칸 값이 몰려 나오는 PDF 가 있어(오공본드 락카 스프레이) 여기서 멈춘다.
            if last and not STOP_LINE.search(line) and not CATEGORY.search(line) and HANGUL.search(line) and len(line) <= 120:
                items[last] = join_wrapped(items[last], prev_raw, raw)
            else:
                last = None
            prev_raw = raw
            continue
        prev_raw = raw
        last = None
        for n, m in enumerate(found):
            nxt = found[n + 1].start() if n + 1 < len(found) else len(line)
            after = tidy_text(line[m.end():nxt])
            before = tidy_text(GROUP_LABEL.sub("", line[(found[n - 1].end() if n else 0):m.start()]))
            text = after if HANGUL.search(after) else (before if n == 0 and HANGUL.search(before) else "")
            if not text or CATEGORY.search(text):
                continue
            code = re.sub(r"\s", "", m.group(0))
            if code not in items:
                items[code] = text
                last = code
                if text is not after:
                    prev_raw = ""   # 코드 앞 글을 썼으면 줄 끝 빈칸은 코드 뒤의 것이라 잇기 판단에 쓰지 않는다
    hazards = [f"{c} {t}" for c, t in items.items() if c.startswith("H")]
    groups = {"prevention": [], "response": [], "storage": [], "disposal": []}
    for c, t in items.items():
        if c.startswith("P"):
            group = {"1": "prevention", "2": "prevention", "3": "response", "4": "storage", "5": "disposal"}[c[1]]
            groups[group].append(f"{c} {t}")
    return hazards, groups


CLASS_LABEL = re.compile(r"유해\s*[.·ㆍ∙▪]?\s*위험성\s*분류|유해성\s*[·ㆍ∙]?\s*위험성\s*분류")
CLASS_STOP = re.compile(r"예방\s*조치|경고\s*표지|그림\s*문자|신\s*호\s*어|^\s*(?:나|2\.2)\s*[.．]")


def broken(text):
    depth = 0
    for ch in text:
        depth += ch in "(（"
        depth -= ch in ")）"
        if depth < 0:
            return True
    return depth != 0 or bool(re.search(r"\(\s*\)|\(\s*\d+\s*\)|\s:\s*\d+\(", text))


def parse_classification(lines, junk):
    """2항 가.(분류) 칸의 글을 그대로 옮긴다. 경고표지 항목이 나오면 멈춘다.

    원문 글자층이 깨져 괄호 짝이 안 맞는 글이 섞이면 None 을 돌려준다. 옮기면 틀린 글이 된다.
    """
    out, taking = [], False
    for raw in lines:
        line = flat(raw)
        if skip(line, junk):
            continue
        if not taking and CLASS_LABEL.search(line):
            taking = True
            line = CLASS_LABEL.split(line, 1)[1]
        elif taking and CLASS_STOP.search(line):
            break
        if taking:
            line = tidy_text(CODE.sub(" ", re.sub(r"^\s*[.．]\s*", "", line))).rstrip(".")
            if line and HANGUL.search(line):
                out.append(line)
    if any(broken(item) for item in out):
        return None
    return "; ".join(out)


def amount_text(m, line=""):
    if m.group(1):
        return f"{m.group(1)}~{m.group(2)}"
    if m.group(3):
        return re.sub(r"\s", "", m.group(3))
    bound = re.search(r"이상|이하", line)
    return f"{m.group(4)}%" + (f" {bound.group(0)}" if bound else "")


LABEL_ONLY = re.compile(r"^(?:번호|물질명|이명|관용명|화학물질명|\(|\))*$")


def parse_ingredients(lines, junk):
    """3항의 성분 줄. CAS 가 있는 줄은 CAS 로, 영업비밀 줄은 그 표기로 행을 만든다."""
    rows, pending = [], []
    body = [flat(l) for l in lines]
    body = [l for l in body if not skip(l, junk)]
    for line in body:
        cases = CAS.findall(line)
        secret = re.search(r"영업\s*비밀", line)
        if not cases and not secret:
            if rows and not rows[-1]["content"]:
                amt = AMOUNT.search(line)
                labelled = re.match(r"^함유량", line)
                if amt and (labelled or not re.search(r"[A-Za-z가-힣]{3,}", AMOUNT.sub("", line))):
                    rows[-1]["content"] = amount_text(amt, line)
                    continue
            pending.append(line)
            continue
        for cas in cases or ["영업비밀"]:
            head, _, tail = line.partition(cas if cases else secret.group(0))
            amt = AMOUNT.search(tail)
            in_head = None if amt else AMOUNT.search(head)
            name = re.sub(r"\((?:CAS|KE)[-\s]*No\.?\)|CAS\s*번호|번호\s*CAS|식별번호|CAS", " ", head)
            name = re.sub(r"자료\s*없음\.?", " ", name)
            if in_head:
                name = name.replace(in_head.group(0), " ")
            name = tidy_text(name)
            if not name or LABEL_ONLY.match(name.replace(" ", "")):
                label = next((l for l in reversed(pending) if l.startswith("물질명")), "")
                name = tidy_text(label.replace("물질명", "", 1)) if label else " ".join(pending[-3:])
            # 괄호 속에 표 머리글 낱말이 섞이면 글자층이 깨진 것이라 괄호째 뺀다.
            name = re.sub(r"\s*[(（][^()（）]*(?:번호|이하|이상|CAS)[^()（）]*[)）]?", " ", name)
            name = tidy_text(re.sub(r"[(（]\s*$", "", tidy_text(name)))
            hit = amt or in_head
            rows.append({"casNo": cas, "sourceName": name, "content": amount_text(hit, line) if hit else ""})
        pending = []
    return rows


AID_ENUM = r"^[\s　]*(?:[가-하]|[a-eA-E]|[1-5](?:\.\d)?)?\s*[.．)]?\s*"
AID = [
    # 영문 SDS 는 "IF IN EYES", "When inhaled :", "B. Skin contact" 처럼 적는다. 영문 항목 이름은 줄 끝이거나
    # 쌍점이 붙을 때만 항목으로 본다(문장 속 "skin contact" 에 걸리지 않게).
    ("eye", re.compile(AID_ENUM + r"(눈에\s*(?:들어갔을|접촉했을|묻었을)\s*때|눈에\s*들어간\s*경우|눈\s*[:：]"
                       r"|(?:eye\s*contact|if\s+in\s+eyes|when\s+you\s+get\s+into\s+your\s+eyes)\s*(?:[:：]|$))", re.I)),
    ("skin", re.compile(AID_ENUM + r"(피부(?:에|와)\s*(?:접촉했을|묻었을|닿았을)\s*때|피부에\s*묻은\s*경우|피부\s*[:：]"
                        r"|(?:skin\s*contact|contact\s+with\s+skin|if\s+on\s+skin(?:\s*\(or\s+hair\）?\)?)?)\s*(?:[:：]|$))", re.I)),
    ("inhalation", re.compile(AID_ENUM + r"((?:흡입|들이마셨)(?:했을|을)?\s*때|흡입한\s*경우|흡입\s*[:：]"
                              r"|(?:inhalation|if\s+inhaled|when\s+inhaled)\s*(?:[:：]|$))", re.I)),
    ("ingestion", re.compile(AID_ENUM + r"((?:먹었|삼켰|섭취했)을\s*때|삼킨\s*경우|섭취\s*[:：]"
                             r"|(?:ingestion|swallowing|if\s+swallowed|when\s+you\s+eat)\s*(?:[:：]|$))", re.I)),
    ("note", re.compile(AID_ENUM + r"((?:기타\s*)?의사의\s*주의\s*사항|기타\s*주의\s*사항"
                        r"|notes?\s*to\s*(?:the\s*)?physician\s*[:：]?|first\s+aid\s+and\s+doctor'?s\s+notes?\s*[:：]?)", re.I)),
]


def parse_first_aid(lines, junk):
    """4항. 항목 이름 뒤 같은 줄에 적힌 조치도 받는다. 접힌 줄은 잇는다."""
    result, current, prev_raw = {}, None, ""
    for raw in lines[1:]:
        line = flat(raw)
        if skip(line, junk):
            continue
        hit = None
        for name, pattern in AID:
            m = pattern.match(line)
            if m:
                hit = (name, m)
                break
        if hit:
            current = hit[0]
            result.setdefault(current, [])
            rest = tidy_text(line[hit[1].end():])
            if rest and re.search(r"[가-힣A-Za-z]", rest) and not re.fullmatch(r"자료\s*없음\.?", rest):
                result[current].append(rest)
            prev_raw = raw
            continue
        # 다른 절 제목이나, 응급조치 항목이 아닌 가./나. 항목이 나오면 4항이 끝난 것이다.
        # "4.1 Description …" 같은 소번호는 절 머리가 아니다. 숫자 뒤 점 다음에 글자가 올 때만 멈춘다.
        if current is not None and (re.match(r"^\d+\s*[.．]\s*[^\d\s.]", line) or re.match(r"^[가-하]\s*[.．]\s*\S", line)):
            break
        if re.match(r"^\d+(?:\.\d+)+\s", line):
            # "4.2 Most important symptoms" 같은 소항목 머리. 다음 항목 이름이 나올 때까지 모으지 않는다.
            if current is not None and not any(pattern.match(line) for _, pattern in AID):
                current = None
            continue
        if current is None or not re.search(r"[가-힣A-Za-z]", line):
            continue
        items = result[current]
        # 앞 줄이 짧으면 접힌 줄이 아니라 제목·값을 줄을 나눠 적은 것이다. 잇지 않는다.
        if items and not ends_sentence(items[-1]) and len(flat(prev_raw)) >= 30:
            items[-1] = join_wrapped(items[-1], prev_raw, raw)
        else:
            items.append(tidy_text(line))
        prev_raw = raw
    return {k: v for k, v in result.items() if v}


# 날짜. 2024.03.27 / 2024-3-27 / 2024년 3월 27일 / 18 3월 2021 / 07/Mar/2023
MONTHS = {m: i for i, m in enumerate(("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
DATE_FORMS = [
    (re.compile(r"((?:19|20)\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})"), (1, 2, 3)),
    (re.compile(r"(?<!\d)(\d{1,2})\s+(\d{1,2})월\s+((?:19|20)\d{2})"), (3, 2, 1)),
    (re.compile(r"(?<!\d)(\d{1,2})[/\s-]([A-Za-z]{3})[a-z]*[/\s-]((?:19|20)\d{2})"), (3, 2, 1)),
]
REVISION_LABELS = (r"최종\s*개정\s*일(?:자)?", r"개정\s*일(?:자)?", r"개정\s*날짜", r"revision\s*date", r"date\s*of\s*revision")
# 최초 작성일로 볼 수 있는 라벨만. 그냥 "작성일자" 는 제조사에 따라 이 판을 쓴 날이라 넣지 않는다.
ISSUE_LABELS = (r"최초\s*작성\s*일(?:자)?", r"제정\s*일(?:자)?", r"date\s*of\s*issue\s*for\s*the\s*1st\s*edition",
                r"created\s*date")


def all_dates(text):
    """글 안의 날짜를 나온 차례대로 모두 돌려준다."""
    found = []
    for pattern, (y, mo, d) in DATE_FORMS:
        for m in pattern.finditer(text):
            month = m.group(mo)
            month = MONTHS.get(month[:3].lower()) if month.isalpha() else int(month)
            if not month or not (1 <= month <= 12 and 1 <= int(m.group(d)) <= 31):
                continue
            found.append((m.start(), f"{int(m.group(y)):04d}-{month:02d}-{int(m.group(d)):02d}"))
    return [value for _, value in sorted(found)]


def first_date(text):
    dates = all_dates(text)
    return dates[0] if dates else ""


# 라벨 값이 끝나는 곳. 다음 항목(라./4.), 빈 줄, 다른 날짜 라벨(인쇄·대체·작성 …).
VALUE_END = re.compile(
    r"\n\s*(?:[가-하a-z]|\d{1,2})\s*[.．)]\s*[가-힣A-Za-z]|\n\s*\n|인쇄|대체|supersed|print|작성|제정|발행|최초|created",
    re.I)
# 최초 작성일 값은 개정일 라벨에서도 끝난다. 개정일 값은 "개정" 이 라벨 자신에 들어 있어 넣지 않는다.
ISSUE_VALUE_END = re.compile(VALUE_END.pattern + r"|개정|revision", re.I)


def labelled_dates(text, labels, value_end=VALUE_END):
    """라벨 값에 적힌 날짜를 모두 모은다. 앞 라벨에서 찾으면 뒤 라벨은 보지 않는다.

    "개정횟수 및 최종 개정일자 : 16차/2019.01.16, 17차/2019.02.11, 18차/…" 처럼 개정
    이력을 줄줄이 적는 제조사가 있어 값 안의 날짜를 모두 돌려준다. 최종 개정일은
    그 가운데 가장 늦은 날짜다. "2021-12-29 (최종 개정일자)" 처럼 날짜 뒤에 괄호
    라벨을 단 꼴도 읽는다.
    """
    flat_text = re.sub(r"[ \t]+", " ", text)
    for label in labels:
        found = []
        for m in re.finditer(label, flat_text, re.I):
            value = flat_text[m.end():m.end() + 1500]
            end = value_end.search(value, 1)
            found.extend(all_dates(value[:end.start()] if end else value))
        for m in re.finditer(r"([0-9./\-]{8,10})\s*\(\s*" + label + r"\s*\)", flat_text, re.I):
            found.extend(all_dates(m.group(1)))
        if found:
            return sorted(set(found))
    return []


def revision_date(text):
    """원문의 최종 개정일. 개정 이력이 줄줄이 적혔으면 가장 늦은 날짜. 못 찾으면 빈 문자열."""
    dates = labelled_dates(text, REVISION_LABELS)
    return dates[-1] if dates else ""


def issue_date(text):
    """원문의 최초 작성일. 라벨 값이 하나일 때만 돌려준다. 여러 개면 판단하지 않는다."""
    dates = labelled_dates(text, ISSUE_LABELS, ISSUE_VALUE_END)
    return dates[0] if len(dates) == 1 else ""


# 응급조치 항목이 제 자리인지 가리는 낱말. 글자층 순서가 뒤틀린 PDF 에서는 성분표 줄이나
# 다른 항목의 조치가 딸려 온다. 그런 줄은 원문에 있던 글이라도 그 칸의 내용이 아니다.
ROUTE_WORDS = {
    "eye": r"눈|eye",
    "skin": r"피부|의복|의류|옷|skin|cloth",
    "inhalation": r"공기|호흡|흡입|산소|air|breath|inhal",
    "ingestion": r"입|삼키|삼켰|먹|구토|토하|섭취|마시|mouth|swallow|vomit|ingest",
}
NOT_FIRST_AID = re.compile(r"\b\d{2,7}-\d{2}-\d\b|KE-\d|\bTWA\b|STEL|ppm|mg/m", re.I)
# 글꼴 연결이 깨진 PDF 에서 제 글자 대신 튀어나오는 음절("싞발을 벖고", "조얶을"). 보통 글에는 거의 안 나온다.
CORRUPTED = re.compile("[싞늒맊홖젂핚짂갂숚렦맋핛젗벖첛얶옦젘앆젃]")
# 마침표 없이 끝나는 영문 조치는 시키는 말로 시작할 때만 조치로 본다("Move person to fresh air").
ENGLISH_ACTION = re.compile(
    r"^(?:Rinse|Remove|Wash|Flush|Seek|Call|Get|Move|Give|Do|If|In\s+case|Take|Keep|Immediately|Supply|Promptly|"
    r"Continue|Clean|Administer|Consult|Never|Obtain|Loosen|Wipe|Transfer|Place|Show|Avoid|Treat|Apply|Use|Allow)\b")
SENTENCE = re.compile(r"(?:시오|것|다|음|함|됨|요|라|세요)\s*[.)]?\s*$|[.!]\s*$")
EMPTY_VALUE = re.compile(r"^(?:자료\s*없음|해당\s*없음|없음|정보\s*없음)\.?$")


def usable_first_aid(key, items):
    """새로 채울 응급조치 줄 가운데 그 칸에 맞는 것만 남긴다.

    - CAS·노출기준처럼 응급조치가 아닌 줄, 문장이 아닌 줄, '없음' 은 뺀다.
    - 눈·피부·흡입·섭취 칸은 그 경로를 가리키는 말이 한 줄도 없고 다른 경로의 말만
      있으면 통째로 버린다. 칸 이름이 어긋나 읽힌 것이다.
    """
    # 글꼴이 깨진 줄이 하나라도 있으면 그 칸은 통째로 두지 않는다. 깨진 줄만 빼면 핵심 조치가
    # 빠진 채 "의사의 치료를 받으시오" 만 남아 오히려 틀린 안내가 된다.
    if any(CORRUPTED.search(item) for item in items):
        return []
    kept = []
    for item in items:
        # 영문 SDS 의 조치는 마침표 없이 끝나기도 한다("Move person to fresh air"). 대문자로 시작하는
        # 세 낱말 이상의 영문 줄은 문장으로 본다.
        english = (re.match(r"^[A-Z][a-z]", item) and len(item.split()) >= 3
                   and (re.search(r"[.!]\s*$", item) or ENGLISH_ACTION.match(item)))
        if not re.search(r"[가-힣]", item) and not english:
            continue   # 한글이 없는 줄은 영문 문장일 때만("light arom.", "Solvent naphtha" 같은 성분표 조각은 뺀다)
        if (NOT_FIRST_AID.search(item) or CORRUPTED.search(item) or not (SENTENCE.search(item) or english)
                or EMPTY_VALUE.match(item.strip()) or item in kept):
            continue
        if key in ROUTE_WORDS:
            own = re.search(ROUTE_WORDS[key], item, re.I)
            other = any(re.search(words, item, re.I) for k, words in ROUTE_WORDS.items() if k != key)
            if other and not own:
                continue   # 다른 경로의 조치가 이 칸에 딸려 온 줄
        kept.append(item)
    if key in ROUTE_WORDS and kept:
        own = any(re.search(ROUTE_WORDS[key], item, re.I) for item in items)
        other = any(re.search(words, item, re.I) for k, words in ROUTE_WORDS.items() if k != key for item in items)
        if other and not own:
            return []   # 다른 경로의 말만 있고 이 경로의 말은 없다. 칸 이름이 어긋나 읽힌 것
    return kept


# 긴급전화번호. 라벨 바로 뒤(40자 안)의 번호를 먼저 본다. 두 칸 표로 라벨만 먼저
# 나오고 값이 뒤로 몰리는 PDF 가 있어, 라벨 뒤에 번호가 없으면 첫 쪽의 국내 전화번호가
# 하나뿐일 때만 그것을 쓴다. 여럿이면 어느 것인지 알 수 없어 비워 둔다.
PHONE = re.compile(r"(?<![\d-])0\d{1,2}[\s)\-.]{1,3}\d{3,4}[\s\-.]{1,3}\d{4}(?![\d-])")
EMERGENCY_LABEL = re.compile(r"긴급\s*(?:전화\s*번호|연락\s*처|연락\s*전화)|emergency\s*(?:tele)?phone", re.I)


def _phone_text(raw):
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 9 and digits.startswith("02"):
        return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
    if digits.startswith("02"):
        return f"{digits[:2]}-{digits[2:-4]}-{digits[-4:]}"
    return f"{digits[:3]}-{digits[3:-4]}-{digits[-4:]}"


def emergency_phone(pages):
    """원문의 긴급전화번호. 못 정하면 빈 문자열."""
    text = "\n".join(pages)
    for m in EMERGENCY_LABEL.finditer(text):
        found = PHONE.search(text[m.end():m.end() + 40])
        if found:
            return _phone_text(found.group(0))
    first_page = {_phone_text(p) for p in PHONE.findall(pages[0] if pages else "")}
    return first_page.pop() if len(first_page) == 1 else ""


# 공급자 주소. 라벨과 같은 줄의 값을 먼저 보고, 없으면 1항에 도로명 주소가 하나뿐일 때만 그것을 쓴다.
# 제조자·수입자 주소가 둘 다 적혀 있으면 어느 것이 공급자인지 알 수 없어 비워 둔다.
ADDRESS_LABEL = re.compile(r"^\s*[-·•]?\s*(?:[가-하]\.\s*)?(?:주\s*소|address)\s*[:：]?\s*(?P<value>.*)$", re.I)
ROAD_ADDRESS = re.compile(
    r"(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충청|충북|충남|전라|전북|전남|경상|경북|경남|제주)"
    r"[가-힣]*\s*(?:[가-힣]+(?:시|군|구)\s*){1,3}(?:[가-힣0-9]+(?:읍|면)\s*)?"
    # 도로명: "마포대로", "본산1로" 다음에 가지 길("4다길", "56번길")이 올 수 있다.
    r"[가-힣0-9·]+(?:로|길)(?:\s*\d+[가-힣]?(?:번)?길)?\s*\d+(?:-\d+)?"
    r"(?:\s*\([^)]{1,20}\))?")


def supplier_address(lines):
    """1항에서 공급자 주소를 읽는다. 못 정하면 빈 문자열."""
    body = [flat(l) for l in lines]
    for line in body:
        m = ADDRESS_LABEL.match(line)
        if m and len(m.group("value")) >= 8 and not re.search(r"e-?mail|@", m.group("value"), re.I):
            return tidy_text(m.group("value"))
    found = {tidy_text(m.group(0)) for line in body for m in ROAD_ADDRESS.finditer(line)}
    return found.pop() if len(found) == 1 else ""
