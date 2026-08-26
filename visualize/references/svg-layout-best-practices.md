# SVG Technical Diagram Layout Best Practices

Layout and routing rules for the one house style. Tokens (colors, fonts, the open-chevron marker) live in `references/style.md`; paste-ready snippets in `references/svg-cookbook.md`.

## 1. Canvas & spacing

- **Canvas**: viewBox `0 0 W H`. Width ~720 is typical. Height grows to fit. Outer **margin 40px**. White background rect. Snap all coordinates to integers.
- **Node size**: height **56** (two-line) or **40** (one-line); `rx="8"`. **Width is computed from the text, never a round guess** (CJK ≈ 2× Latin). Text overflow is the #1 diagram failure; `svgkit` and the validator both size off the text. Exact formula: `references/style.md`.
- **Vertical gap** between stacked boxes: **≥ 56–60px** (the connector lives in the gap).
- **Horizontal gap** between boxes: **≥ 40–75px**.
- **Containers**: dashed group `rx="14"`; solid panel `rx="20"`; hairline `0.5` stroke.
- **Reserve canvas height for the legend.** The legend defaults to the bottom row. If the lowest nodes (datastores, result boxes) already reach the bottom, grow the canvas by ~40px so the legend gets its own clear row instead of overlapping a node — a legend swimming into a cylinder reads as a mistake even when both are individually correct.

## 2. Arrow routing & connection points

- **One marker** — the open chevron (`references/style.md`). It recolors per line via `context-stroke`. Lines are `stroke-width="1.5"`, `stroke-linecap="round"`.
- **Anchor on edges, never centers.** A vertical connector between two stacked boxes runs from the bottom-edge midpoint of one to the top-edge midpoint of the next.
- **Never run a straight segment through a box.** Use an orthogonal L-shaped `<path>` to route around it. Only the *arriving* segment carries `marker-end`.
- **Branches**: split a parent into children with `M px py L bx py L bx cy` per child (color each branch with its family LINE color); merge with the mirror.
- **Multiple arrows between the same two rows**: stagger by 15–20px so heads don't overlap.
- **Crossings**: prefer rerouting. If unavoidable, a 5px white jump-over arc on the lower-priority line reads cleanly (we use no other tricks).

## 3. Arrow labels

- Short (**≤3 words**), 12–14px, family TITLE/SUB color.
- Place at the segment midpoint, offset 6–15px perpendicular to the line.
- Add a `#FFFFFF` background plate **only** if the offset still overlaps a line or box (padding ~4px×2px). Most labels need no plate.
- **A label must be shorter than the arrow it rides.** The gap between neighbouring boxes is often only ~40px, but a few words of text easily exceed that — a centered label wider than its arrow spills into the boxes on both ends. When the natural wording is too long, either shorten it (`top-k chunks` → `top-k`), widen the gap so the arrow is long enough to carry it, or flip the label to the emptier side of the line (`svgkit`: negate `label_offset`). Never let a label overhang into an adjacent box. The `label vs box` check enforces this.
- **`label_offset` is signed.** On a vertical segment positive puts the label to the right of the line, negative to the left; on a horizontal segment positive is above, negative below. A right-gutter loop-back or a return edge running down a left-hand gutter usually wants the negative side.

## 4. Self-check pass (automated — read the output, don't eyeball it)

This is an explicit pass, and it is **code**. `svgkit`'s `d.save()` runs it on the file it just wrote; for hand-written SVG run `python3 scripts/validate_svg.py <file>…` (several files at once; `-q` prints only the ones with problems). Each item below names the check that enforces it and what to do about a finding.

| Item | Check | Verdict | Fix |
|---|---|---|---|
| **Box vs box** — no two solid boxes partially overlap | `box overlap` | fail | Move them apart (≥40–75px horizontal, ≥56px vertical). Full containment is exempt — a `panel()` holding nodes is intentional. |
| **Arrow vs box** — no segment cuts through a box | `arrow collisions` | fail | Reroute as an orthogonal L-bend around the box; anchor endpoints on edges. Filled `<path>` shapes (a `cylinder()` body) count as obstacles. |
| **Box vs canvas** — nothing spills the viewBox | `box bounds vs viewBox` | fail | Grow `Diagram(w, h)` or move the element in. |
| **Text vs its box** — every label fits the box it sits in | `text fit` | warn | Size the box from the text (§1). `svgkit.node()` does it for you. |
| **Label vs box** — a label outside a box doesn't land on one | `label vs box` | warn | Shorten the wording, widen the gap so the arrow carries it, or flip the label to the other side with `label_offset=-8`. Also catches a legend row swimming into the bottom row of nodes. |
| **Label vs label** — no two free labels overlap | `label vs label` | warn | Nudge the perpendicular offset (6–15px) or stagger neighbours by ~20px. |

Warnings are warnings because the width estimate deliberately errs wide — but treat them as real until you've looked at the file. Errors are never acceptable.

Obstacle rules the geometry checks share: solid rects/circles/ellipses/polygons and **filled paths** ≥70×30 are obstacles; dashed containers, `fill="none"` rects, cells <70 wide or <30 tall, and panels >70% of the viewBox are not — so arrows may freely cross a dashed group or a tiny swatch.

## 5. Z-order (SVG render order; top of file = back)

```
1. Background rect
2. Grouping containers (dashed rects, solid panels)
3. Arrow paths / lines
4. Arrow-label background plates (only if used)
5. Boxes (rects, cylinders, diamonds…)
6. Box text
7. Arrow-label text
8. Legend
```

## 6. The flat rule

- **No** drop shadows, gradients, `<filter>`s, or blur. Ever.
- Hairline box strokes (`0.5`), 1.5px round-cap lines, open-chevron heads.
- Warm palette only (`references/style.md`) — no cold gray/blue Tailwind values.
- Self-contained: inline font in `<style>`, no `@import`, no remote `url()/href/src`.

## Pre-export checklist

Everything below the rule is enforced by `scripts/validate_svg.py` (and therefore by `d.save()`); the items above it are judgement calls only you can make.

- [ ] Labels ≤3 words; sentence case; plates only where needed.
- [ ] Box fills/strokes/text use the family tokens; arrows use family LINE colors.
- [ ] Meaning carried by color and (sparingly) dashing — not by arrowhead shape or line thickness.
- [ ] Legend present when 2+ families or 2+ arrow meanings appear.
- [ ] Canvas is tall enough that the legend gets its own row.

---

- [ ] `<title>` + `<desc>` are the first children.
- [ ] Every box width was computed from its text (CJK ≈ 2× Latin); nothing clips.
- [ ] Only two font sizes (14 / 12), plus at most one 15–16 heading.
- [ ] Exactly one `<marker id="arrow">` in `<defs>`; every `marker-end` references it.
- [ ] No solid boxes partially overlap; nothing spills the viewBox.
- [ ] No arrow crosses a box interior; endpoints sit on edges.
- [ ] No label lands on a box or on another label.
- [ ] White background rect; warm palette only; no shadow/gradient/filter.
- [ ] Ends with `</svg>`.

Run it: `python3 scripts/validate_svg.py <file>…` — or just let `d.save()` do it.

## Common anti-patterns

| Anti-pattern | Fix |
|---|---|
| Cold gray/blue boxes | Use the warm family fills (`#F5F4ED`, `#E1F5EE`, …) |
| Filled-triangle arrowhead | Use the single open-chevron marker |
| Drop shadow / gradient to add "depth" | Remove it — the style is flat |
| Straight arrow crosses a box | Orthogonal L-path around it; anchor on edges |
| Thick arrow to mean "important" | Keep 1.5px; signal importance with color |
| Label overlaps a node | Increase offset; add a `#FFFFFF` plate as a last resort |
| Arrow connects to a corner | Move to an edge midpoint |
| Arrow label wider than its arrow, overhanging into a box | Shorten the label, widen the gap, or negate `label_offset` to flip it to the emptier side |
| Legend overlaps a bottom-row node | Grow the canvas ~40px for a legend row, or move the legend to an empty corner |
| Dashed vs solid faked with a second marker shape | One chevron only; `dashed=True` carries "async / optional / realization" |
