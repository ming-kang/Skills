"""Shared presentation helpers for the owned reference diagrams."""

from html import escape

from svgkit import FAMILIES, Diagram, snap, text_width


def text(d, x, y, value, *, size=12, family="neutral", anchor="start",
         role="caption", layer="labels", weight=None):
    color = FAMILIES[family]["title" if size >= 14 else "sub"]
    weight = weight or (500 if size == 14 else 400)
    d.raw(f'<text data-role="{role}" x="{snap(x)}" y="{snap(y)}" '
          f'text-anchor="{anchor}" dominant-baseline="central" '
          f'font-size="{size}" font-weight="{weight}" fill="{color}">'
          f'{escape(value)}</text>', layer=layer)


def canvas(width, height, title, desc, subtitle=None):
    d = Diagram(width, height, title=title, desc=desc)
    text(d, 40, 32, title, size=16, weight=600, role="diagram-title")
    if subtitle:
        text(d, 40, 56, subtitle)
    return d


def rail(d, points, family="neutral", *, dashed=False):
    """A shared connector segment; arrowheads belong only at destination nodes."""
    route = "M" + " L".join(f"{snap(x)} {snap(y)}" for x, y in points)
    dash = ' stroke-dasharray="4 3"' if dashed else ''
    d.raw(f'<path d="{route}" fill="none" stroke="{FAMILIES[family]["line"]}" '
          f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"{dash}/>',
          layer="arrows")


def rule(d, x1, y, x2, *, layer="containers"):
    d.raw(f'<line x1="{snap(x1)}" y1="{snap(y)}" x2="{snap(x2)}" y2="{snap(y)}" '
          'stroke="rgba(31,30,29,0.3)" stroke-width="0.5"/>', layer=layer)


def footer(d, colors=(), edges=()):
    """Wrap a compact key, reserving a 40px bottom margin for every row."""
    items = [(family, label, None) for family, label in colors] + list(edges)
    positions, x, row = [], 40, 0
    for family, label, dashed in items:
        symbol = 18 if dashed is None else 42
        width = symbol + text_width(label, 12)
        if x > 40 and x + width > d.width - 40:
            x, row = 40, row + 1
        positions.append((x, row, family, label, dashed))
        x += width + 24
    if not positions:
        return
    top = d.height - 40 - row * 24
    rule(d, 40, top - 24, d.width - 40, layer="legend")
    for x, row, family, label, dashed in positions:
        y = top + row * 24
        fam = FAMILIES[family]
        if dashed is None:
            d.raw(f'<rect x="{snap(x)}" y="{snap(y - 6)}" width="12" height="12" '
                  f'rx="3" fill="{fam["fill"]}" stroke="{fam["stroke"]}" stroke-width="0.5"/>',
                  layer="legend")
            tx = x + 18
        else:
            dash = ' stroke-dasharray="4 3"' if dashed else ''
            d.raw(f'<line x1="{snap(x)}" y1="{snap(y)}" x2="{snap(x + 30)}" y2="{snap(y)}" '
                  f'stroke="{fam["line"]}" stroke-width="1.5" stroke-linecap="round"'
                  f'{dash} marker-end="url(#arrow)"/>', layer="legend")
            tx = x + 42
        text(d, tx, y, label, role="legend-label", layer="legend")


def activation(d, cx, top, bottom, family="neutral"):
    fam = FAMILIES[family]
    d.raw(f'<rect data-role="activation" x="{cx - 6}" y="{top}" width="12" '
          f'height="{bottom - top}" rx="4" fill="{fam["fill"]}" '
          f'stroke="{fam["stroke"]}" stroke-width="0.5"/>')
