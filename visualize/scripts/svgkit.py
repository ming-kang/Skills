#!/usr/bin/env python3
"""svgkit — a tiny, zero-dependency builder for the visualize house style.

Why this exists
---------------
Hand-emitting every ``<rect>``/``<text>``/``<line>`` and mentally computing box
widths, edge anchors, and z-order is slow and error-prone. The #1 failure in
quick SVG diagrams is *text overflowing its box* — caused by guessing widths
instead of measuring them. svgkit does the boring math in code, deterministically:

* ``text_width`` measures a label (Latin ~8px, CJK ~15px at the 14px title size)
  so boxes are sized to fit, not eyeballed.
* ``Diagram`` owns the skeleton, the single open-chevron marker, the white
  background, ``<title>``/``<desc>``, automatic z-order, and a guaranteed
  ``</svg>`` close.
* ``node``/``arrow``/``lpath``/``container``/``legend`` map 1:1 to the house-style
  primitives and emit *exactly* the clean presentation-attribute form documented
  in ``references/svg-cookbook.md`` and ``references/style.md``.

It covers the tedious 80% (boxes, arrows, containers, legend). For the artistic
20% — scatter plots, patch grids, vector bars — use ``Diagram.raw()`` to drop in
hand-written SVG on any layer.

Standard library only. No third-party packages, ever.

Quick start
-----------
>>> from svgkit import Diagram
>>> d = Diagram(680, 200, title="RAG pipeline", desc="Query to grounded answer.")
>>> d.pipeline([
...     {"title": "Query", "sub": "user question"},
...     {"title": "Retriever", "sub": "top-k", "family": "green"},
... ], labels=["embed"], auto_legend=True)
>>> d.save("rag.svg")  # fit() grows the canvas; boxes sized from text

Path bootstrap (any cwd)
------------------------
>>> from svgkit import ensure_on_path  # only if already importable
>>> # Or, before import:
>>> #   from pathlib import Path; import sys
>>> #   from svgkit import ensure_on_path  # after sys.path has scripts/
"""

from __future__ import annotations

import math
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "FAMILIES",
    "text_width",
    "box_width",
    "snap",
    "resolve_scripts_dir",
    "ensure_on_path",
    "Box",
    "Lifeline",
    "Diagram",
]


# --------------------------------------------------------------------------- #
# Tokens — the single source of truth for these values is references/style.md.
# Keep them byte-for-byte in sync with that file.
# --------------------------------------------------------------------------- #

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

# The one marker. The open chevron recolors itself per line via context-stroke.
_MARKER = (
    '  <defs>\n'
    '    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5"\n'
    '            markerWidth="6" markerHeight="6" orient="auto-start-reverse">\n'
    '      <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke"\n'
    '            stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>\n'
    '    </marker>\n'
    '  </defs>'
)


# Layer order = SVG paint order (top of file paints first / sits at the back).
_LAYERS = ("containers", "arrows", "plates", "boxes", "box_text", "labels", "legend")

Point = tuple[float, float]


# --------------------------------------------------------------------------- #
# The boring math, done in code
# --------------------------------------------------------------------------- #

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


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def snap(n: float) -> str:
    """Integer-snap coordinates; drop a trailing .0 so output stays clean."""
    r = round(n)
    return str(int(r))


def _resolve_line(color: str | None) -> str:
    """Accept a family name or a safe CSS hex/rgb/rgba color."""
    if color is None:
        return NEUTRAL_LINE
    if color in FAMILIES:
        return FAMILIES[color]["line"]
    value = color.strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?", value):
        return value
    if re.fullmatch(r"rgba?\(\s*[\d.]+(?:\s*,\s*[\d.]+){2}(?:\s*,\s*[\d.]+)?\s*\)", value):
        return value
    raise ValueError("color must be a family name or a hex/rgb/rgba CSS color")


def _family(name: str) -> dict[str, str]:
    """Look up a color family; raise with a clear fix when the name is wrong."""
    try:
        return FAMILIES[name]
    except KeyError:
        known = ", ".join(FAMILIES)
        raise KeyError(f"unknown family {name!r}; choose from: {known}") from None


# Default legend glosses for auto_legend() — short, house-style meanings.
_FAMILY_GLOSS: dict[str, str] = {
    "neutral": "default / plumbing",
    "green": "primary / success",
    "purple": "alternate / parallel",
    "terracotta": "warning / failure",
    "amber": "highlight",
}


def resolve_scripts_dir(start: Path | str | None = None) -> Path | None:
    """Find this skill's ``scripts/`` directory from ``start`` (or cwd).

    Walks parents looking for either ``visualize/scripts/svgkit.py`` (repo root)
    or ``scripts/svgkit.py`` (skill root). Returns ``None`` if nothing matches.
    Lets agents import without hard-coding an absolute path or guessing cwd.
    """
    root = Path(start) if start is not None else Path.cwd()
    if root.is_file():
        root = root.parent
    for base in (root, *root.parents):
        for rel in (("visualize", "scripts"), ("scripts",)):
            candidate = base.joinpath(*rel)
            if (candidate / "svgkit.py").is_file():
                return candidate.resolve()
    # Last resort: directory of this file (when svgkit itself is already importable).
    here = Path(__file__).resolve().parent
    if (here / "svgkit.py").is_file():
        return here
    return None


def ensure_on_path(start: Path | str | None = None) -> Path:
    """Insert the skill ``scripts/`` dir on ``sys.path`` and return it.

    Raises ``FileNotFoundError`` with a fix hint when the skill cannot be found.
    Safe to call more than once.
    """
    scripts = resolve_scripts_dir(start)
    if scripts is None:
        raise FileNotFoundError(
            "could not locate visualize/scripts/svgkit.py from "
            f"{Path(start) if start is not None else Path.cwd()}; "
            "pass the skill root or repo root to ensure_on_path(), or "
            "sys.path.insert(0, '<path-to-visualize>/scripts')"
        )
    s = str(scripts)
    if s not in sys.path:
        sys.path.insert(0, s)
    return scripts


# --------------------------------------------------------------------------- #
# Box — geometry + edge anchors (connect arrows to edges, never centers)
# --------------------------------------------------------------------------- #

@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float
    family: str = "neutral"

    @property
    def cx(self) -> float: return self.x + self.w / 2
    @property
    def cy(self) -> float: return self.y + self.h / 2
    @property
    def top(self) -> Point: return (self.cx, self.y)
    @property
    def bottom(self) -> Point: return (self.cx, self.y + self.h)
    @property
    def left(self) -> Point: return (self.x, self.cy)
    @property
    def right(self) -> Point: return (self.x + self.w, self.cy)


@dataclass
class Lifeline:
    """Actor box at the top plus a vertical dashed lifeline."""

    actor: Box
    x: float
    y0: float
    y1: float

    @property
    def top(self) -> Point: return self.actor.bottom
    @property
    def bottom(self) -> Point: return (self.x, self.y1)


# --------------------------------------------------------------------------- #
# Diagram — the builder
# --------------------------------------------------------------------------- #

class Diagram:
    """Accumulate primitives on z-ordered layers, then ``render()``/``save()``."""

    def __init__(self, width: float, height: float, title: str = "",
                 desc: str = "", fixed_size: bool = False):
        self.width = width
        self.height = height
        self.title = title
        self.desc = desc
        # When True, render() emits the declared (width, height) verbatim and
        # only warns on overflow. When False (default), render() grows the
        # height automatically so content + legend never clip. Escape hatch
        # for layouts the agent has hand-sized.
        self.fixed_size = fixed_size
        self._layers: dict[str, list[str]] = {name: [] for name in _LAYERS}
        # Geometry registry for fit() / connect() — every solid shape returned
        # from a primitive is tracked so the canvas can auto-grow and arrows can
        # pick edge anchors without the caller doing the math.
        self._boxes: list[Box] = []
        self._content_min_x: float = math.inf
        self._content_min_y: float = math.inf
        self._content_max_x: float = -math.inf
        self._content_max_y: float = -math.inf
        self._viewbox_x: float = 0.0
        self._viewbox_y: float = 0.0
        self._has_legend: bool = False

    # -- geometry registry ------------------------------------------------- #

    def _track(self, box: Box) -> Box:
        """Register a solid shape for fit() and return it unchanged."""
        self._boxes.append(box)
        self._note_extent(box.x, box.y, box.w, box.h)
        return box

    def _note_extent(self, x: float, y: float, w: float = 0, h: float = 0) -> None:
        """Expand content bounds for non-Box art (containers, arrows, labels)."""
        vals = (x, y, w, h)
        if not all(math.isfinite(v) for v in vals):
            raise ValueError("diagram coordinates and sizes must be finite")
        x0, x1 = sorted((x, x + w))
        y0, y1 = sorted((y, y + h))
        self._content_min_x = min(self._content_min_x, x0)
        self._content_min_y = min(self._content_min_y, y0)
        self._content_max_x = max(self._content_max_x, x1)
        self._content_max_y = max(self._content_max_y, y1)

    # -- layout helpers ---------------------------------------------------- #

    @staticmethod
    def right_of(box: Box, gap: float = 60) -> float:
        """X coordinate ``gap`` px to the right of ``box`` (for the next node)."""
        return box.x + box.w + gap

    @staticmethod
    def below(box: Box, gap: float = 60) -> float:
        """Y coordinate ``gap`` px below ``box`` (the vertical twin of ``right_of``)."""
        return box.y + box.h + gap

    @staticmethod
    def _spec_size(spec: dict) -> tuple[float, float]:
        """Predict a ``node()`` spec's size without rendering it.

        ``row`` and ``col`` use this to center mixed-height / mixed-width nodes
        while preserving a constant edge-to-edge gap. Keeping the same sizing
        formula as ``node()`` prevents subtle connector zig-zags.
        """
        title = str(spec.get("title", ""))
        sub = spec.get("sub")
        lines = spec.get("lines")
        w = spec.get("w")
        h = spec.get("h")
        if w is None:
            if lines is not None:
                widths = [box_width(title)]
                widths.extend(box_width(str(line), sizes=(12,)) for line in lines)
                w = max(widths)
            else:
                w = box_width(title, sub)
        if h is None:
            h = 22 + 18 * (1 + len(lines)) if lines is not None else (56 if sub else 40)
        return float(w), float(h)

    def row(self, specs: list[dict], x: float = 40, y: float = 40,
            gap: float = 56, align: str = "center") -> list[Box]:
        """Lay node specs left→right with a constant edge-to-edge ``gap``.

        ``align="center"`` (default) aligns vertical centers even when node
        heights differ; ``"start"`` top-aligns them. Returns the boxes for
        edge-anchored connectors.
        """
        if align not in {"center", "start"}:
            raise ValueError("row align must be 'center' or 'start'")
        sizes = [self._spec_size(spec) for spec in specs]
        max_h = max((h for _, h in sizes), default=0.0)
        boxes: list[Box] = []
        if align == "center":
            heights = [self._spec_height(s) for s in specs]
            max_h = max(heights) if heights else 0
            ys = [y + (max_h - h) / 2 for h in heights]
        elif align == "top":
            ys = [y] * len(specs)
        else:
            raise ValueError(f"row() align must be 'center' or 'top', got {align!r}")
        cur_x = x
        for spec, (_, h) in zip(specs, sizes):
            node_y = y + (max_h - h) / 2 if align == "center" else y
            b = self.node(cur_x, node_y, **spec)
            boxes.append(b)
            cur_x = self.right_of(b, gap)
        return boxes

    def col(self, specs: list[dict], x: float = 40, y: float = 40,
            gap: float = 60, align: str = "center") -> list[Box]:
        """Lay node specs top→bottom with a constant edge-to-edge ``gap``.

        ``align="center"`` (default) aligns horizontal centers even when node
        widths differ; ``"start"`` left-aligns them.
        """
        if align not in {"center", "start"}:
            raise ValueError("col align must be 'center' or 'start'")
        sizes = [self._spec_size(spec) for spec in specs]
        max_w = max((w for w, _ in sizes), default=0.0)
        boxes: list[Box] = []
        if align == "center":
            widths = [self._spec_width(s) for s in specs]
            max_w = max(widths) if widths else 0
            xs = [x + (max_w - w) / 2 for w in widths]
        elif align == "left":
            xs = [x] * len(specs)
        else:
            raise ValueError(f"col() align must be 'center' or 'left', got {align!r}")
        cur_y = y
        for spec, (w, _) in zip(specs, sizes):
            node_x = x + (max_w - w) / 2 if align == "center" else x
            b = self.node(node_x, cur_y, **spec)
            boxes.append(b)
            cur_y = self.below(b, gap)
        return boxes

    def chain(self, boxes: list[Box], color: str | None = None,
              labels: list[str | None] | None = None, **kw) -> None:
        """Connect consecutive boxes with ``connect()`` — the one-liner for pipelines.

        ``labels`` is optional and parallel to the *gaps* (len = len(boxes)-1).
        Extra kwargs (``dashed``, ``plate``) pass through to each ``connect``.
        """
        for i in range(len(boxes) - 1):
            lab = None
            if labels and i < len(labels):
                lab = labels[i]
            self.connect(boxes[i], boxes[i + 1], color=color, label=lab, **kw)

    def pipeline(self, specs: list[dict], *, x: float = 40, y: float = 80,
                 gap: float = 56, align: str = "center",
                 labels: list[str | None] | None = None, color: str | None = None,
                 legend: list[tuple[str, str]] | None = None,
                 auto_legend: bool = False, **chain_kw) -> list[Box]:
        """Fast-path linear diagram: ``row`` + ``chain`` (+ optional legend).

        Prefer this over separate ``row``/``chain`` calls for ≤5-node pipelines —
        fewer tokens for the agent, fewer coordinate mistakes. Returns the boxes.

        ``legend`` is an explicit ``[(family, gloss), …]`` list. ``auto_legend=True``
        builds a legend from non-neutral families used on the boxes (see
        ``auto_legend()``). Explicit ``legend`` wins if both are given.
        """
        boxes = self.row(specs, x=x, y=y, gap=gap, align=align)
        self.chain(boxes, color=color, labels=labels, **chain_kw)
        if legend is not None:
            self.legend(legend)
        elif auto_legend:
            self.auto_legend()
        return boxes

    def grid(self, rows: list[list[dict]], *, x: float = 40, y: float = 40,
             gap_x: float = 56, gap_y: float = 60,
             row_align: str = "center") -> list[list[Box]]:
        """Lay a 2-D grid of ``node`` specs; each inner list is one horizontal row.

        Rows are left-aligned at ``x``; columns are *not* equal-width — each cell
        sizes from its own text (use a fixed ``w`` in the spec when you need a
        matrix look). Returns ``list[list[Box]]`` matching the input shape.
        """
        result: list[list[Box]] = []
        cur_y = y
        for specs in rows:
            row_boxes = self.row(specs, x=x, y=cur_y, gap=gap_x, align=row_align)
            result.append(row_boxes)
            if row_boxes:
                cur_y = max(self.below(b, gap_y) for b in row_boxes)
            else:
                cur_y += gap_y
        return result

    def heading(self, text: str, *, x: float = 40, y: float = 36,
                size: int = 16) -> None:
        """Optional canvas heading (15–16px). Place above the first content row.

        Does not reserve layout space automatically — keep content ``y`` below
        the heading (typical: heading at y=36, first row at y=72–80).
        """
        if size < 15 or size > 16:
            size = 16
        self._layers["labels"].append(
            f'  <text x="{snap(x)}" y="{snap(y)}" dominant-baseline="central" '
            f'font-size="{size}" font-weight="500" fill="{CONTAINER_TITLE}">'
            f'{_esc(text)}</text>'
        )
        self._note_extent(x, y - size / 2, text_width(text, size), size)

    def fit(self, margin: float = 40, legend_room: float | None = None) -> "Diagram":
        """Grow the canvas so every tracked shape clears ``margin`` from the edges.

        Call once after placing content (and after ``legend()`` if you use one).
        Prevents the #2 failure mode after text-overflow: boxes clipped by a
        too-small viewBox. Returns ``self`` for chaining (``d.fit().save(...)``).

        ``legend_room`` is only for deliberate extra whitespace. Legends track
        their own bounds, so the default is zero; adding another implicit row
        here used to leave a conspicuous 76px empty footer.
        """
        if not math.isfinite(margin) or margin < 0:
            raise ValueError("fit margin must be finite and non-negative")
        if legend_room is None:
            legend_room = 0.0
        if not math.isfinite(legend_room) or legend_room < 0:
            raise ValueError("legend_room must be finite and non-negative")
        if self._content_max_x == -math.inf:
            return self
        left = min(self._viewbox_x, self._content_min_x - margin)
        top = min(self._viewbox_y, self._content_min_y - margin)
        right = max(self._viewbox_x + self.width, self._content_max_x + margin)
        bottom = max(self._viewbox_y + self.height,
                     self._content_max_y + margin + legend_room)
        self._viewbox_x, self._viewbox_y = left, top
        self.width, self.height = right - left, bottom - top
        return self

    def _marker_for(self, color: str | None) -> str:
        """Resolve ``marker-end``.

        One ``context-stroke`` marker (``url(#arrow)``) serves every color — the
        open chevron recolors itself to match each arrow's stroke.
        """
        return "url(#arrow)"

    @staticmethod
    def _dash_attr(dashed: bool) -> str:
        return ' stroke-dasharray="4 3"' if dashed else ""

    @staticmethod
    def _fill_opacity_attr(opacity: float | None) -> str:
        if opacity is None:
            return ""
        if not 0 <= opacity <= 1:
            raise ValueError("opacity must be between 0 and 1")
        # Fade only the fill. A group-level `opacity` also fades the hairline
        # stroke, defeating the crisp tint-within-family treatment.
        return f' fill-opacity="{opacity:g}"'

    # -- nodes ------------------------------------------------------------- #

    def node(self, x: float, y: float, title: str, sub: str | None = None,
             family: str = "neutral", w: float | None = None,
             h: float | None = None, lines: list[str] | None = None,
             opacity: float | None = None) -> Box:
        """A rounded box, sized from its text unless ``w`` is given.

        Two lines (title + sub) default to height 56; one line to 40. Pass
        ``lines`` (extra 12/SUB rows beneath the title) for a multi-line card —
        ``sub`` and ``lines`` are mutually exclusive. With ``lines`` the height
        is ``22 + 18 * (1 + len(lines))`` (a 22px title band plus 18px per row).

        ``opacity`` (0–1) tints the fill for sibling stages of one family — the
        editorial "tint-within-family" technique from ``references/style.md``.
        """
        if sub is not None and lines is not None:
            raise ValueError("node() accepts `sub` (one line) or `lines` (many), not both")
        fam = _family(family)
        if lines is not None:
            if w is None:
                cand = [box_width(title)]
                cand.extend(box_width(l, sizes=(12,)) for l in lines)
                w = max(cand)
            if h is None:
                h = 22 + 18 * (1 + len(lines))
        else:
            if w is None:
                w = box_width(title, sub)
            if h is None:
                h = 56 if sub else 40
        cx = x + w / 2
        op = self._fill_opacity_attr(opacity)
        self._layers["boxes"].append(
            f'  <rect x="{snap(x)}" y="{snap(y)}" width="{snap(w)}" height="{snap(h)}" rx="8" '
            f'fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"{op}/>'
        )
        if lines is not None:
            # Title band 0 at y+21, each extra line 18px below.
            self._layers["box_text"].append(
                f'  <text x="{snap(cx)}" y="{snap(y + 21)}" text-anchor="middle" '
                f'dominant-baseline="central" font-size="14" font-weight="500" '
                f'fill="{fam["title"]}">{_esc(title)}</text>'
            )
            for i, line in enumerate(lines, start=1):
                self._layers["box_text"].append(
                    f'  <text x="{snap(cx)}" y="{snap(y + 21 + i * 18)}" text-anchor="middle" '
                    f'dominant-baseline="central" font-size="12" '
                    f'fill="{fam["sub"]}">{_esc(line)}</text>'
                )
        elif sub:
            ty = y + h / 2
            self._layers["box_text"].append(
                f'  <text x="{snap(cx)}" y="{snap(ty - 8)}" text-anchor="middle" '
                f'dominant-baseline="central" font-size="14" font-weight="500" '
                f'fill="{fam["title"]}">{_esc(title)}</text>'
            )
            self._layers["box_text"].append(
                f'  <text x="{snap(cx)}" y="{snap(ty + 9)}" text-anchor="middle" '
                f'dominant-baseline="central" font-size="12" '
                f'fill="{fam["sub"]}">{_esc(sub)}</text>'
            )
        else:
            self._layers["box_text"].append(
                f'  <text x="{snap(cx)}" y="{snap(y + h / 2)}" text-anchor="middle" '
                f'dominant-baseline="central" font-size="14" font-weight="500" '
                f'fill="{fam["title"]}">{_esc(title)}</text>'
            )
        return self._track(Box(x, y, w, h, family))

    def state(self, x: float, y: float, title: str, sub: str | None = None,
              family: str = "neutral", w: float | None = None,
              h: float | None = None, lines: list[str] | None = None,
              opacity: float | None = None) -> Box:
        """A UML state node; geometrically identical to ``node()`` (semantic alias)."""
        return self.node(x, y, title, sub, family=family, w=w, h=h, lines=lines,
                         opacity=opacity)

    def diamond(self, x: float, y: float, title: str, family: str = "amber",
                hw: float | None = None, hh: float = 40) -> Box:
        """Decision diamond. ``hw`` = half-width, ``hh`` = half-height; ``(x, y)`` is
        the top-left of the bounding box (so the diamond is centred at
        ``(x + hw, y + hh)`` and spans ``2*hw`` × ``2*hh``). If ``hw`` is None it
        is sized from ``title``.
        """
        fam = _family(family)
        if hw is None:
            hw = max(text_width(title, 14) / 2 + 16, 50)
        cx, cy = x + hw, y + hh
        w, h = hw * 2, hh * 2
        pts = f"{snap(cx)},{snap(cy - hh)} {snap(cx + hw)},{snap(cy)} " \
              f"{snap(cx)},{snap(cy + hh)} {snap(cx - hw)},{snap(cy)}"
        self._layers["boxes"].append(
            f'  <polygon points="{pts}" fill="{fam["fill"]}" stroke="{fam["stroke"]}" '
            f'stroke-width="0.5"/>'
        )
        self._layers["box_text"].append(
            f'  <text x="{snap(cx)}" y="{snap(cy)}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="14" font-weight="500" '
            f'fill="{fam["title"]}">{_esc(title)}</text>'
        )
        return self._track(Box(x, y, w, h, family))

    def usecase(self, x: float, y: float, label: str,
                family: str = "neutral", w: float | None = None,
                h: float = 60) -> Box:
        """UML use-case ellipse (min 140x60) with a centred label.

        ``x, y`` is the top-left of the bounding box. Width auto-sizes from the
        label (min 140); height defaults to 60. An ellipse this size IS a
        collision obstacle, so route ``<<include>>`` / ``<<extend>>`` arrows with
        ``lpath()`` around neighbouring ellipses.
        """
        fam = _family(family)
        if w is None:
            w = max(box_width(label), 140)
        rx, ry = w / 2, h / 2
        cx, cy = x + rx, y + ry
        self._layers["boxes"].append(
            f'  <ellipse cx="{snap(cx)}" cy="{snap(cy)}" rx="{snap(rx)}" ry="{snap(ry)}" '
            f'fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
        )
        self._layers["box_text"].append(
            f'  <text x="{snap(cx)}" y="{snap(cy)}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="14" font-weight="500" '
            f'fill="{fam["title"]}">{_esc(label)}</text>'
        )
        return self._track(Box(x, y, w, h, family))

    def actor(self, cx: float, y: float, label: str,
              family: str = "neutral") -> Box:
        """A UML stick-figure actor (use-case diagrams).

        ``cx, y`` is the head top; the figure is centred on ``cx``. Renders a
        ``<g>`` of head circle + body/arms/legs in the family LINE color, with a
        14px label below. Returns a ``Box`` (anchor only — no rect is drawn) so
        association arrows can anchor on the actor's left/right edges at hand
        height. The whole figure is a ``<g>`` of primitives, which the validator
        does not treat as a collision obstacle (its obstacle scan covers
        rect/circle/ellipse/polygon, not groups), so arrows may cross it; keep
        actors outside the system boundary regardless so association arrows
        never need to cross the body. The returned ``Box`` is a rough anchor
        envelope — the label text sits below it (to ~y+74).
        """
        fam = _family(family)
        head_r = 8
        body_top = y + head_r * 2
        body_bot = body_top + 24
        arm_y = body_top + 6
        leg_bot = body_bot + 14
        self._layers["boxes"].append(
            f'  <g stroke="{fam["line"]}" stroke-width="1.5" fill="none" '
            f'stroke-linecap="round">\n'
            f'    <circle cx="{snap(cx)}" cy="{snap(y + head_r)}" r="{head_r}" '
            f'fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>\n'
            f'    <line x1="{snap(cx)}" y1="{snap(body_top)}" x2="{snap(cx)}" y2="{snap(body_bot)}"/>\n'
            f'    <line x1="{snap(cx - 11)}" y1="{snap(arm_y)}" x2="{snap(cx + 11)}" y2="{snap(arm_y)}"/>\n'
            f'    <line x1="{snap(cx)}" y1="{snap(body_bot)}" x2="{snap(cx - 8)}" y2="{snap(leg_bot)}"/>\n'
            f'    <line x1="{snap(cx)}" y1="{snap(body_bot)}" x2="{snap(cx + 8)}" y2="{snap(leg_bot)}"/>\n'
            f'  </g>'
        )
        self._layers["box_text"].append(
            f'  <text x="{snap(cx)}" y="{snap(leg_bot + 14)}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="14" font-weight="500" '
            f'fill="{fam["title"]}">{_esc(label)}</text>'
        )
        # Track extent for fit() but actors are not collision obstacles; still
        # register so the canvas grows to cover the stick figure + label.
        box = Box(cx - 20, y, 40, leg_bot + 20 - y, family)
        self._note_extent(box.x, box.y, box.w, box.h)
        return box

    def cylinder(self, x: float, y: float, title: str, sub: str | None = None,
                 family: str = "green", w: float | None = None, h: float = 54) -> Box:
        """Datastore cylinder. ``(x, y)`` is the top-left of the body; cap ry = min(w/6, 9) (flat cap)."""
        fam = _family(family)
        if w is None:
            w = box_width(title, sub)
        # Flat cap (ry capped at 9) — matches the house-style cylinder in the
        # cookbook/shape-vocabulary and the gallery art. Uncapped w/6 makes the
        # cap ellipse taller than the body for normal box widths.
        rx, ry = w / 2, min(w / 6, 9.0)
        cx = x + rx
        top = y + ry
        body_h = h
        self._layers["boxes"].append(
            f'  <path d="M {snap(x)} {snap(top)} A {snap(rx)} {snap(ry)} 0 0 1 {snap(x + w)} '
            f'{snap(top)} L {snap(x + w)} {snap(top + body_h)} A {snap(rx)} {snap(ry)} 0 0 1 '
            f'{snap(x)} {snap(top + body_h)} Z" fill="{fam["fill"]}" stroke="{fam["stroke"]}" '
            f'stroke-width="0.5"/>'
        )
        self._layers["boxes"].append(
            f'  <ellipse cx="{snap(cx)}" cy="{snap(top)}" rx="{snap(rx)}" ry="{snap(ry)}" '
            f'fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
        )
        total_h = body_h + ry * 2
        cy = top + body_h / 2
        if sub:
            self._layers["box_text"].append(
                f'  <text x="{snap(cx)}" y="{snap(cy - 8)}" text-anchor="middle" '
                f'dominant-baseline="central" font-size="14" font-weight="500" '
                f'fill="{fam["title"]}">{_esc(title)}</text>'
            )
            self._layers["box_text"].append(
                f'  <text x="{snap(cx)}" y="{snap(cy + 9)}" text-anchor="middle" '
                f'dominant-baseline="central" font-size="12" '
                f'fill="{fam["sub"]}">{_esc(sub)}</text>'
            )
        else:
            self._layers["box_text"].append(
                f'  <text x="{snap(cx)}" y="{snap(cy)}" text-anchor="middle" '
                f'dominant-baseline="central" font-size="14" font-weight="500" '
                f'fill="{fam["title"]}">{_esc(title)}</text>'
            )
        return self._track(Box(x, y, w, total_h, family))

    def lifeline(self, x: float, label: str, y0: float, y1: float,
                 family: str = "neutral", w: float | None = None) -> Lifeline:
        """Sequence-diagram actor (one-line box) plus dashed vertical lifeline."""
        actor = self.node(x, y0, label, family=family, w=w, h=40)
        cx = actor.cx
        self._layers["containers"].append(
            f'  <line x1="{snap(cx)}" y1="{snap(actor.bottom[1])}" x2="{snap(cx)}" '
            f'y2="{snap(y1)}" stroke="rgba(31,30,29,0.3)" stroke-width="0.5" '
            f'stroke-dasharray="4 3"/>'
        )
        self._note_extent(x, y0, actor.w, y1 - y0)
        return Lifeline(actor=actor, x=cx, y0=y0, y1=y1)

    def point(self, x: float, y: float, label: str | None = None,
              family: str = "neutral", r: int = 5) -> Point:
        """A small filled circle marker (with optional label) — scatter / concept-map dot.

        Replaces the cookbook §7 hand-written snippet for embedding-space
        points and concept-map leaves: one ``<circle r={r}>`` in the family
        fill, plus an optional 12/CAPTION label offset to the upper-right.
        The point itself sits on the ``boxes`` layer (it's a visual
        artifact, not an obstacle) and the label on ``labels`` (drawn on
        top, immune to being buried under later color blocks).

        Returns the centre ``Point`` so callers can chain ``d.arrow()``
        to it. Use ``r=8`` for milestone dots, ``r=3`` for dense scatter.

        Not registered as a collision obstacle — ``r`` ≤ 8 is far below the
        validator's 30px floor and arrows are expected to point AT the
        point (leader lines), not flow around it.
        """
        fam = FAMILIES[family]
        self._layers["boxes"].append(
            f'  <circle cx="{snap(x)}" cy="{snap(y)}" r="{r}" '
            f'fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
        )
        if label:
            self._layers["labels"].append(
                f'  <text x="{snap(x + r + 8)}" y="{snap(y - 4)}" font-size="12" '
                f'fill="{CAPTION}">{_esc(label)}</text>'
            )
        self._track_extent(x - r, y - r, x + r, y + r)
        if label:
            tw = text_width(label, 12)
            self._track_extent(x + r + 8, y - 4 - 6, x + r + 8 + tw, y - 4 + 6)
        return (x, y)

    def state_dot(self, x: float, y: float, kind: str = "initial") -> Point:
        """UML initial (filled) or final (double circle) pseudo-state."""
        if kind == "initial":
            self._layers["boxes"].append(
                f'  <circle cx="{snap(x)}" cy="{snap(y)}" r="8" fill="#141413"/>'
            )
            self._note_extent(x - 8, y - 8, 16, 16)
        elif kind == "final":
            self._layers["boxes"].append(
                f'  <circle cx="{snap(x)}" cy="{snap(y)}" r="12" fill="none" '
                f'stroke="#141413" stroke-width="1.5"/>'
            )
            self._layers["boxes"].append(
                f'  <circle cx="{snap(x)}" cy="{snap(y)}" r="8" fill="#141413"/>'
            )
            self._note_extent(x - 12, y - 12, 24, 24)
        else:
            raise ValueError(f"state_dot kind must be 'initial' or 'final', got {kind!r}")
        return (x, y)

    def entity(self, x: float, y: float, name: str, attrs: list[str],
               family: str = "neutral", w: float | None = None) -> Box:
        """ER entity: header band + attribute lines."""
        fam = _family(family)
        header_h = 28
        line_h = 18
        if w is None:
            w = max(box_width(name), max((box_width(a, sizes=(12,)) for a in attrs), default=120))
        h = header_h + len(attrs) * line_h + 8
        self._layers["boxes"].append(
            f'  <rect x="{snap(x)}" y="{snap(y)}" width="{snap(w)}" height="{snap(h)}" rx="8" '
            f'fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
        )
        self._layers["boxes"].append(
            f'  <line x1="{snap(x)}" y1="{snap(y + header_h)}" x2="{snap(x + w)}" '
            f'y2="{snap(y + header_h)}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
        )
        cx = x + w / 2
        self._layers["box_text"].append(
            f'  <text x="{snap(cx)}" y="{snap(y + header_h / 2)}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="14" font-weight="500" '
            f'fill="{fam["title"]}">{_esc(name)}</text>'
        )
        for i, attr in enumerate(attrs):
            self._layers["box_text"].append(
                f'  <text x="{snap(x + 12)}" y="{snap(y + header_h + 14 + i * line_h)}" '
                f'dominant-baseline="central" font-size="12" '
                f'fill="{fam["sub"]}">{_esc(attr)}</text>'
            )
        return self._track(Box(x, y, w, h, family))

    def class_box(self, x: float, y: float, name: str,
                  attrs: list[str] | None = None,
                  methods: list[str] | None = None,
                  family: str = "neutral",
                  abstract: bool = False,
                  stereotype: str | None = None,
                  w: float | None = None) -> Box:
        """UML three-compartment class box: name / attributes / methods.

        The house-style sibling of ``entity()`` (which is two-compartment): a
        name band (optionally topped by a ``<<stereotype>>`` line), then an
        attributes compartment, then a methods compartment, split by hairline
        dividers. Min width 160 (per ``references/diagram-types.md``). With
        ``abstract=True`` the name italicises; ``stereotype`` (e.g. ``"interface"``)
        renders as ``<<interface>>`` above it. Visibility markers (``+`` / ``-`` /
        ``#``) belong in the attr/method strings the caller passes.
        """
        fam = _family(family)
        attrs = attrs or []
        methods = methods or []
        name_h = 30 + (10 if stereotype else 0)
        attr_h = len(attrs) * 18 + 8 if attrs else 0
        meth_h = len(methods) * 18 + 8 if methods else 0
        h = name_h + attr_h + meth_h
        if w is None:
            cand = [box_width(name), 160]
            if stereotype:
                cand.append(box_width(f"<<{stereotype}>>", sizes=(12,)))
            cand.extend(box_width(a, sizes=(12,)) for a in attrs)
            cand.extend(box_width(m, sizes=(12,)) for m in methods)
            w = max(cand)
        self._layers["boxes"].append(
            f'  <rect x="{snap(x)}" y="{snap(y)}" width="{snap(w)}" height="{snap(h)}" rx="8" '
            f'fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
        )
        has_attrs = bool(attrs)
        has_methods = bool(methods)
        if has_attrs or has_methods:
            self._layers["boxes"].append(
                f'  <line x1="{snap(x)}" y1="{snap(y + name_h)}" x2="{snap(x + w)}" '
                f'y2="{snap(y + name_h)}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
            )
        if has_attrs and has_methods:
            self._layers["boxes"].append(
                f'  <line x1="{snap(x)}" y1="{snap(y + name_h + attr_h)}" x2="{snap(x + w)}" '
                f'y2="{snap(y + name_h + attr_h)}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
            )
        italic = ' font-style="italic"' if abstract else ''
        cx = x + w / 2
        if stereotype:
            self._layers["box_text"].append(
                f'  <text x="{snap(cx)}" y="{snap(y + 12)}" text-anchor="middle" '
                f'dominant-baseline="central" font-size="12" '
                f'fill="{fam["sub"]}">{_esc(f"<<{stereotype}>>")}</text>'
            )
            self._layers["box_text"].append(
                f'  <text x="{snap(cx)}" y="{snap(y + 25)}" text-anchor="middle" '
                f'dominant-baseline="central" font-size="14" font-weight="500"{italic} '
                f'fill="{fam["title"]}">{_esc(name)}</text>'
            )
        else:
            self._layers["box_text"].append(
                f'  <text x="{snap(cx)}" y="{snap(y + name_h / 2)}" text-anchor="middle" '
                f'dominant-baseline="central" font-size="14" font-weight="500"{italic} '
                f'fill="{fam["title"]}">{_esc(name)}</text>'
            )
        attr_y0 = y + name_h
        for i, attr in enumerate(attrs):
            self._layers["box_text"].append(
                f'  <text x="{snap(x + 12)}" y="{snap(attr_y0 + 14 + i * 18)}" '
                f'dominant-baseline="central" font-size="12" '
                f'fill="{fam["sub"]}">{_esc(attr)}</text>'
            )
        meth_y0 = y + name_h + attr_h
        for i, meth in enumerate(methods):
            self._layers["box_text"].append(
                f'  <text x="{snap(x + 12)}" y="{snap(meth_y0 + 14 + i * 18)}" '
                f'dominant-baseline="central" font-size="12" '
                f'fill="{fam["sub"]}">{_esc(meth)}</text>'
            )
        return self._track(Box(x, y, w, h, family))

    def step(self, x: float, y: float, n: int, title: str,
             sub: str | None = None, family: str = "neutral",
             w: float | None = None, h: float | None = None) -> Box:
        """A numbered step card — circled badge + title (+ optional sub).

        Reads as one item in a recipe / pipeline / permission ladder. The badge
        is a neutral disc so it stands out on every family fill; the number takes
        the family TITLE color. Width grows from the text (44px badge area +
        16px right pad, min 150), so labels never clip. Height 56 with sub, 44 without.
        """
        fam = _family(family)
        if h is None:
            h = 56 if sub else 44
        if w is None:
            content = max(text_width(title, 14),
                          text_width(sub, 12) if sub else 0)
            w = max(int(math.ceil((content + 60) / 4) * 4), 150)  # 44 badge + 16 pad
        self._layers["boxes"].append(
            f'  <rect x="{snap(x)}" y="{snap(y)}" width="{snap(w)}" height="{snap(h)}" rx="8" '
            f'fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
        )
        bx, by = x + 22, y + h / 2
        self._layers["boxes"].append(
            f'  <circle cx="{snap(bx)}" cy="{snap(by)}" r="11" fill="#F1EFE8" '
            f'stroke="{fam["stroke"]}" stroke-width="0.5"/>'
        )
        self._layers["box_text"].append(
            f'  <text x="{snap(bx)}" y="{snap(by)}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="14" font-weight="500" '
            f'fill="{fam["title"]}">{_esc(str(n))}</text>'
        )
        tx = x + 44
        if sub:
            self._layers["box_text"].append(
                f'  <text x="{snap(tx)}" y="{snap(y + h / 2 - 8)}" dominant-baseline="central" '
                f'font-size="14" font-weight="500" fill="{fam["title"]}">{_esc(title)}</text>'
            )
            self._layers["box_text"].append(
                f'  <text x="{snap(tx)}" y="{snap(y + h / 2 + 9)}" dominant-baseline="central" '
                f'font-size="12" fill="{fam["sub"]}">{_esc(sub)}</text>'
            )
        else:
            self._layers["box_text"].append(
                f'  <text x="{snap(tx)}" y="{snap(y + h / 2)}" dominant-baseline="central" '
                f'font-size="14" font-weight="500" fill="{fam["title"]}">{_esc(title)}</text>'
            )
        return self._track(Box(x, y, w, h, family))

    def bar(self, x: float, y: float, w: float, label: str,
            family: str = "neutral", h: float = 28) -> Box:
        """A Gantt / timeline bar — a rounded rect with the label inside.

        Unlike ``node()`` the width is a caller-supplied datum (a bar spans a
        time range), not measured from the label. Height defaults to 28, under
        the validator's 30px obstacle floor, so a bar is NOT a collision
        obstacle — milestone leaders and adjacent bars route freely. Keep
        ``w >= text_width(label, 12) + 16`` or the label clips (surfaced by the
        validator's text-fit check as a deliberate contract).
        """
        fam = _family(family)
        self._layers["boxes"].append(
            f'  <rect x="{snap(x)}" y="{snap(y)}" width="{snap(w)}" height="{snap(h)}" rx="6" '
            f'fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
        )
        self._layers["box_text"].append(
            f'  <text x="{snap(x + w / 2)}" y="{snap(y + h / 2)}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="12" '
            f'fill="{fam["sub"]}">{_esc(label)}</text>'
        )
        # Bars are not collision obstacles (h default 28), but still extend canvas.
        self._note_extent(x, y, w, h)
        return Box(x, y, w, h, family)

    def panel(self, x: float, y: float, w: float, h: float, title: str,
              subtitle: str | None = None, family: str = "neutral") -> Box:
        """A titled card with a colored header band (the "Step 1 / Result" window).

        Body is white so you can drop nodes / mono rows / .raw() art onto it; the
        header band carries the family color + the title (and an optional muted
        subtitle on the same row). The band is drawn as two stacked rects (a
        rounded one + a square one) so it reads flat against the body. Band
        height 26 is under the validator's 30px obstacle floor, so arrows still
        treat the whole panel as a single collision box.
        """
        fam = _family(family)
        band_h = 26
        self._layers["boxes"].append(
            f'  <rect x="{snap(x)}" y="{snap(y)}" width="{snap(w)}" height="{snap(h)}" rx="8" '
            f'fill="{BG}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
        )
        self._layers["boxes"].append(
            f'  <rect x="{snap(x)}" y="{snap(y)}" width="{snap(w)}" height="{band_h}" rx="8" '
            f'fill="{fam["fill"]}"/>'
        )
        self._layers["boxes"].append(
            f'  <rect x="{snap(x)}" y="{snap(y + band_h - 14)}" width="{snap(w)}" '
            f'height="14" fill="{fam["fill"]}"/>'
        )
        cy = y + band_h / 2
        self._layers["box_text"].append(
            f'  <text x="{snap(x + 16)}" y="{snap(cy)}" dominant-baseline="central" '
            f'font-size="14" font-weight="500" fill="{fam["title"]}">{_esc(title)}</text>'
        )
        if subtitle:
            tw = text_width(title, 14)
            self._layers["box_text"].append(
                f'  <text x="{snap(x + 16 + tw + 12)}" y="{snap(cy)}" dominant-baseline="central" '
                f'font-size="12" fill="{fam["sub"]}">{_esc(subtitle)}</text>'
            )
        return self._track(Box(x, y, w, h, family))

    # -- arrows ------------------------------------------------------------ #

    def arrow(self, a: Point, b: Point, color: str | None = None,
              label: str | None = None, plate: bool = False,
              dashed: bool = False, bidirectional: bool = False) -> None:
        """A straight connector ``a -> b``. ``color`` is a family name or hex.

        ``dashed=True`` draws async / optional / dependency edges
        (``stroke-dasharray="4 3"``). ``bidirectional=True`` puts the open
        chevron on both ends (bind mounts, duplex links).
        """
        stroke = _resolve_line(color)
        start = f' marker-start="{self._marker_for(color)}"' if bidirectional else ""
        self._layers["arrows"].append(
            f'  <line x1="{snap(a[0])}" y1="{snap(a[1])}" x2="{snap(b[0])}" y2="{snap(b[1])}" '
            f'stroke="{stroke}" stroke-width="1.5" stroke-linecap="round"'
            f'{self._dash_attr(dashed)}{start} '
            f'marker-end="{self._marker_for(color)}"/>'
        )
        self._note_extent(min(a[0], b[0]) - 4, min(a[1], b[1]) - 4,
                          abs(b[0] - a[0]) + 8, abs(b[1] - a[1]) + 8)
        if label:
            self._place_label(a, b, label, plate)
        self._track_extent(a[0], a[1], b[0], b[1])

    def lpath(self, points: list[Point], color: str | None = None,
              label: str | None = None, plate: bool = False,
              dashed: bool = False, bidirectional: bool = False) -> None:
        """An orthogonal multi-segment route; the arriving end carries the marker."""
        if len(points) < 2:
            raise ValueError("lpath needs at least two points")
        stroke = _resolve_line(color)
        d = "M" + " L".join(f"{snap(px)} {snap(py)}" for px, py in points)
        start = f' marker-start="{self._marker_for(color)}"' if bidirectional else ""
        self._layers["arrows"].append(
            f'  <path d="{d}" fill="none" stroke="{stroke}" stroke-width="1.5" '
            f'stroke-linecap="round"{self._dash_attr(dashed)}{start} '
            f'marker-end="{self._marker_for(color)}"/>'
        )
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        self._note_extent(min(xs) - 4, min(ys) - 4,
                          max(xs) - min(xs) + 8, max(ys) - min(ys) + 8)
        if label:
            segs = [(points[i], points[i + 1]) for i in range(len(points) - 1)]
            longest = max(segs, key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
            self._place_label(longest[0], longest[1], label, plate)

    def _warn_unrouteable(self, a: Point, b: Point) -> None:
        """Print a one-line warning naming the segment and the obstacles hit."""
        hit = [obs for obs in self._obstacles
               if self._segment_intersects_rect(a, b, obs)]
        names = [f"[{obs.x:g},{obs.y:g}-{obs.x + obs.w:g},{obs.y + obs.h:g}]"
                 for obs in hit[:2]]
        more = "..." if len(hit) > 2 else ""
        print(
            f"svgkit: arrow ({a[0]:g},{a[1]:g})→({b[0]:g},{b[1]:g}) "
            f"can't avoid {', '.join(names)}{more}; emitting straight line. "
            f"Re-layout or pass route='straight' to suppress this warning."
        )

    def lpath(self, points: list[Point], color: str | None = None,
              label: str | None = None, plate: bool = False,
              dashed: bool = False) -> None:
        """An orthogonal multi-segment route; only the arriving end carries the marker.

        User-driven geometry — ``lpath()`` does NOT consult the obstacle
        registry (the agent already specified the route). Use this when you
        want full manual control over the path; use ``arrow()`` for automatic
        obstacle avoidance.
        """
        if len(points) < 2:
            raise ValueError("lpath needs at least two points")
        self._emit_arrow_path(points, color=color, label=label, plate=plate, dashed=dashed)
        for p, q in zip(points[:-1], points[1:]):
            self._track_extent(p[0], p[1], q[0], q[1])

    def curve(self, a: Point, b: Point, color: str | None = None,
              label: str | None = None, marker: bool = True,
              dashed: bool = False) -> None:
        """A cubic bezier from ``a`` to ``b`` — mind-map / concept-map branches.

        Control points push the curve out horizontally from each end (half the
        horizontal run), so a branch leaving the right of a central node starts
        flat and arrives flat. Vertical branches look best when ``a`` sits above
        or beside ``b``; for a pure vertical drop prefer ``arrow``. Pass
        ``marker=False`` for undirected concept-map branches (no chevron).
        """
        stroke = _resolve_line(color)
        dx = (b[0] - a[0]) * 0.5
        c1 = (a[0] + dx, a[1])
        c2 = (b[0] - dx, b[1])
        d = (f"M {snap(a[0])} {snap(a[1])} C {snap(c1[0])} {snap(c1[1])} "
             f"{snap(c2[0])} {snap(c2[1])} {snap(b[0])} {snap(b[1])}")
        end = f' marker-end="{self._marker_for(color)}"' if marker else ""
        self._layers["arrows"].append(
            f'  <path d="{d}" fill="none" stroke="{stroke}" stroke-width="1.5" '
            f'stroke-linecap="round"{self._dash_attr(dashed)}{end}/>'
        )
        xs = [a[0], b[0], c1[0], c2[0]]
        ys = [a[1], b[1], c1[1], c2[1]]
        self._note_extent(min(xs) - 4, min(ys) - 4,
                          max(xs) - min(xs) + 8, max(ys) - min(ys) + 8)
        if label:
            self._place_label(a, b, label, plate=False)
        self._track_extent(a[0], a[1], b[0], b[1])

    def connect(self, src: Box, dst: Box, color: str | None = None,
                label: str | None = None, plate: bool = False,
                dashed: bool = False, route: str = "auto",
                bidirectional: bool = False) -> None:
        """Box-to-box connector that picks edge anchors and routing for you.

        Prefer this over raw ``arrow``/``lpath`` for ordinary graphs — it is the
        single biggest quality win: edges always land on mid-sides, never centers,
        and diagonals become orthogonal L-paths that do not cut through boxes.

        ``route``:
          * ``"auto"`` (default) — straight when boxes share a row/column
            (within 12px of aligned centers); otherwise an L-path through the gap.
          * ``"straight"`` — always a single segment between the facing edges.
          * ``"ortho"`` — always an L/Z orthogonal path (even when aligned).
        """
        if src is dst:
            self.self_loop(src, color=color, label=label, plate=plate,
                           dashed=dashed, bidirectional=bidirectional)
            return
        overlap_x = min(src.x + src.w, dst.x + dst.w) - max(src.x, dst.x)
        overlap_y = min(src.y + src.h, dst.y + dst.h) - max(src.y, dst.y)
        if overlap_x > 0 and overlap_y > 0:
            raise ValueError("connect() boxes overlap; reposition them or route from explicit points")

        if route not in {"auto", "straight", "ortho"}:
            raise ValueError("connect route must be 'auto', 'straight', or 'ortho'")
        dx = dst.cx - src.cx
        dy = dst.cy - src.cy
        aligned_h = abs(dy) <= 12
        aligned_v = abs(dx) <= 12

        if route == "straight" or (route == "auto" and (aligned_h or aligned_v)):
            if abs(dx) >= abs(dy):
                a, b = (src.right, dst.left) if dx >= 0 else (src.left, dst.right)
            else:
                a, b = (src.bottom, dst.top) if dy >= 0 else (src.top, dst.bottom)
            self.arrow(a, b, color=color, label=label, plate=plate,
                       dashed=dashed, bidirectional=bidirectional)
            return

        # Orthogonal: prefer the axis with more free gap so the bend sits in
        # whitespace rather than inside either box.
        gap_x = max(0.0, abs(dx) - (src.w + dst.w) / 2)
        gap_y = max(0.0, abs(dy) - (src.h + dst.h) / 2)

        if gap_x >= gap_y:
            # Horizontal-first: exit side, bend at mid-x, enter side.
            if dx >= 0:
                a, exit_y = src.right, src.cy
                b, enter_y = dst.left, dst.cy
                mid_x = (src.x + src.w + dst.x) / 2
            else:
                a, exit_y = src.left, src.cy
                b, enter_y = dst.right, dst.cy
                mid_x = (dst.x + dst.w + src.x) / 2
            # If the mid-x would sit inside a box (overlapping columns), fall
            # back to vertical-first via a side gutter.
            if src.x < mid_x < src.x + src.w or dst.x < mid_x < dst.x + dst.w:
                gutter = max(src.x + src.w, dst.x + dst.w) + 28
                self.lpath([a, (gutter, exit_y), (gutter, enter_y), b],
                           color=color, label=label, plate=plate, dashed=dashed,
                           bidirectional=bidirectional)
            else:
                self.lpath([a, (mid_x, exit_y), (mid_x, enter_y), b],
                           color=color, label=label, plate=plate, dashed=dashed,
                           bidirectional=bidirectional)
        else:
            # Vertical-first: exit top/bottom, bend at mid-y, enter top/bottom.
            if dy >= 0:
                a, exit_x = src.bottom, src.cx
                b, enter_x = dst.top, dst.cx
                mid_y = (src.y + src.h + dst.y) / 2
            else:
                a, exit_x = src.top, src.cx
                b, enter_x = dst.bottom, dst.cx
                mid_y = (dst.y + dst.h + src.y) / 2
            if src.y < mid_y < src.y + src.h or dst.y < mid_y < dst.y + dst.h:
                gutter = max(src.y + src.h, dst.y + dst.h) + 28
                self.lpath([a, (exit_x, gutter), (enter_x, gutter), b],
                           color=color, label=label, plate=plate, dashed=dashed,
                           bidirectional=bidirectional)
            else:
                self.lpath([a, (exit_x, mid_y), (enter_x, mid_y), b],
                           color=color, label=label, plate=plate, dashed=dashed,
                           bidirectional=bidirectional)

    def self_loop(self, box: Box, color: str | None = None,
                  label: str | None = None, plate: bool = False,
                  dashed: bool = False, bidirectional: bool = False,
                  gutter: float = 32) -> None:
        """Draw a compact right-gutter loop from a box back to itself.

        This is the safe spelling for retry / reasoning loops. ``connect(b, b)``
        delegates here instead of drawing a misleading arrow through the box.
        """
        if not all(math.isfinite(v) for v in (box.x, box.y, box.w, box.h, gutter)):
            raise ValueError("self-loop geometry must be finite")
        if box.w <= 0 or box.h <= 0:
            raise ValueError("self-loop box must have positive width and height")
        if gutter < 16:
            raise ValueError("self-loop gutter must be at least 16")
        spread = min(10.0, max(1.0, box.h / 5), box.h / 2)
        a = (box.x + box.w, box.cy + spread)
        b = (box.x + box.w, box.cy - spread)
        gx = box.x + box.w + gutter
        self.lpath([a, (gx, a[1]), (gx, b[1]), b], color=color,
                   label=label, plate=plate, dashed=dashed,
                   bidirectional=bidirectional)

    def fanout(self, parent: Box, children: list[Box], color: str | None = None,
               labels: list[str | None] | None = None,
               gutter: float = 24, dashed: bool = False) -> None:
        """Split one parent into several children with orthogonal branches.

        Drops a short marker-free stem out of the parent's facing side, then
        fans L-paths (with chevrons) to each child's facing edge. Children
        should sit on the same side of the parent (below, above, right, or
        left) — the side is inferred from the first child's position.
        """
        if not children:
            return
        stroke = _resolve_line(color)
        dash = self._dash_attr(dashed)
        # Prefer vertical when every child is clearly above/below the parent
        # band — otherwise a left-most first child makes abs(dx) dominate and the
        # bus is drawn *through* mid-row siblings (architecture fan-out bug).
        below = all(c.y >= parent.y + parent.h - 4 for c in children)
        above = all(c.y + c.h <= parent.y + 4 for c in children)
        c0 = children[0]
        dx, dy = c0.cx - parent.cx, c0.cy - parent.cy
        vertical = below or above or abs(dy) > abs(dx)
        if not vertical:
            # Horizontal fan (children to the right or left).
            going_right = dx >= 0
            stem = parent.right if going_right else parent.left
            bus_x = (parent.x + parent.w + gutter) if going_right else (parent.x - gutter)
            # Stem to the bus has no marker — only arriving branches do.
            self._layers["arrows"].append(
                f'  <line x1="{snap(stem[0])}" y1="{snap(stem[1])}" '
                f'x2="{snap(bus_x)}" y2="{snap(parent.cy)}" '
                f'stroke="{stroke}" stroke-width="1.5" stroke-linecap="round"{dash}/>'
            )
            for i, child in enumerate(children):
                lab = labels[i] if labels and i < len(labels) else None
                target = child.left if going_right else child.right
                self.lpath([(bus_x, parent.cy), (bus_x, child.cy), target],
                           color=color, label=lab, dashed=dashed)
        else:
            # Vertical fan (children below or above).
            going_down = below or (not above and dy >= 0)
            stem = parent.bottom if going_down else parent.top
            bus_y = (parent.y + parent.h + gutter) if going_down else (parent.y - gutter)
            self._layers["arrows"].append(
                f'  <line x1="{snap(stem[0])}" y1="{snap(stem[1])}" '
                f'x2="{snap(parent.cx)}" y2="{snap(bus_y)}" '
                f'stroke="{stroke}" stroke-width="1.5" stroke-linecap="round"{dash}/>'
            )
            for i, child in enumerate(children):
                lab = labels[i] if labels and i < len(labels) else None
                target = child.top if going_down else child.bottom
                self.lpath([(parent.cx, bus_y), (child.cx, bus_y), target],
                           color=color, label=lab, dashed=dashed)

    def _place_label(self, a: Point, b: Point, label: str, plate: bool) -> None:
        # Warn if the label is wider than the carrying segment — a residual
        # defect mode the d25cf57 fix only patched partially. Warn-only;
        # never mutate the label (the agent may have intentional verbosity).
        seg_len = math.hypot(b[0] - a[0], b[1] - a[1])
        label_w = text_width(label, 12)
        if label_w > seg_len - 4 and seg_len > 0:
            print(
                f"svgkit: arrow label '{label}' is ~{label_w:.0f}px wide on a "
                f"~{seg_len:.0f}px segment — it will overlap the arrow. "
                f"Use a shorter label, give the arrow more room, or wrap with "
                f"a plate=True background rect."
            )
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        vertical = abs(b[0] - a[0]) < abs(b[1] - a[1])
        lw = text_width(label, 12)
        seg_len = abs(b[0] - a[0]) + abs(b[1] - a[1])
        # Auto-plate when the label is long relative to its segment, or when
        # the caller forced plate=True. Prevents labels swimming into boxes.
        if not plate and lw > seg_len * 0.85 and seg_len > 0:
            plate = True
        if vertical:
            tx, ty, anchor = mx + 8, my, "start"
        else:
            tx, ty, anchor = mx, my - 8, "middle"
        if plate:
            w = lw + 8
            self._layers["plates"].append(
                f'  <rect x="{snap(tx - (w / 2 if anchor == "middle" else 0))}" '
                f'y="{snap(ty - 8)}" width="{snap(w)}" height="16" rx="3" fill="{BG}"/>'
            )
        self._layers["labels"].append(
            f'  <text x="{snap(tx)}" y="{snap(ty)}" text-anchor="{anchor}" '
            f'dominant-baseline="central" font-size="12" '
            f'fill="{CAPTION}">{_esc(label)}</text>'
        )
        self._note_extent(tx - (lw / 2 if anchor == "middle" else 0), ty - 8, lw + 8, 16)

    # -- containers & legend ----------------------------------------------- #

    def container(self, x: float, y: float, w: float, h: float,
                  label: str | None = None, sub: str | None = None,
                  solid: bool = False) -> None:
        """A grouping box. Dashed (rx=14) by default, or a solid panel (rx=20)."""
        if solid:
            rect = (f'  <rect x="{snap(x)}" y="{snap(y)}" width="{snap(w)}" height="{snap(h)}" '
                    f'rx="20" fill="{FAMILIES["neutral"]["fill"]}" '
                    f'stroke="rgba(31,30,29,0.3)" stroke-width="0.5"/>')
        else:
            rect = (f'  <rect x="{snap(x)}" y="{snap(y)}" width="{snap(w)}" height="{snap(h)}" '
                    f'rx="14" fill="none" stroke="rgba(31,30,29,0.3)" '
                    f'stroke-width="0.5" stroke-dasharray="4 3"/>')
        self._layers["containers"].append(rect)
        # Track container extent even though arrows pass through (passive).
        self._track_extent(x, y, x + w, y + h)
        if label:
            self._layers["containers"].append(
                f'  <text x="{snap(x + 20)}" y="{snap(y + 26)}" dominant-baseline="central" '
                f'font-size="14" font-weight="500" fill="{CONTAINER_TITLE}">{_esc(label)}</text>'
            )
        if sub:
            self._layers["containers"].append(
                f'  <text x="{snap(x + 20)}" y="{snap(y + 44)}" dominant-baseline="central" '
                f'font-size="12" fill="{CONTAINER_SUB}">{_esc(sub)}</text>'
            )
        self._note_extent(x, y, w, h)

    def scope(self, x: float, y: float, w: float, h: float,
              label: str, sub: str | None = None) -> Box:
        """A dashed scope/loop frame with an uppercase letter-spaced label.

        For regions that *mean* something — "EACH TURN", "AGENTIC LOOP",
        "RETRY ×3". Visually a container() variant, but the label is uppercased,
        weight 500, and tracked out (letter-spacing 2) so it reads as a scope
        badge rather than a group title. Still dashed, still a non-obstacle, so
        arrows cross it freely. Returns a Box for anchoring inner content.
        """
        self._layers["containers"].append(
            f'  <rect x="{snap(x)}" y="{snap(y)}" width="{snap(w)}" height="{snap(h)}" '
            f'rx="14" fill="none" stroke="rgba(31,30,29,0.3)" stroke-width="0.5" '
            f'stroke-dasharray="6 4"/>'
        )
        # Scope extent matters for auto-fit height but not for obstacle avoidance.
        self._track_extent(x, y, x + w, y + h)
        self._layers["containers"].append(
            f'  <text x="{snap(x + 22)}" y="{snap(y + 26)}" dominant-baseline="central" '
            f'font-size="14" font-weight="500" letter-spacing="2" '
            f'fill="{CONTAINER_TITLE}">{_esc(label.upper())}</text>'
        )
        if sub:
            self._layers["containers"].append(
                f'  <text x="{snap(x + 22)}" y="{snap(y + 46)}" dominant-baseline="central" '
                f'font-size="12" fill="{CONTAINER_SUB}">{_esc(sub)}</text>'
            )
        self._note_extent(x, y, w, h)
        return Box(x, y, w, h, "neutral")

    def zone(self, divider_x: float, y_top: float, y_bottom: float,
             left_label: str, right_label: str,
             left_cx: float, right_cx: float) -> float:
        """A vertical dashed trust-boundary divider with two column headers.

        For "Local | External", "On-prem | Cloud", "Client | Server" splits: a
        dashed line down the canvas with a header above each side. Put the nodes
        of each side in their own half; cross-zone arrows are the interesting
        ones. Headers are centred at ``left_cx`` / ``right_cx`` (the column
        centres). Returns ``divider_x`` for symmetry / chaining.
        """
        self._layers["containers"].append(
            f'  <line x1="{snap(divider_x)}" y1="{snap(y_top)}" x2="{snap(divider_x)}" '
            f'y2="{snap(y_bottom)}" stroke="rgba(31,30,29,0.3)" stroke-width="0.5" '
            f'stroke-dasharray="6 4"/>'
        )
        self._layers["labels"].append(
            f'  <text x="{snap(left_cx)}" y="{snap(y_top)}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="14" font-weight="500" '
            f'fill="{CONTAINER_TITLE}">{_esc(left_label)}</text>'
        )
        self._layers["labels"].append(
            f'  <text x="{snap(right_cx)}" y="{snap(y_top)}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="14" font-weight="500" '
            f'fill="{CONTAINER_TITLE}">{_esc(right_label)}</text>'
        )
        self._note_extent(max(left_cx, right_cx, divider_x) + 40, y_bottom)
        return divider_x

    def legend(self, items: list[tuple[str, str]], x: float = 40,
               y: float | None = None, gap: float = 24) -> None:
        """Record legend items; ``render()`` emits them after auto-fit.

        Wraps to a new line (24px down) if the next item would pass the right
        margin (40px from the edge); the first item on a row never triggers a
        wrap, so many-item legends never overflow.

        When ``y`` is omitted the legend sits just below the tracked content
        (``content_max_y + 28``), not at a fixed canvas bottom — so a later
        ``fit()`` can grow the canvas around it without the legend overlapping
        nodes.
        """
        self._has_legend = True
        if y is None:
            has_content = self._content_max_y != -math.inf
            y = (self._content_max_y + 28) if has_content else (self.height - 20)
        # Fit may later grow the canvas around already-placed content. Wrap
        # against that effective width now, not merely the constructor width.
        content_right = self._content_max_x if self._content_max_x != -math.inf else 0
        right_limit = max(self._viewbox_x + self.width - 40, content_right)
        cx = x
        row_y = y
        for family, label in items:
            fam = _family(family)
            item_w = 18 + text_width(label, 12) + gap
            if cx != x and cx + item_w > right_limit:
                cx = x
                row_y += 24
            self._layers["legend"].append(
                f'  <rect x="{snap(cx)}" y="{snap(row_y - 6)}" width="12" height="12" rx="3" '
                f'fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
            )
            self._layers["legend"].append(
                f'  <text x="{snap(cx + 18)}" y="{snap(row_y)}" dominant-baseline="central" '
                f'font-size="12" fill="{CAPTION}">{_esc(label)}</text>'
            )
            cx += item_w
            self._note_extent(cx, row_y + 10)

    def auto_legend(self, labels: dict[str, str] | None = None,
                    *, include_neutral: bool = False) -> bool:
        """Build a legend from families used on tracked boxes. Returns True if drawn.

        Skips when fewer than two families appear on the diagram (house rule:
        legend only when 2+ families convey meaning). Accent families get the
        short glosses in ``_FAMILY_GLOSS`` unless ``labels`` overrides a key.
        Call after placing all nodes; before or instead of an explicit ``legend()``.
        """
        order: list[str] = []
        seen: set[str] = set()
        for box in self._boxes:
            fam = box.family
            if fam not in FAMILIES or fam in seen:
                continue
            if fam == "neutral" and not include_neutral:
                continue
            seen.add(fam)
            order.append(fam)
        # Count neutrals toward the "2+ families" rule even when not shown.
        all_families = {b.family for b in self._boxes if b.family in FAMILIES}
        if include_neutral:
            family_count = len(all_families)
        else:
            family_count = len(all_families)  # neutrals still count if present
        if family_count < 2 or not order:
            return False
        gloss = labels or {}
        items = [(f, gloss.get(f, _FAMILY_GLOSS.get(f, f))) for f in order]
        self.legend(items)
        return True

    # -- escape hatch ------------------------------------------------------ #

    def label(self, x: float, y: float, text: str,
               size: int = 12, color: str = CAPTION,
               anchor: str = "start", weight: int = 400) -> None:
        """A standalone text label (not inside a box, not on an arrow).

        Use for timeline tick labels, diagram sub-headings, footnotes, and any
        annotation that lives outside the box/arrow/legend vocabulary.
        ``color`` accepts a hex string or a family name; ``anchor`` is SVG's
        ``text-anchor`` (start / middle / end).
        """
        if color in FAMILIES:
            color = FAMILIES[color]["title"]
        self._layers["labels"].append(
            f'  <text x="{snap(x)}" y="{snap(y)}" text-anchor="{anchor}" '
            f'dominant-baseline="central" font-size="{size}" font-weight="{weight}" '
            f'fill="{color}">{_esc(text)}</text>'
        )
        # Approximate text extent via text_width; ascender/descender tolerance.
        tw = text_width(text, size)
        th = size * 1.2
        if anchor == "middle":
            self._track_extent(x - tw / 2, y - th / 2, x + tw / 2, y + th / 2)
        elif anchor == "end":
            self._track_extent(x - tw, y - th / 2, x, y + th / 2)
        else:
            self._track_extent(x, y - th / 2, x + tw, y + th / 2)

    def raw(self, svg: str, layer: str) -> None:
        """Drop hand-written SVG onto ``layer`` (one of the z-order layers).

        Use for scatter plots, patch grids, vector bars — anything outside the
        box/arrow/container/legend vocabulary.

        ``layer`` is **required**: the silent ``layer="boxes"`` default used
        to bury ``<text>`` under later color blocks because ``box_text``
        (rendered above ``boxes``) was the right layer for text. The
        guiding error below names each layer's role so the mistake can't
        recur.
        """
        if layer is None:
            raise ValueError(
                "raw() requires an explicit layer argument. The seven layers "
                "(back → front in the SVG paint order) are:\n"
                "  'containers' — backdrop art (rects, paths drawn BEHIND everything)\n"
                "  'arrows'     — line/path connectors\n"
                "  'plates'     — opaque background rectangles for arrow labels\n"
                "  'boxes'      — solid colored shapes (boxes, ellipses, cylinders)\n"
                "  'box_text'   — text inside a box (renders above boxes)\n"
                "  'labels'     — standalone text labels (NOT inside a box)\n"
                "  'legend'     — swatch+text legend rows\n"
                "Text goes on 'box_text' or 'labels', never 'boxes'."
            )
        if layer not in self._layers:
            raise ValueError(f"unknown layer {layer!r}; choose from {_LAYERS}")
        self._layers[layer].append(svg)

    # -- output ------------------------------------------------------------ #

    def render(self) -> str:
        x, y = snap(self._viewbox_x), snap(self._viewbox_y)
        w, h = snap(self.width), snap(self.height)
        out: list[str] = []
        out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}" '
                   f'width="{w}" height="{h}" role="img">')
        out.append(f'  <title>{_esc(self.title)}</title>')
        out.append(f'  <desc>{_esc(self.desc)}</desc>')
        out.append(f'  <style>text {{ font-family: {FONT_STACK}; }}</style>')
        out.append(_MARKER)
        out.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{BG}"/>')
        for name in _LAYERS:
            out.extend(self._layers[name])
        out.append('</svg>')
        return "\n".join(out) + "\n"

    def save(self, path: str | Path, *, fit: bool = True) -> str:
        """Write the SVG, creating parent directories when needed.

        ``fit=True`` (default) expands the viewBox on every side to clear content.
        Pass ``fit=False`` only for an intentionally fixed, pixel-exact viewBox.
        """
        if fit:
            self.fit()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.render(), encoding="utf-8")
        return str(target)
