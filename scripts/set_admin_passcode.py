"""관리자 가림막의 암호를 바꾼다.

    py scripts/set_admin_passcode.py "새암호"

js/admin-gate.js 의 PASS_HASH 한 줄만 갈아 끼운다. 암호 자체는 어디에도
저장하지 않는다. 저장소에 남는 것은 SHA-256 값뿐이다.

다만 이것이 암호를 지켜 준다는 뜻은 아니다. 이 사이트는 서버가 없는
정적 사이트라 암호를 확인하는 일이 브라우저 안에서 일어나고, 저장소가
공개라 해시도 같이 공개된다. 짧거나 흔한 말은 해시만 보고도 금방
되짚어진다. 애초에 잠금이 아니라 가림막이므로, 이 뒤에는 새어 나가도
곤란하지 않은 것만 둔다. 자세한 까닭은 js/admin-gate.js 첫머리에 적었다.

그러니 여기에는 다른 곳에서 쓰는 암호를 절대 쓰지 않는다.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bump_asset_version

# 어느 폴더에서 부르든 되게 한다. 현재 폴더를 기준으로 삼으면 저장소
# 뿌리로 먼저 옮겨 가야 하는데, 그 한 걸음 때문에 안 바꾸고 넘어간다.
GATE = Path(__file__).resolve().parents[1] / "js" / "admin-gate.js"
LINE = re.compile(r'(const PASS_HASH = ")[0-9a-f]{64}(";)')


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not argv[0].strip():
        print(__doc__)
        return 2

    passcode = argv[0]
    if len(passcode.strip()) < 6:
        print("암호가 너무 짧다. 여섯 글자 이상으로 한다.")
        return 1

    source = GATE.read_text(encoding="utf-8")
    if not LINE.search(source):
        print(f"{GATE} 에서 PASS_HASH 줄을 찾지 못했다.")
        return 1

    digest = hashlib.sha256(passcode.encode("utf-8")).hexdigest()
    GATE.write_text(LINE.sub(rf"\g<1>{digest}\g<2>", source), encoding="utf-8")

    # 판 번호를 같이 올린다. 안 올리면 오프라인 저장이 옛 파일을 계속
    # 돌려주어, 이미 한 번 들어온 브라우저에서는 암호가 안 바뀐다.
    version = bump_asset_version.bump()

    # 암호는 찍지 않는다. 화면을 누가 보고 있을지 모른다.
    root = GATE.parent.parent
    print(f"{GATE} 의 암호를 바꿨다.")
    print(f"  해시 {digest[:16]}…")
    print(f"  판 번호도 {version} 로 올렸다. 저장해 둔 브라우저까지 새 암호가 간다.")
    print()
    print("이제 아래를 붙여 넣으면 사이트에 반영된다.")
    print(f'  git -C "{root}" add -A')
    print(f'  git -C "{root}" commit -m "관리자 암호 변경"')
    print(f'  git -C "{root}" push')
    print()
    print("이미 열어 둔 브라우저는 그대로 열려 있다. 잠그려면 관리자 패널에서")
    print("[관리자 모드 끄기] 를 누른다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
