"""Shared style tokens and conservative text measurements."""

import math
import re
import unicodedata

FAMILIES: dict[str, dict[str, str]] = {
    # meaning            FILL       STROKE                 TITLE      SUB        LINE
    "neutral":   dict(fill="#F5F4ED", stroke="rgba(31,30,29,0.3)", title="#141413", sub="#3D3D3A", line="#73726C"),
    "green":     dict(fill="#E1F5EE", stroke="#0F6E56",            title="#085041", sub="#0F6E56", line="#1D9E75"),
    "purple":    dict(fill="#EEEDFE", stroke="#534AB7",            title="#3C3489", sub="#534AB7", line="#7F77DD"),
    "terracotta":dict(fill="#FAECE7", stroke="#993C1D",            title="#712B13", sub="#993C1D", line="#C75B38"),
    "amber":     dict(fill="#FAEEDA", stroke="#854F0B",            title="#633806", sub="#854F0B", line="#EF9F27"),
}

BG = "#FFFFFF"
NEUTRAL_LINE = FAMILIES["neutral"]["line"]
CAPTION = "#3D3D3A"
CONTAINER_TITLE = "#141413"
CONTAINER_SUB = "#3D3D3A"

FONT_STACK = ("'Anthropic Sans', -apple-system, BlinkMacSystemFont, "
              "'Segoe UI', 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB', "
              "'Noto Sans CJK SC', sans-serif")


def _is_wide(ch: str) -> bool:
    """True for CJK / full-width glyphs (~2x the width of a Latin letter)."""
    return unicodedata.east_asian_width(ch) in ("W", "F")

def text_width(s: str, size: int = 14) -> float:
    """Estimate rendered width of ``s`` in px at the given font ``size``.

    Latin / digit / punctuation ~= 8px and CJK ~= 15px at the 14px title size;
    both scale linearly with size (so ~7 / ~13 at 12px). The estimate errs wide
    on purpose so text never clips.
    """
    latin = size * 8 / 14
    wide = size * 15 / 14
    return sum(wide if _is_wide(ch) else latin for ch in s)

def box_width(*lines: str | None, sizes: tuple[int, ...] = (14, 12)) -> int:
    """Width that fits every line: max(line widths) + 32, min 120, rounded up to x4."""
    widest = 0.0
    for i, line in enumerate(lines):
        if not line:
            continue
        size = sizes[i] if i < len(sizes) else sizes[-1]
        widest = max(widest, text_width(line, size))
    raw = max(widest + 32, 120)
    return int(math.ceil(raw / 4) * 4)

WARM_PALETTE: set[str] = {
    "#f5f4ed", "#141413", "#3d3d3a", "#73726c",
    "#e1f5ee", "#0f6e56", "#085041", "#1d9e75",
    "#eeedfe", "#534ab7", "#3c3489", "#7f77dd",
    "#faece7", "#993c1d", "#712b13", "#c75b38",
    "#faeeda", "#854f0b", "#633806", "#ef9f27",
    "#fac775", "#f5c4b3", "#9fe1cb", "#cecbf6", "#f4c0d1", "#c0dd97", "#b5d4f4",
    "#f1efe8", "#5f5e5a", "#ffffff", "#000000", "#fff",
}
COLOR_KEYWORDS_OK = {"none", "transparent", "context-stroke", "currentcolor", "inherit"}


def normalize_hex(value: str) -> str | None:
    """Normalize hex and numeric RGB paints; alpha is checked separately."""
    value = value.strip().lower()
    if value in {"white", "black"}:
        return "#ffffff" if value == "white" else "#000000"
    match = re.fullmatch(r"#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})", value)
    if match:
        raw = match.group(1)
        raw = "".join(ch * 2 for ch in raw[:3]) if len(raw) in {3, 4} else raw[:6]
        return "#" + raw
    match = re.fullmatch(r"rgba?\((.*)\)", value)
    if not match:
        return None
    channels = re.split(r"[,\s]+", match.group(1).split("/", 1)[0].strip())[:3]
    try:
        if len(channels) != 3:
            return None
        numbers = [float(ch[:-1]) * 255 / 100 if ch.endswith("%") else float(ch) for ch in channels]
        if not all(math.isfinite(number) for number in numbers):
            return None
        return "#" + "".join(f"{min(255, max(0, math.floor(number + 0.5))):02x}" for number in numbers)
    except ValueError:
        return None


def is_cold_color(value: str) -> bool:
    hx = normalize_hex(value)
    if hx is None or hx in WARM_PALETTE:
        return False
    r = int(hx[1:3], 16)
    g = int(hx[3:5], 16)
    b = int(hx[5:7], 16)
    return b > r + 12 and b >= g - 4



# Include every family paint, including the neutral rgba border.
WARM_PALETTE.update(filter(None, (normalize_hex(value) for family in FAMILIES.values() for value in family.values())))
