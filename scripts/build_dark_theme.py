#!/usr/bin/env python
"""Generate the dark theme block from the light stylesheet.

화면 곳곳에 색을 직접 적어 둔 곳이 530군데라 선택자를 하나씩 대응할 수 없다.
밝은 화면 규칙을 읽어 색의 밝기만 뒤집은 어두운 화면 규칙을 만들어 붙인다.

색상(빨강·주황)은 그대로 두고 밝기만 바꾸므로 위험을 알리는 색이 유지된다.
밝은 화면 규칙은 건드리지 않고 뒤에 덧붙이기만 한다.
"""

from __future__ import annotations

import argparse
import colorsys
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSS = ROOT / "css" / "style.css"
MARKER = "/* ==== 어두운 화면: 자동 생성 구간 시작 ==== */"
END_MARKER = "/* ==== 어두운 화면: 자동 생성 구간 끝 ==== */"

# 이 속성만 바꾼다. 크기나 배치는 건드리지 않는다.
COLOR_PROPS = ("color", "background", "background-color", "border-color",
               "border-top-color", "border-bottom-color", "border-left-color",
               "border-right-color", "outline-color", "fill", "stroke")

HEX = re.compile(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")
RGBA = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)")


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def flip_lightness(r: int, g: int, b: int) -> tuple[int, int, int]:
    """밝기를 뒤집되 완전한 검정·흰색은 피한다.

    아주 밝은 면은 눈이 부시지 않을 만큼만 어둡게, 진한 글자는 너무 희지 않게
    옮긴다. 색상은 유지해서 위험을 알리는 빨강이 빨강으로 남는다.
    """
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    flipped = 1.0 - l
    # 무채색에 가까운 면은 배경으로 쓰이므로 더 눌러 준다.
    if s < 0.18:
        flipped = clamp(flipped, 0.08, 0.90)
        if l > 0.85:          # 흰 면 -> 어두운 면
            flipped = clamp(0.10 + (1.0 - l) * 0.6, 0.08, 0.18)
        elif l < 0.25:        # 검은 글자 -> 밝은 글자
            flipped = clamp(0.86 + (0.25 - l) * 0.3, 0.80, 0.93)
    else:
        # 색이 있는 값은 대비만 확보하고 너무 튀지 않게 채도를 조금 낮춘다.
        flipped = clamp(flipped, 0.16, 0.86)
        s = clamp(s * 0.9, 0.0, 0.85)
    nr, ng, nb = colorsys.hls_to_rgb(h, flipped, s)
    return round(nr * 255), round(ng * 255), round(nb * 255)


def to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def convert_value(value: str) -> str:
    def hex_sub(match: re.Match) -> str:
        digits = match.group(1)
        if len(digits) == 3:
            digits = "".join(ch * 2 for ch in digits)
        r, g, b = (int(digits[i:i + 2], 16) for i in (0, 2, 4))
        return to_hex(*flip_lightness(r, g, b))

    def rgba_sub(match: re.Match) -> str:
        r, g, b = (int(match.group(i)) for i in (1, 2, 3))
        alpha = match.group(4)
        nr, ng, nb = flip_lightness(r, g, b)
        return f"rgba({nr}, {ng}, {nb}, {alpha})" if alpha else f"rgb({nr}, {ng}, {nb})"

    return RGBA.sub(rgba_sub, HEX.sub(hex_sub, value))


def first_lightness(value: str) -> float | None:
    """선언에 처음 나오는 색의 밝기. 어두운 면인지 가리는 데 쓴다."""
    hex_match = HEX.search(value)
    if hex_match:
        digits = hex_match.group(1)
        if len(digits) == 3:
            digits = "".join(ch * 2 for ch in digits)
        r, g, b = (int(digits[i:i + 2], 16) for i in (0, 2, 4))
    else:
        rgba_match = RGBA.search(value)
        if not rgba_match:
            return None
        r, g, b = (int(rgba_match.group(i)) for i in (1, 2, 3))
    return colorsys.rgb_to_hls(r / 255, g / 255, b / 255)[1]


def strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def split_rules(css: str):
    """중괄호 깊이를 세어 최상위 규칙과 미디어쿼리를 나눈다."""
    depth = 0
    start = 0
    for index, char in enumerate(css):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                yield css[start:index + 1]
                start = index + 1


def convert_block(block: str) -> str:
    head, _, rest = block.partition("{")
    body = rest.rstrip()[:-1] if rest.rstrip().endswith("}") else rest
    selector = " ".join(head.split())

    if selector.startswith("@media"):
        inner = "".join(convert_block(part) for part in split_rules(body))
        return f"{selector} {{\n{inner}}}\n\n" if inner.strip() else ""
    if selector.startswith("@") or not selector:
        return ""
    # 이미 어두운 화면용으로 적은 규칙은 건드리지 않는다.
    if "[data-theme" in selector:
        return ""

    declarations = []
    for declaration in body.split(";"):
        if ":" not in declaration:
            continue
        prop, _, value = declaration.partition(":")
        prop = prop.strip()
        value = value.strip()
        if prop.startswith("--") or prop not in COLOR_PROPS:
            continue
        if not (HEX.search(value) or RGBA.search(value)):
            continue
        declarations.append((prop, value))

    if not declarations:
        return ""

    by_prop = dict(declarations)
    bg_value = by_prop.get("background") or by_prop.get("background-color")
    fg_value = by_prop.get("color")

    # 이미 어두운 면은 뒤집으면 오히려 밝아진다. 그대로 둔다.
    if bg_value is not None and first_lightness(bg_value) is not None:
        if first_lightness(bg_value) < 0.30:
            return ""

    kept = []
    for prop, value in declarations:
        # 배경 없이 밝은 글자만 적힌 규칙은, 이미 어두운 바탕 위에 있는 글자다.
        # 뒤집으면 어두운 바탕에 어두운 글자가 된다.
        if prop == "color" and bg_value is None:
            lightness = first_lightness(value)
            if lightness is not None and lightness > 0.62:
                continue
        converted = convert_value(value)
        if converted != value:
            kept.append(f"  {prop}: {converted};")

    if not kept:
        return ""
    scoped = ", ".join(f'[data-theme="dark"] {part.strip()}' for part in selector.split(","))
    return f"{scoped} {{\n" + "\n".join(kept) + "\n}\n\n"


# 밝기를 뒤집는 것만으로는 맞지 않는 곳을 마지막에 바로잡는다.
MANUAL_TAIL = '''/* ── 자동 변환으로 맞지 않는 부분 손질 ─────────────────── */

/* GHS 그림문자는 흰 바탕에 빨간 마름모로 그려져 있다.
 * 바탕까지 어둡게 하면 마름모 테두리가 사라져 무슨 그림인지 알 수 없다. */
[data-theme="dark"] .ghs-item img,
[data-theme="dark"] .ghs-icon img,
[data-theme="dark"] .label-pictogram img,
[data-theme="dark"] .poster-ghs-row img {
  background: #ffffff;
  border-radius: 6px;
  padding: 2px;
}

/* 머리글은 원래 어두운 색이라 뒤집으면 오히려 밝아진다. 그대로 둔다. */
[data-theme="dark"] .site-header {
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0) 34%),
    linear-gradient(135deg, #0a1614 0%, #0d2a26 58%, #10453a 100%);
  color: #e7f0ed;
}

[data-theme="dark"] .site-header h1,
[data-theme="dark"] .header-note,
[data-theme="dark"] .dataset-meta,
[data-theme="dark"] .dataset-meta dt,
[data-theme="dark"] .dataset-meta dd,
[data-theme="dark"] .current-selection {
  color: #dcece7;
}

[data-theme="dark"] body {
  background:
    linear-gradient(180deg, #0a1412 0, #0a1412 292px, transparent 292px),
    linear-gradient(135deg, #101b19 0%, #0e1715 45%, #111d1a 100%);
  color: var(--color-ink);
}

/* 위험을 알리는 배지는 대비를 확실히 확보한다. */
[data-theme="dark"] .hazard-badge {
  background: #b3261e;
  color: #ffffff;
  border-color: #ff8d82;
}

/* 화면 전환 버튼은 어두운 머리글 위에 있어 밝게 둔다. */
[data-theme="dark"] .theme-toggle {
  border-color: rgba(255, 255, 255, 0.34);
  background: rgba(255, 255, 255, 0.12);
  color: #eaf7f2;
}

[data-theme="dark"] .theme-toggle:hover {
  border-color: rgba(255, 255, 255, 0.6);
  background: rgba(255, 255, 255, 0.2);
}

/* H·P 코드 배지는 글자가 작아 대비를 넉넉히 준다. */
[data-theme="dark"] .safety-code-badge {
  background: #1d3a33;
  border-color: #46a68d;
  color: #a9ecd8;
}

/* ── 면의 높낮이 ───────────────────────────────────────────
 * 밝기만 뒤집으면 바탕과 카드가 같은 어둡기가 되어 카드가 카드로 보이지 않는다.
 * 바닥 → 패널 → 카드 순서로 조금씩 밝게 해서 얹혀 있는 느낌을 준다.
 * 글자는 면 위에서 또렷하도록 밝은 쪽으로 고정한다.
 */

[data-theme="dark"] {
  --surface-0: #0e1715;   /* 페이지 바닥 */
  --surface-1: #16211f;   /* 패널 */
  --surface-2: #1e2b28;   /* 패널 위의 카드 */
  --surface-3: #26332f;   /* 카드 위의 작은 면 */
  --on-surface: #e8f1ee;
  --on-surface-muted: #a3b7b1;
}

[data-theme="dark"] .search-panel,
[data-theme="dark"] .selection-panel,
[data-theme="dark"] .detail-block,
[data-theme="dark"] .poster-board,
[data-theme="dark"] .offline-panel,
[data-theme="dark"] .search-assist {
  background: var(--surface-1);
  border-color: #2b3a36;
  color: var(--on-surface);
}

[data-theme="dark"] .info-item,
[data-theme="dark"] .info-item.is-highlight,
[data-theme="dark"] .info-item.is-empty,
[data-theme="dark"] .summary-item,
[data-theme="dark"] .poster-block,
[data-theme="dark"] .first-aid-block,
[data-theme="dark"] .worker-caution-category,
[data-theme="dark"] .selection-item,
[data-theme="dark"] .full-product-item,
[data-theme="dark"] .full-product-item.is-pdf-based,
[data-theme="dark"] .component-table,
[data-theme="dark"] .component-table-wrap,
[data-theme="dark"] .shortcut-chip,
[data-theme="dark"] .notice,
[data-theme="dark"] .no-ghs {
  background: var(--surface-2);
  background-image: none;
  border-color: #32423d;
  color: var(--on-surface);
}

[data-theme="dark"] .info-item.is-highlight {
  border-color: #3f7d68;
}

[data-theme="dark"] .info-icon,
[data-theme="dark"] .search-heading-icon,
[data-theme="dark"] .component-table th,
[data-theme="dark"] .search-assist-head {
  background: var(--surface-3);
  color: var(--on-surface);
}

/* 라벨처럼 보조로 읽는 글자만 한 단계 낮춘다. */
[data-theme="dark"] .info-label,
[data-theme="dark"] .summary-label,
[data-theme="dark"] .search-help,
[data-theme="dark"] .poster-footer,
[data-theme="dark"] .detail-note,
[data-theme="dark"] .summary-note {
  color: var(--on-surface-muted);
}

/* 값으로 읽는 글자는 또렷하게. */
[data-theme="dark"] .info-text,
[data-theme="dark"] .info-value,
[data-theme="dark"] .summary-value,
[data-theme="dark"] .component-table td,
[data-theme="dark"] .detail-block li,
[data-theme="dark"] .detail-block p {
  color: var(--on-surface);
}

/* 그림자는 어두운 화면에서 더 깊게 */
[data-theme="dark"] .search-panel,
[data-theme="dark"] .detail-block,
[data-theme="dark"] .poster-board,
[data-theme="dark"] .selection-item,
[data-theme="dark"] .full-product-item {
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.45);
}

'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate dark theme rules.")
    parser.add_argument("--css", type=Path, default=DEFAULT_CSS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    css = args.css.read_text(encoding="utf-8")

    # 이전에 생성한 구간은 걷어내고 다시 만든다.
    start = css.find(MARKER)
    if start >= 0:
        end = css.find(END_MARKER)
        css = css[:start] + (css[end + len(END_MARKER):] if end >= 0 else "")
        css = css.rstrip() + "\n"

    source = strip_comments(css)
    generated = "".join(convert_block(block) for block in split_rules(source))

    rules = generated.count("{")
    output = (css.rstrip() + "\n\n\n" + MARKER + "\n"
              "/* build_dark_theme.py 가 만든다. 직접 고치지 말고 스크립트를 다시 돌린다. */\n\n"
              + generated + MANUAL_TAIL + END_MARKER + "\n")
    args.css.write_text(output, encoding="utf-8", newline="\n")

    print(f"어두운 화면 규칙 {rules}개 생성")
    print(f"- 파일: {args.css.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
