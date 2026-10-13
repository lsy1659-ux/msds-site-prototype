"""CAS 전체 토큰과 체크 숫자 검증. 형식 검증은 물질 동일성 검증이 아니다."""
import re

CAS_SHAPE = re.compile(r"[0-9]{2,7}-[0-9]{2}-[0-9]")
CAS_TOKEN = re.compile(r"(?<![0-9A-Za-z_-])[0-9]{2,7}-[0-9]{2}-[0-9](?![0-9A-Za-z_-])")
SOURCE_IDENTIFIER = re.compile(r"T-[0-9]{4}-[0-9]+(?:\([0-9]{4}-[0-9]{2}-[0-9]{2}\))?")

def join_identifier_date(text):
    return re.sub(r"(?<=[0-9]{4}-[0-9]{2}-)\s+(?=[0-9]{2}\))", "", text)

def valid_cas(value):
    text = str(value or '').strip()
    if not CAS_SHAPE.fullmatch(text):
        return False
    digits = text.replace('-', '')
    return sum(int(d) * i for i, d in enumerate(reversed(digits[:-1]), 1)) % 10 == int(digits[-1])

def extract_cas(text):
    return [m.group(0) for m in CAS_TOKEN.finditer(text) if valid_cas(m.group(0))]
