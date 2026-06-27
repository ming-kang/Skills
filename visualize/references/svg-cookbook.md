# SVG Cookbook — copy, paste, adjust

Everything here is ready to paste and conforms to `references/style.md`. Colors, radii, and stroke widths are exact. Coordinates are examples — change them, but keep the relationships (edge-anchored arrows, 40px margins, 56px two-line boxes).

Read the matching diagram in `assets/gallery/<type>.svg` for the feel of each pattern (index: `references/diagram-gallery.md`).

---

## 0. Default method: `scripts/svgkit.py` (do the math in code)

**If `python3` is available, build the diagram with `svgkit` instead of writing raw XML by hand.** It computes box widths from the text (killing the #1 failure — overflow), anchors arrows on edges, owns the z-order, the single marker, the white background, `<title>`/`<desc>`, and the closing `</svg>`. You write the *layout*, not the markup. It emits exactly the clean form shown in the rest of this file, so everything below still describes the output — you just generate it.

```python
python3 << 'EOF'
import sys; sys.path.insert(0, 'scripts')   # adjust to the skill's scripts/ dir
from svgkit import Diagram

d = Diagram(760, 240,
            title="RAG pipeline",
            desc="Query is embedded, retrieves top-k, then grounded by the LLM.")
q = d.node(40, 100, "Query", "user question")
e = d.node(d.right_of(q, 56), 100, "Embed", "to vector")
r = d.node(d.right_of(e, 56), 100, "Retriever", "top-k passages", family="green")
l = d.node(d.right_of(r, 56), 100, "LLM", "grounded answer", family="purple")
d.arrow(q.right, e.left)
d.arrow(e.right, r.left, color="green",  label="vector")
d.arrow(r.right, l.left, color="purple", label="context")
d.legend([("green", "retrieval path"), ("purple", "generation")])
d.save("rag-pipeline.svg")
print("SVG generated")
EOF
```

That is the **entire** diagram. The equivalent by hand is ~30 lines of `<rect>`/ `<text>`/`<line>` plus four width computations and four edge-anchor calculations — more output tokens, and every coordinate is a chance to clip text or cross a box.

**API (primitives + shape helpers, 1:1 with the visual vocabulary):**

| Call | Emits |
|---|---|
| `text_width(s, size=14)` | px width estimate (Latin×8 / CJK×15 at 14px) — the boring math |
| `Diagram(w, h, title, desc)` | skeleton + marker + white bg + title/desc + auto z-order |
| `.node(x, y, title, sub=None, family="neutral", w=None, lines=None)` → `Box` | a box; auto-sizes width if `w` omitted; `lines` adds extra 12/SUB rows (multi-line card); returns edge anchors `.top/.bottom/.left/.right/.cx/.cy` |
| `.right_of(box, gap=60)` | X coordinate `gap` px to the right of `box` (for the next node) |
| `.below(box, gap=60)` | Y coordinate `gap` px below `box` (vertical twin of `right_of`) |
| `.row([{...}, …], x=40, y=40, gap=56)` → `[Box]` | lay nodes left→right on one baseline with equal gaps |
| `.col([{...}, …], x=40, y=40, gap=60)` → `[Box]` | lay nodes top→bottom in a column with equal gaps |
| `.state(x, y, title, sub=None, …)` → `Box` | state-machine rounded rect (alias of `node`) |
| `.diamond(x, y, title, family="amber", hw=None, hh=40)` → `Box` | flowchart decision diamond with centred title |
| `.usecase(x, y, label, family="neutral", w=None, h=60)` → `Box` | UML use-case ellipse (min 140×60). Ellipses ARE collision obstacles — route «include»/«extend» with `.lpath()` around neighbours |
| `.actor(cx, y, label, family="neutral")` → `Box` | UML stick figure (circle head + body) with a 14px label below. Anchor-only Box (no rect drawn); NOT a collision obstacle — keep outside the boundary |
| `.cylinder(x, y, title, sub=None, family="green", w=None, h=54)` → `Box` | datastore cylinder |
| `.lifeline(x, label, y0, y1, family="neutral")` → `Lifeline` | sequence actor box + dashed vertical lifeline |
| `.state_dot(x, y, kind="initial"\|"final")` → `Point` | UML initial / final pseudo-state |
| `.entity(x, y, name, attrs, family="neutral")` → `Box` | ER entity with header band + attribute lines |
| `.class_box(x, y, name, attrs=None, methods=None, family="neutral", abstract=False, stereotype=None)` → `Box` | UML three-compartment class box (min width 160; abstract name italic; `<<interface>>` stereotype when given) |
| `.step(x, y, n, title, sub=None, family="neutral")` → `Box` | numbered step card (circled badge + title + sub) — recipe / ladder |
| `.bar(x, y, w, label, family="neutral", h=28)` → `Box` | Gantt / timeline bar; rounded rect with centred inside label. h=28 < 30 so it is NOT a collision obstacle. Width is the time span, not the label |
| `.panel(x, y, w, h, title, subtitle=None, family="neutral")` → `Box` | white card with a colored header band (the "Step 1 / Result" window) |
| `.arrow(a, b, color=None, label=None, plate=False)` | straight edge-to-edge connector (only the arrival carries the marker) |
| `.lpath([p1, p2, …], color=None, label=None)` | orthogonal L-route around obstacles |
| `.curve(a, b, color=None, label=None)` | cubic bezier branch (mind-map / concept-map) |
| `.container(x, y, w, h, label=None, sub=None, solid=False)` | dashed group (rx14) or solid panel (rx20) |
| `.scope(x, y, w, h, label, sub=None)` → `Box` | dashed loop/scope frame with an uppercase tracked badge (`EACH TURN`…) |
| `.zone(divider_x, y_top, y_bottom, left_label, right_label, left_cx, right_cx)` | vertical dashed trust-boundary divider + two column headers |
| `.legend([(family, label), …])` | swatch+label row near the bottom |
| `.raw(svg, layer=…)` | **escape hatch** — hand-written SVG on a chosen z-layer |

`family` is one of `neutral / green / purple / terracotta / amber`. `color` takes a family name **or** a raw hex. Layers for `.raw()`: `containers, arrows, plates, boxes, box_text, labels, legend`.

> **Compositing patterns** (zone splits, step ladders, verdict rails, titled panels, scope frames, right-gutter loop-backs, side-rails, two-line payload labels, stateful cell strips) live in `references/layout-patterns.md` — reach for it whenever the request is more than a flat box/arrow graph. `.step`, `.panel`, `.scope`, and `.zone` above are the one-liner forms of the most common ones.

**Use `.raw()` for the artistic 20%** — scatter points, patch grids, vector bars (snippets §5–§8 below). svgkit handles boxes/arrows/containers/legend; you hand-draw the custom shapes onto the right layer:

```python
d.raw('<circle cx="450" cy="140" r="5" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>', layer="boxes")
d.raw('<text x="460" y="135" font-size="12" fill="#3D3D3A">king</text>', layer="box_text")
```

A committed, validator-clean parity sample produced by `svgkit` lives at `assets/samples/svgkit-rag.svg`.

> **No `python3`?** Fall back to the hand-written method (§ "Generating with the Python list method" at the end, or just write the file directly with the Write tool). The snippets below are the ground truth either way.

---

## 1. Full skeleton

Paste this, set `W`/`H`, then drop snippets between the comments.

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 460" width="760" height="460" role="img">
  <title>Short title for screen readers</title>
  <desc>One or two sentences describing the diagram.</desc>
  <style>
    text { font-family: 'Anthropic Sans', -apple-system, BlinkMacSystemFont,
           'Segoe UI', 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB',
           'Noto Sans CJK SC', sans-serif; }
  </style>
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke"
            stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>
  <rect width="760" height="460" fill="#FFFFFF"/>

  <!-- containers -->
  <!-- arrows (drawn before boxes so boxes sit on top) -->
  <!-- boxes + text -->
  <!-- legend -->
</svg>
```

**Z-order** (top of file = back): background → dashed/solid containers → arrows → arrow-label background rects → boxes → box text → arrow-label text → legend.

---

## 2. Nodes

> **Width is computed from the text, not guessed.** `svgkit` measures each label (CJK ≈ 2× Latin) and sizes the box to fit, so Chinese labels never clip. The exact formula lives in `references/style.md`; `svgkit.node()` applies it automatically when `w` is omitted.

### Two-line neutral node
```xml
<rect x="300" y="40" width="160" height="56" rx="8"
      fill="#F5F4ED" stroke="rgba(31,30,29,0.3)" stroke-width="0.5"/>
<text x="380" y="62" text-anchor="middle" dominant-baseline="central"
      font-size="14" font-weight="500" fill="#141413">Compressor</text>
<text x="380" y="79" text-anchor="middle" dominant-baseline="central"
      font-size="12" fill="#3D3D3A">splits into KV</text>
```

### One-line neutral node
```xml
<rect x="300" y="40" width="160" height="40" rx="8"
      fill="#F5F4ED" stroke="rgba(31,30,29,0.3)" stroke-width="0.5"/>
<text x="380" y="60" text-anchor="middle" dominant-baseline="central"
      font-size="14" font-weight="500" fill="#141413">Hidden state</text>
```

### Colored family nodes
Swap the four colors together. Green shown; the others are drop-in.
```xml
<!-- GREEN (primary / retrieval) -->
<rect x="60" y="120" width="220" height="56" rx="8"
      fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
<text x="170" y="142" text-anchor="middle" dominant-baseline="central"
      font-size="14" font-weight="500" fill="#085041">Retriever</text>
<text x="170" y="159" text-anchor="middle" dominant-baseline="central"
      font-size="12" fill="#0F6E56">top-k from store</text>
```
| Family | rect fill | rect stroke | title fill | sub fill |
|---|---|---|---|---|
| Purple | `#EEEDFE` | `#534AB7` | `#3C3489` | `#534AB7` |
| Terracotta | `#FAECE7` | `#993C1D` | `#712B13` | `#993C1D` |
| Amber | `#FAEEDA` | `#854F0B` | `#633806` | `#854F0B` |

---

## 3. Containers

```xml
<!-- Dashed group with a top-left label -->
<rect x="40" y="40" width="240" height="300" rx="14"
      fill="none" stroke="rgba(31,30,29,0.3)" stroke-width="0.5" stroke-dasharray="4 3"/>
<text x="60" y="66" font-size="14" font-weight="500" fill="#141413">Knowledge base</text>
<text x="60" y="84" font-size="12" fill="#3D3D3A">indexed once</text>

<!-- Solid section panel -->
<rect x="120" y="40" width="440" height="380" rx="20"
      fill="#F5F4ED" stroke="rgba(31,30,29,0.3)" stroke-width="0.5"/>
<text x="140" y="66" font-size="14" font-weight="500" fill="#141413">61 transformer layers</text>
```
Containers are *not* collision obstacles, so arrows may pass through them freely.

---

## 4. Arrows

```xml
<!-- straight, neutral, with arrowhead -->
<line x1="380" y1="96" x2="380" y2="156" stroke="#73726C" stroke-width="1.5"
      stroke-linecap="round" marker-end="url(#arrow)"/>

<!-- colored (chevron inherits the stroke via context-stroke) -->
<line x1="170" y1="176" x2="170" y2="236" stroke="#1D9E75" stroke-width="1.5"
      stroke-linecap="round" marker-end="url(#arrow)"/>

<!-- split: parent -> two children (each branch its own color) -->
<line x1="380" y1="212" x2="380" y2="232" stroke="#73726C" stroke-width="1.5"/>
<path d="M380 232 L190 232 L190 272" fill="none" stroke="#1D9E75"
      stroke-width="1.5" stroke-linecap="round" marker-end="url(#arrow)"/>
<path d="M380 232 L570 232 L570 272" fill="none" stroke="#7F77DD"
      stroke-width="1.5" stroke-linecap="round" marker-end="url(#arrow)"/>

<!-- merge: two children -> parent -->
<path d="M190 328 L190 348 L380 348" fill="none" stroke="#1D9E75" stroke-width="1.5"/>
<path d="M570 328 L570 348 L380 348" fill="none" stroke="#7F77DD" stroke-width="1.5"/>
<line x1="380" y1="348" x2="380" y2="388" stroke="#73726C" stroke-width="1.5"
      stroke-linecap="round" marker-end="url(#arrow)"/>

<!-- feedback / loop (route around boxes with an L-path) -->
<path d="M460 416 L600 416 L600 160 L460 160" fill="none" stroke="#7F77DD"
      stroke-width="1.5" stroke-linecap="round" marker-end="url(#arrow)"/>
```

### Arrow label
```xml
<text x="285" y="175" text-anchor="middle" dominant-baseline="central" font-size="12"
      fill="#141413">embedding</text>
```
Only add a background plate if it overlaps a line:
```xml
<rect x="262" y="166" width="46" height="16" rx="3" fill="#FFFFFF"/>
```

---

## 5. Striped sequence strip

Alternating pattern (e.g. interleaved layers). Cells are <70px wide so the validator ignores them.
```xml
<!-- repeat, x += 18, alternating the two fills -->
<rect x="198" y="230" width="14" height="18" rx="3" fill="#1D9E75"/>
<rect x="216" y="230" width="14" height="18" rx="3" fill="#7F77DD"/>
<rect x="234" y="230" width="14" height="18" rx="3" fill="#1D9E75"/>
<rect x="252" y="230" width="14" height="18" rx="3" fill="#7F77DD"/>
```

## 6. Vector / embedding bars

Rows of varying width + opacity depict a numeric vector.
```xml
<rect x="490" y="100" width="22" height="12" rx="3" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5" opacity="0.9"/>
<rect x="490" y="115" width="36" height="12" rx="3" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5" opacity="0.55"/>
<rect x="490" y="130" width="16" height="12" rx="3" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5" opacity="0.4"/>
<rect x="490" y="145" width="40" height="12" rx="3" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5" opacity="0.8"/>
<text x="510" y="175" text-anchor="middle" font-size="12" fill="#3D3D3A">vector (1152-d)</text>
```

## 7. Scatter points + leader line

For concept / embedding-space diagrams (put inside a dashed container).
```xml
<!-- direction line from origin to a point -->
<line x1="420" y1="290" x2="450" y2="140" stroke="#1D9E75" stroke-width="1.5"
      stroke-linecap="round" marker-end="url(#arrow)"/>
<!-- the point -->
<circle cx="450" cy="140" r="5" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
<text x="460" y="135" font-size="12" fill="#3D3D3A">king</text>

<!-- leader/callout: dashed line + small anchor dot -->
<line x1="95" y1="87" x2="298" y2="140" stroke="#73726C" stroke-width="0.5" stroke-dasharray="4 3"/>
<circle cx="95" cy="87" r="2" fill="#73726C"/>
```

## 8. Patch / color grid

Decorative tints, 45×45 cells, hairline stroke. (Highlight one cell with a 2px family stroke to single it out.) See `references/style.md` for the full decorative pastel palette (amber / peach / mint / lavender / pink / lime / sky).
```xml
<rect x="50" y="65" width="45" height="45" fill="#FAC775" stroke="#854F0B" stroke-width="2"/>
<rect x="95" y="65" width="45" height="45" fill="#9FE1CB" stroke="rgba(31,30,29,0.3)" stroke-width="0.5"/>
<rect x="140" y="65" width="45" height="45" fill="#CECBF6" stroke="rgba(31,30,29,0.3)" stroke-width="0.5"/>
```

## 9. Legend row

```xml
<rect x="40" y="420" width="12" height="12" rx="3" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
<text x="58" y="426" dominant-baseline="central" font-size="12" fill="#3D3D3A">Retrieval path</text>
<rect x="200" y="420" width="12" height="12" rx="3" fill="#EEEDFE" stroke="#534AB7" stroke-width="0.5"/>
<text x="218" y="426" dominant-baseline="central" font-size="12" fill="#3D3D3A">Index / write path</text>
```

---

## Collision-safe checklist (matches `scripts/validate_svg.py`)

- Treat the diagram like a small DRC pass: obstacles, text boxes, arrow segments, and label plates are separate objects.
- Solid shapes ≥70×30 are obstacles. **Never** run a straight `<line>`/`<path>` segment through one — anchor at the edge or route an L-path around it.
- These are *not* obstacles: dashed rects, `fill="none"` rects, cells <70 wide or <30 tall, and panels larger than 70% of the viewBox.
- Keep solid sibling obstacles from overlapping; leave at least 8px clearance even inside dense panels.
- Text must fit its host box; outside labels must not overlap nodes, other labels, or arrow strokes unless a white plate sits behind the label.
- Paint in z-order: containers → arrows → plates → boxes → box text → labels → legend, so color blocks never cover text.
- Every `marker-end="url(#arrow)"` must reference the `<marker id="arrow">`.
- Keep filtered/edge elements ≥ a few px inside the viewBox (we use no filters, so this is automatic).

## Generating with the Python list method (fallback)

Prefer `svgkit` (§0). Use this hand-written method only when you need full manual control or `python3` is unavailable. Append one line at a time so the file can't be truncated mid-tag:

```python
lines = []
lines.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 460" width="760" height="460" role="img">')
# ... one lines.append(...) per element ...
lines.append('</svg>')
open('out.svg','w',encoding='utf-8').write('\n'.join(lines))
```
