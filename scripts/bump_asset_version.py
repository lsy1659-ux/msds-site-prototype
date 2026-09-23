"""화면 파일의 판 번호를 올린다.

    py scripts/bump_asset_version.py

오프라인 저장(서비스워커)은 화면 파일을 주소가 똑같을 때 저장본으로
돌려준다. 그래서 js 나 css 를 고쳐도 `?v=` 가 그대로면 이미 저장해 둔
브라우저에는 옛 파일이 계속 나간다. 고친 것이 반영되지 않는다.

판 번호를 올리면 주소가 달라져 새로 받아 간다. sw.js 의 CACHE_VERSION 도
같이 올려 옛 저장칸을 비운다.

파일을 고친 뒤 올리기 전에 부른다. 암호를 바꿀 때는
scripts/set_admin_passcode.py 가 알아서 부른다.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["index.html", "label.html", "guide.html", "substance.html", "register.html"]
SW = ROOT / "sw.js"

ASSET_VERSION = re.compile(r'\?v=[0-9A-Za-z._-]+')
CACHE_VERSION = re.compile(r'(const CACHE_VERSION = "msds-)([0-9A-Za-z-]+)(";)')


def next_version(current: str) -> str:
    """오늘 날짜에 차례를 붙인다. 하루에 여러 번 올려도 겹치지 않는다."""
    today = date.today().strftime("%Y%m%d")
    match = re.match(rf"{today}-(\d+)$", current)
    return f"{today}-{int(match.group(1)) + 1}" if match else f"{today}-1"


def current_version() -> str:
    source = (ROOT / PAGES[0]).read_text(encoding="utf-8")
    found = re.search(r'\?v=([0-9A-Za-z._-]+)', source)
    return found.group(1) if found else ""


def bump() -> str:
    version = next_version(current_version())

    for name in PAGES:
        path = ROOT / name
        path.write_text(ASSET_VERSION.sub(f"?v={version}", path.read_text(encoding="utf-8")),
                        encoding="utf-8")

    source = SW.read_text(encoding="utf-8")
    if CACHE_VERSION.search(source):
        SW.write_text(CACHE_VERSION.sub(rf"\g<1>{version}\g<3>", source), encoding="utf-8")
    else:
        print("!! sw.js 에서 CACHE_VERSION 을 못 찾았다. 손으로 올려야 한다.")

    return version


def main() -> int:
    was = current_version()
    now = bump()
    print(f"판 번호 {was or '(없음)'} -> {now}")
    print(f"  화면 {len(PAGES)}개와 sw.js 를 고쳤다.")
    print("  이걸 같이 올려야 이미 저장해 둔 브라우저에도 새 파일이 간다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
