"""올리기 전에 한 줄로 돌린다. 빠뜨리면 CI 가 깨지는 일을 차례대로 한다.

    py scripts/prepare_release.py              판 번호까지 올린다
    py scripts/prepare_release.py --no-bump    화면 파일을 안 고쳤으면 판 번호는 그대로

하는 일.

  1. 관리대장 반영          scripts/apply_msds_register.py --write
  2. 문구 꼴·PDF 대조 보완  scripts/normalize_public_content.py --write
  3. 화면 판 번호 올리기     scripts/bump_asset_version.py (--no-bump 이면 건너뜀)
  4. 테스트                 python -m unittest
  5. 배포 목록 다시 만들기   validate_public_release.py --write-manifest
  6. CI 와 같은 검증         validate_public_release.py --check-manifest

2026-09-18 부터 닷새 동안 5번을 빠뜨려 CI 가 계속 실패했는데 아무도 몰랐다.
데이터나 PDF 를 바꿨으면 커밋 전에 이것을 돌린다. 하나라도 실패하면 멈추고
무엇이 실패했는지 알린다.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate-msds-release.yml"


def expected_products() -> str:
    """CI 가 기대하는 제품 수. 워크플로 파일에서 읽어 같은 값으로 검증한다."""
    found = re.search(r"--expected-products\s+(\d+)", WORKFLOW.read_text(encoding="utf-8"))
    return found.group(1) if found else "0"


def run(title: str, *args: str) -> None:
    print(f"\n== {title}")
    completed = subprocess.run([sys.executable, *args], cwd=ROOT)
    if completed.returncode != 0:
        print(f"\n!! 실패: {title}. 위 메시지를 보고 고친 뒤 다시 돌리세요.")
        raise SystemExit(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-bump", action="store_true", help="판 번호를 올리지 않는다")
    args = parser.parse_args()
    count = expected_products()

    run("관리대장 반영", "scripts/apply_msds_register.py", "--write")
    run("문구 꼴·PDF 대조 보완", "scripts/normalize_public_content.py", "--write")
    if not args.no_bump:
        run("화면 판 번호 올리기", "scripts/bump_asset_version.py")
    run("테스트", "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py")
    run("배포 목록 다시 만들기", "scripts/validate_public_release.py", "--expected-products", count,
        "--write-manifest", "data/release-manifest.json", "--data-cutoff-date", date.today().isoformat())
    run("CI 와 같은 검증", "scripts/validate_public_release.py", "--expected-products", count,
        "--check-manifest", "data/release-manifest.json")
    print(f"\n모두 통과했습니다(제품 {count}건). 이제 커밋하고 올리면 됩니다.")
    print("제품 수가 바뀌었으면 .github/workflows/validate-msds-release.yml 의 --expected-products 도 고치세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
