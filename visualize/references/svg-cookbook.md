# SVG cookbook

Use `scripts/svgkit.py` with Python 3.10+. It provides estimated text sizing, edge anchors, layer order, the shared marker, and validation, using only the standard library. [Style](style.md) defines the tokens; [layout patterns](layout-patterns.md) shows how to compose the primitives.

## 0. Complete runnable example

Save this as `draw.py` and run `python draw.py /path/to/visualize output.svg`. The first argument is the installed skill folder, wherever it resides. The output directory must exist.

```python
import sys
from pathlib import Path

skill_dir = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(skill_dir / "scripts"))
from svgkit import Diagram

d = Diagram(600, 300, title="Import records",
            desc="The parser reads records from an input file.")
d.panel(40, 40, 520, 176, "Import")
source = d.node(64, 104, "Source file", "raw records", w=160)
parser = d.node(376, 104, "Parser", "validated rows", family="green", w=160)
d.arrow(source.right, parser.left, color="green", label="records", label_offset=12)
d.legend([("neutral", "Source"), ("green", "Processing")])
d.save(sys.argv[2])
```

This example is complete and validates without warnings. After changing its content, inspect the rendered SVG; estimated text dimensions do not replace actual font measurements.

## 1. Nodes, groups, and notation

`family` is `neutral`, `green`, `purple`, `terracotta`, or `amber`. `Box` results expose `x`, `y`, `w`, `h`, `cx`, `cy`, and edge-midpoint tuples `top`, `bottom`, `left`, `right`.

| Call | Result and behavior |
|---|---|
| `Diagram(width, height, title=..., desc=...)` | Complete SVG document; title and description are accessibility text. Add a visible heading separately if useful. |
| `text_width(text, size=14)` | Conservative pixel-width estimate, including CJK. |
| `box_width(*lines, sizes=(14, 12))` | Required width rounded to 4px, minimum 120px, with 16px side padding. |
| `d.node(x, y, title, sub=None, family="neutral", w=None, h=None, lines=None)` | `Box`; auto-sizes unless dimensions are supplied. Use `sub` or `lines`, not both. |
| `d.state(x, y, title, sub=None, **options)` | State box with the same sizing as `node()`. |
| `d.step(x, y, n, title, sub=None, family="neutral", w=None, h=None)` | `Box` with a numbered badge. |
| `d.diamond(x, y, title, family="amber", hw=None, hh=40)` | `Box`; `hw`/`hh` are half-width/half-height. Automatic width allows for sloping sides. |
| `d.cylinder(x, y, title, sub=None, family="green", w=None, h=54)` | `Box`; `h` is the body height, and the returned bounds include curved caps. |
| `d.usecase(x, y, label, family="neutral", w=None, h=60)` | Ellipse `Box`; route around its curved outline. |
| `d.actor(cx, y, label, family="neutral")` | Stick figure and an anchor `Box`; keep the label clear. |
| `d.lifeline(x, label, y0, y1, family="neutral", w=None)` | Participant box plus dashed lifeline; result exposes `x`, `y0`, `y1`, and `actor`. |
| `d.state_dot(x, y, kind="initial")` | Initial dot or `kind="final"` ringed dot. |
| `d.entity(x, y, name, attrs, family="neutral", w=None)` | Entity name and attribute compartments. |
| `d.class_box(x, y, name, attrs=None, methods=None, family="neutral", abstract=False, stereotype=None, w=None)` | Three-compartment class box; stereotype and name receive separate baselines. |
| `d.bar(x, y, w, label, family="neutral", h=28)` | Fixed-width chart mark. Use an empty label and external caption if text cannot fit. |
| `d.container(x, y, w, h, label=None, sub=None, solid=False)` | Dashed group or a solid neutral panel. |
| `d.panel(x, y, w, h, title, subtitle=None, family="neutral")` | White panel with a 26px colored header band; returns a `Box`. Subtitle shares the header row. |
| `d.scope(x, y, w, h, label, sub=None)` | Dashed frame with an uppercase scope badge; returns a `Box`. |
| `d.zone(divider_x, y_top, y_bottom, left_label, right_label, left_cx, right_cx)` | Boundary divider and region headings. |

## 2. Positioning

`d.right_of(box, gap=60)` returns the next x position; `d.below(box, gap=60)` returns the next y position. `d.row(specs, x=40, y=40, gap=56)` and `d.col(specs, x=40, y=40, gap=60)` take dictionaries of node arguments and return boxes. They do not route connectors or resize the canvas. `col()` aligns left edges, so use a common computed width to align centers.

```python
from svgkit import box_width

labels = [("Receive", "input records"), ("Validate", "required fields")]
width = max(box_width(title, sub) for title, sub in labels)
nodes = d.col([dict(title=title, sub=sub, w=width) for title, sub in labels],
              x=80, y=80, gap=60)
d.arrow(nodes[0].bottom, nodes[1].top)
```

Explicit dimensions are your responsibility. Boxes may share a larger width, but timeline bars and other value-driven marks must keep their data scale. Leave room beneath panel headers and above the entire legend.

## 3. Connections

`color` accepts a family name, a CSS paint, or `None` for Neutral. The standard style uses family LINE colors.

| Call | Behavior |
|---|---|
| `d.arrow(a, b, color=None, label=None, plate=False, dashed=False, both=False, label_offset=8)` | Straight edge-to-edge connector; `both=True` adds a start arrowhead. |
| `d.lpath(points, color=None, label=None, plate=False, dashed=False, both=False, label_offset=8)` | Multi-segment route; label on the longest segment. Supply orthogonal points for a right-angle route. |
| `d.curve(a, b, color=None, label=None, marker=True, dashed=False, label_offset=8)` | Cubic curve, useful for lateral branches; plain vertical connections can use `arrow()`. |
| `d.branch(center, target, family="neutral", label=None, marker=False, label_offset=8)` | Curve between two boxes with automatically selected edge anchors; unheaded by default. |

Positive `label_offset` places text right of a vertical segment or above a horizontal one; negative uses the other side. A plate can clear a line crossing but cannot repair text over a node. Define the meaning of dashed edges in the legend.

For a shared trunk or an annotation leader, use an unheaded raw path. Give shared trunks `data-role="connector"` and 1.5px strokes. Annotation leaders can be 0.5–0.75px, optionally dashed, and have no arrowhead. See [parallel pipelines](../assets/gallery/patterns/parallel-pipelines.svg) and [feedback pipeline](../assets/gallery/patterns/feedback-pipeline.svg).

## 4. Custom marks and layers

`d.raw(svg, layer="boxes")` inserts literal SVG. Layers, back to front:

`containers` → `arrows` → `plates` → `boxes` → `box_text` → `labels` → `legend`.

Panel backgrounds belong on `containers`. Put fixed-size data marks on `boxes`, then their captions on `labels`. Reuse the family tokens exported as `FAMILIES`. Escape user text with `html.escape()` when constructing raw XML.

```python
from html import escape
from svgkit import FAMILIES

family = FAMILIES["green"]
d.raw(f'<circle data-role="data-mark" cx="80" cy="100" r="5" '
      f'fill="{family["line"]}"/>')
d.raw(f'<text data-role="caption" x="96" y="100" dominant-baseline="central" '
      f'font-size="12" fill="{family["sub"]}">{escape("Sample point")}</text>', layer="labels")
```

Use `data-role="node"` for ordinary routing obstacles; `panel`/`container` for intentional groups; `node-part` for compound-shape pieces; `data-mark` for marks whose geometry represents values; and `connector` for markerless graph edges. Text roles include `node-text`, `arrow-label`, `container-label`, and `legend-label`. The helpers emit these hints automatically. For complex raw fragments, set roles explicitly on the relevant elements.

## 5. Legend, output, and validation

`d.legend([(family, label), ...], x=40, y=None)` wraps color swatches above the 40px bottom margin. An explicit `y` is the first row's center; every additional row consumes 24px. Use matching raw line/point symbols for a connection or data-series key; see [annotated-chart.svg](../assets/gallery/patterns/annotated-chart.svg).

`d.render()` returns SVG text. `d.save(path, check=True)` writes the file, reports findings, and returns the path when there are no hard failures. Warnings are non-fatal. A failure raises `ValidationError` with the complete `.results`; the SVG remains available to inspect. Validator load/run errors also raise. `check=False` skips that pass, so validate separately before delivery.

```bash
python SKILL_DIR/scripts/validate_svg.py --strict -q output-directory/
python SKILL_DIR/scripts/validate_svg.py --json diagram.svg other.svg
```

See [validation.md](validation.md) for supported geometry and CSS, severity, and JSON output. Rendering is still necessary to assess actual fonts, layer order, and reading clarity.

## 6. Manual SVG

Without Python, start from a complete [skeleton](diagram-gallery.md#skeletons) or gallery SVG. Preserve the namespace, title/description, inline font stack, open-chevron definition, and white canvas. Replace the content, resize from the labels, update every affected endpoint, and keep the paint order above.

For custom geometry, the distributed SVGs are runnable references: [cylinders](../assets/gallery/architecture.svg), [decisions](../assets/gallery/flowchart.svg), [actors and ellipses](../assets/gallery/use-case.svg), [scaled bands](../assets/gallery/patterns/annotated-funnel.svg), and [miniature mechanisms](../assets/gallery/patterns/mechanism-comparison.svg). They do not depend on this repository's build tools.
