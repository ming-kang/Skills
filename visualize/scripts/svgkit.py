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
>>> d = Diagram(680, 220, title="RAG pipeline", desc="Query to grounded answer.")
>>> q = d.node(40, 90, "Query", "user question")
>>> r = d.node(d.right_of(q, 60), 90, "Retriever", "top-k", family="green")
>>> d.arrow(q.right, r.left, label="embed")
>>> d.save("rag.svg")
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass

__all__ = ["FAMILIES", "text_width", "box_width", "snap", "Box", "Lifeline", "Diagram"]


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
    """Accept a family name, a hex/rgb string, or None (neutral)."""
    if color is None:
        return NEUTRAL_LINE
    if color in FAMILIES:
        return FAMILIES[color]["line"]
    return color


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
                 desc: str = ""):
        self.width = width
        self.height = height
        self.title = title
        self.desc = desc
        self._layers: dict[str, list[str]] = {name: [] for name in _LAYERS}

    # -- layout helpers ---------------------------------------------------- #

    @staticmethod
    def right_of(box: Box, gap: float = 60) -> float:
        """X coordinate ``gap`` px to the right of ``box`` (for the next node)."""
        return box.x + box.w + gap

    @staticmethod
    def below(box: Box, gap: float = 60) -> float:
        """Y coordinate ``gap`` px below ``box`` (the vertical twin of ``right_of``)."""
        return box.y + box.h + gap

    def row(self, specs: list[dict], x: float = 40, y: float = 40,
            gap: float = 56) -> list[Box]:
        """Lay ``specs`` left→right on one baseline; equal ``gap`` between each.

        Each spec is a kwargs dict for ``node()`` (without ``x``/``y``). Returns
        the boxes so you can anchor arrows off their edges. The gap is constant
        so connectors between neighbours are all the same length.
        """
        boxes: list[Box] = []
        cur_x = x
        for spec in specs:
            b = self.node(cur_x, y, **spec)
            boxes.append(b)
            cur_x = self.right_of(b, gap)
        return boxes

    def col(self, specs: list[dict], x: float = 40, y: float = 40,
            gap: float = 60) -> list[Box]:
        """Lay ``specs`` top→bottom in a column; equal ``gap`` between each.

        Vertical twin of ``row``. Note the boxes are left-aligned on ``x`` (not
        center-aligned) — snap arrow anchors to ``.top``/``.bottom`` rather than
        assuming equal widths.
        """
        boxes: list[Box] = []
        cur_y = y
        for spec in specs:
            b = self.node(x, cur_y, **spec)
            boxes.append(b)
            cur_y = self.below(b, gap)
        return boxes

    def _marker_for(self, color: str | None) -> str:
        """Resolve ``marker-end``.

        One ``context-stroke`` marker (``url(#arrow)``) serves every color — the
        open chevron recolors itself to match each arrow's stroke.
        """
        return "url(#arrow)"

    # -- nodes ------------------------------------------------------------- #

    def node(self, x: float, y: float, title: str, sub: str | None = None,
             family: str = "neutral", w: float | None = None,
             h: float | None = None, lines: list[str] | None = None) -> Box:
        """A rounded box, sized from its text unless ``w`` is given.

        Two lines (title + sub) default to height 56; one line to 40. Pass
        ``lines`` (extra 12/SUB rows beneath the title) for a multi-line card —
        ``sub`` and ``lines`` are mutually exclusive. With ``lines`` the height
        is ``22 + 18 * (1 + len(lines))`` (a 22px title band plus 18px per row).
        """
        if sub is not None and lines is not None:
            raise ValueError("node() accepts `sub` (one line) or `lines` (many), not both")
        fam = FAMILIES[family]
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
        self._layers["boxes"].append(
            f'  <rect x="{snap(x)}" y="{snap(y)}" width="{snap(w)}" height="{snap(h)}" rx="8" '
            f'fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
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
        return Box(x, y, w, h, family)

    def state(self, x: float, y: float, title: str, sub: str | None = None,
              family: str = "neutral", w: float | None = None,
              h: float | None = None, lines: list[str] | None = None) -> Box:
        """A UML state node; geometrically identical to ``node()`` (semantic alias)."""
        return self.node(x, y, title, sub, family=family, w=w, h=h, lines=lines)

    def diamond(self, x: float, y: float, title: str, family: str = "amber",
                hw: float | None = None, hh: float = 40) -> Box:
        """Decision diamond. ``hw`` = half-width, ``hh`` = half-height; ``(x, y)`` is
        the top-left of the bounding box (so the diamond is centred at
        ``(x + hw, y + hh)`` and spans ``2*hw`` × ``2*hh``). If ``hw`` is None it
        is sized from ``title``.
        """
        fam = FAMILIES[family]
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
        return Box(x, y, w, h, family)

    def usecase(self, x: float, y: float, label: str,
                family: str = "neutral", w: float | None = None,
                h: float = 60) -> Box:
        """UML use-case ellipse (min 140x60) with a centred label.

        ``x, y`` is the top-left of the bounding box. Width auto-sizes from the
        label (min 140); height defaults to 60. An ellipse this size IS a
        collision obstacle, so route ``<<include>>`` / ``<<extend>>`` arrows with
        ``lpath()`` around neighbouring ellipses.
        """
        fam = FAMILIES[family]
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
        return Box(x, y, w, h, family)

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
        fam = FAMILIES[family]
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
        return Box(cx - 20, y, 40, 64, family)

    def cylinder(self, x: float, y: float, title: str, sub: str | None = None,
                 family: str = "green", w: float | None = None, h: float = 54) -> Box:
        """Datastore cylinder. ``(x, y)`` is the top-left of the body; cap ry = min(w/6, 9) (flat cap)."""
        fam = FAMILIES[family]
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
        return Box(x, y, w, total_h, family)

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
        return Lifeline(actor=actor, x=cx, y0=y0, y1=y1)

    def state_dot(self, x: float, y: float, kind: str = "initial") -> Point:
        """UML initial (filled) or final (double circle) pseudo-state."""
        if kind == "initial":
            self._layers["boxes"].append(
                f'  <circle cx="{snap(x)}" cy="{snap(y)}" r="8" fill="#141413"/>'
            )
        elif kind == "final":
            self._layers["boxes"].append(
                f'  <circle cx="{snap(x)}" cy="{snap(y)}" r="12" fill="none" '
                f'stroke="#141413" stroke-width="1.5"/>'
            )
            self._layers["boxes"].append(
                f'  <circle cx="{snap(x)}" cy="{snap(y)}" r="8" fill="#141413"/>'
            )
        else:
            raise ValueError(f"state_dot kind must be 'initial' or 'final', got {kind!r}")
        return (x, y)

    def entity(self, x: float, y: float, name: str, attrs: list[str],
               family: str = "neutral", w: float | None = None) -> Box:
        """ER entity: header band + attribute lines."""
        fam = FAMILIES[family]
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
        return Box(x, y, w, h, family)

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
        fam = FAMILIES[family]
        attrs = attrs or []
        methods = methods or []
        name_h = 30 + (10 if stereotype else 0)
        attr_h = max(len(attrs), 1) * 18 + 8
        meth_h = max(len(methods), 1) * 18 + 8
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
        self._layers["boxes"].append(
            f'  <line x1="{snap(x)}" y1="{snap(y + name_h)}" x2="{snap(x + w)}" '
            f'y2="{snap(y + name_h)}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
        )
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
        return Box(x, y, w, h, family)

    def step(self, x: float, y: float, n: int, title: str,
             sub: str | None = None, family: str = "neutral",
             w: float | None = None, h: float | None = None) -> Box:
        """A numbered step card — circled badge + title (+ optional sub).

        Reads as one item in a recipe / pipeline / permission ladder. The badge
        is a neutral disc so it stands out on every family fill; the number takes
        the family TITLE color. Width grows from the text (44px badge area +
        16px right pad, min 150), so labels never clip. Height 56 with sub, 44 without.
        """
        fam = FAMILIES[family]
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
        return Box(x, y, w, h, family)

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
        fam = FAMILIES[family]
        self._layers["boxes"].append(
            f'  <rect x="{snap(x)}" y="{snap(y)}" width="{snap(w)}" height="{snap(h)}" rx="6" '
            f'fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>'
        )
        self._layers["box_text"].append(
            f'  <text x="{snap(x + w / 2)}" y="{snap(y + h / 2)}" text-anchor="middle" '
            f'dominant-baseline="central" font-size="12" '
            f'fill="{fam["sub"]}">{_esc(label)}</text>'
        )
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
        fam = FAMILIES[family]
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
        return Box(x, y, w, h, family)

    # -- arrows ------------------------------------------------------------ #

    def arrow(self, a: Point, b: Point, color: str | None = None,
              label: str | None = None, plate: bool = False) -> None:
        """A straight connector ``a -> b``. ``color`` is a family name or hex."""
        stroke = _resolve_line(color)
        self._layers["arrows"].append(
            f'  <line x1="{snap(a[0])}" y1="{snap(a[1])}" x2="{snap(b[0])}" y2="{snap(b[1])}" '
            f'stroke="{stroke}" stroke-width="1.5" stroke-linecap="round" '
            f'marker-end="{self._marker_for(color)}"/>'
        )
        if label:
            self._place_label(a, b, label, plate)

    def lpath(self, points: list[Point], color: str | None = None,
              label: str | None = None, plate: bool = False) -> None:
        """An orthogonal multi-segment route; only the arriving end carries the marker."""
        if len(points) < 2:
            raise ValueError("lpath needs at least two points")
        stroke = _resolve_line(color)
        d = "M" + " L".join(f"{snap(px)} {snap(py)}" for px, py in points)
        self._layers["arrows"].append(
            f'  <path d="{d}" fill="none" stroke="{stroke}" stroke-width="1.5" '
            f'stroke-linecap="round" marker-end="{self._marker_for(color)}"/>'
        )
        if label:
            # Place the label on the longest segment — the most readable spot,
            # not whichever index happens to sit at the middle.
            segs = [(points[i], points[i + 1]) for i in range(len(points) - 1)]
            longest = max(segs, key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
            self._place_label(longest[0], longest[1], label, plate)

    def curve(self, a: Point, b: Point, color: str | None = None,
              label: str | None = None, marker: bool = True) -> None:
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
            f'stroke-linecap="round"{end}/>'
        )
        if label:
            self._place_label(a, b, label, plate=False)

    def _place_label(self, a: Point, b: Point, label: str, plate: bool) -> None:
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        vertical = abs(b[0] - a[0]) < abs(b[1] - a[1])
        if vertical:
            tx, ty, anchor = mx + 8, my, "start"
        else:
            tx, ty, anchor = mx, my - 8, "middle"
        if plate:
            w = text_width(label, 12) + 8
            self._layers["plates"].append(
                f'  <rect x="{snap(tx - (w / 2 if anchor == "middle" else 0))}" '
                f'y="{snap(ty - 8)}" width="{snap(w)}" height="16" rx="3" fill="{BG}"/>'
            )
        self._layers["labels"].append(
            f'  <text x="{snap(tx)}" y="{snap(ty)}" text-anchor="{anchor}" '
            f'dominant-baseline="central" font-size="12" '
            f'fill="{CAPTION}">{_esc(label)}</text>'
        )

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

    def scope(self, x: float, y: float, w: float, h: float,
              label: str, sub: str | None = None) -> Box:
        """A dashed scope/loop frame with an uppercase letter-spaced label.

        For regions that *mean* something — "EACH TURN", "AGENTIC LOOP",
        "RETRY ×3". Visually a container() variant, but the label is uppercased,
        weight 600, and tracked out (letter-spacing 2) so it reads as a scope
        badge rather than a group title. Still dashed, still a non-obstacle, so
        arrows cross it freely. Returns a Box for anchoring inner content.
        """
        self._layers["containers"].append(
            f'  <rect x="{snap(x)}" y="{snap(y)}" width="{snap(w)}" height="{snap(h)}" '
            f'rx="14" fill="none" stroke="rgba(31,30,29,0.3)" stroke-width="0.5" '
            f'stroke-dasharray="6 4"/>'
        )
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
        return divider_x

    def legend(self, items: list[tuple[str, str]], x: float = 40,
               y: float | None = None, gap: float = 24) -> None:
        """A horizontal swatch+label row. ``items`` = [(family, label), ...].

        Wraps to a new line (24px down) if the next item would pass the right
        margin (40px from the edge); the first item on a row never triggers a
        wrap, so many-item legends never overflow.
        """
        if y is None:
            y = self.height - 20
        right_limit = self.width - 40
        cx = x
        row_y = y
        for family, label in items:
            fam = FAMILIES.get(family, FAMILIES["neutral"])
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

    # -- escape hatch ------------------------------------------------------ #

    def raw(self, svg: str, layer: str = "boxes") -> None:
        """Drop hand-written SVG onto ``layer`` (one of the z-order layers).

        Use for scatter plots, patch grids, vector bars — anything outside the
        box/arrow/container/legend vocabulary.
        """
        if layer not in self._layers:
            raise ValueError(f"unknown layer {layer!r}; choose from {_LAYERS}")
        self._layers[layer].append(svg)

    # -- output ------------------------------------------------------------ #

    def render(self) -> str:
        w, h = snap(self.width), snap(self.height)
        out: list[str] = []
        out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
                   f'width="{w}" height="{h}" role="img">')
        out.append(f'  <title>{_esc(self.title)}</title>')
        out.append(f'  <desc>{_esc(self.desc)}</desc>')
        out.append(f'  <style>text {{ font-family: {FONT_STACK}; }}</style>')
        out.append(_MARKER)
        out.append(f'  <rect width="{w}" height="{h}" fill="{BG}"/>')
        for name in _LAYERS:
            out.extend(self._layers[name])
        out.append('</svg>')
        return "\n".join(out) + "\n"

    def save(self, path: str) -> str:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.render())
        return path
