"""화면 파일의 판 번호를 올린다.

    py scripts/bump_asset_version.py

오프라인 저장(서비스워커)은 화면 파일을 주소가 똑같을 때 저장본으로
돌려준다. 그래서 js 나 css 를 고쳐도 `?v=` 가 그대로면 이미 저장해 둔
브라우저에는 옛 파일이 계속 나간다. 고친 것이 반영되지 않는다.

판 번호를 올리면 주소가 달라져 새로 받아 간다. sw.js 의 CACHE_VERSION 도
같이 올려 옛 저장칸을 비운다.

파일을 고친 뒤 올리기 전에 부른다. 암호를 바꿀 때는
scripts/set_admin_passcode.py 가 알아서 부른다.

    py scripts/bump_asset_version.py              판 번호를 올린다
    py scripts/bump_asset_version.py --if-changed 화면 파일이 바뀌었을 때만 올린다
    py scripts/bump_asset_version.py --check      바뀌었는데 안 올렸으면 실패(테스트·CI 용)

판 번호를 올리는 것을 잊으면 고친 화면이 현장 폰에 안 간다. 그래서 sw.js 에
화면 파일 전체의 지문(SHELL_FINGERPRINT)을 적어 둔다. 화면 파일을 고치고 판
번호를 안 올리면 지문이 안 맞아 테스트가 실패한다. 줄바꿈(CRLF/LF)은 지문에
넣지 않는다. 회사 PC 와 GitHub 의 줄바꿈이 달라도 같은 지문이 나온다.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["index.html", "label.html", "guide.html", "substance.html", "register.html"]
SW = ROOT / "sw.js"

ASSET_VERSION = re.compile(r'\?v=[0-9A-Za-z._-]+')
CACHE_VERSION = re.compile(r'(const CACHE_VERSION = "msds-)([0-9A-Za-z-]+)(";)')
FINGERPRINT = re.compile(r'(const SHELL_FINGERPRINT = ")([0-9a-f]*)(";)')


def shell_assets() -> list[str]:
    """sw.js 의 SHELL_ASSETS 가운데 이 저장소에 있는 파일."""
    source = SW.read_text(encoding="utf-8")
    block = source[source.index("const SHELL_ASSETS"):source.index("const DATA_ASSETS")]
    return sorted(name for name in re.findall(r'"([^"]+)"', block) if (ROOT / name).is_file())


def shell_fingerprint() -> str:
    """화면 파일 전체의 지문. 파일 이름과 내용(줄바꿈은 LF 로 맞춤)을 차례로 해시한다."""
    digest = hashlib.sha256()
    for name in shell_assets():
        data = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
        digest.update(name.encode("utf-8") + b"\0" + data + b"\0")
    return digest.hexdigest()[:16]


def recorded_fingerprint() -> str:
    found = FINGERPRINT.search(SW.read_text(encoding="utf-8"))
    return found.group(2) if found else ""


def write_fingerprint() -> str:
    value = shell_fingerprint()
    source = SW.read_text(encoding="utf-8")
    if FINGERPRINT.search(source):
        source = FINGERPRINT.sub(rf"\g<1>{value}\g<3>", source)
    else:
        source = source.replace(
            "const SHELL_CACHE", '// 화면 파일 지문. scripts/bump_asset_version.py 가 적는다. 손으로 고치지 않는다.\n'
            f'const SHELL_FINGERPRINT = "{value}";\nconst SHELL_CACHE', 1)
    SW.write_text(source, encoding="utf-8")
    return value


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

    # 판 번호를 화면 파일에 적은 뒤에 지문을 낸다. 판 번호도 화면 파일의 일부다.
    write_fingerprint()
    return version


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="화면 파일이 바뀌었는데 판 번호를 안 올렸으면 실패")
    mode.add_argument("--if-changed", action="store_true", help="화면 파일이 바뀌었을 때만 올린다")
    args = parser.parse_args()

    stale = recorded_fingerprint() != shell_fingerprint()
    if args.check:
        if stale:
            print("!! 화면 파일(js·css·html)이 바뀌었는데 판 번호를 안 올렸다.")
            print("   py scripts/bump_asset_version.py 를 돌리고 같이 올리세요.")
            return 1
        print("화면 파일 지문이 판 번호와 맞다.")
        return 0
    if args.if_changed and not stale:
        print(f"화면 파일이 그대로라 판 번호({current_version()})를 그대로 둔다.")
        return 0

    was = current_version()
    now = bump()
    print(f"판 번호 {was or '(없음)'} -> {now}")
    print(f"  화면 {len(PAGES)}개와 sw.js 를 고쳤다.")
    print("  이걸 같이 올려야 이미 저장해 둔 브라우저에도 새 파일이 간다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
