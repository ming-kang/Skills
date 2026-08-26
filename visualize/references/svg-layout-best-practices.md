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

This is an explicit pass, and it is **code**. `d.save()` writes the SVG first and validates that exact file. Warnings print to stderr but remain non-fatal; any hard failure prints all details/fixes and raises `svgkit.ValidationError`, whose `.results` contains the complete structured result list. The failed artifact remains on disk. For hand-written SVG run `python3 scripts/validate_svg.py <file>…`; it accepts several files, exits 1 if any has a hard failure, and exits 0 for clean or warnings-only input. `-q` is completely silent when every file is clean and prints only warnings/failures otherwise.

| Contract | Check | Verdict | Fix |
|---|---|---|---|
| Valid UTF-8/XML, `<svg>` root, usable viewBox | file/XML/root/viewBox | fail | Repair syntax and use `viewBox="min-x min-y width height"`. |
| Non-empty `<title>` then `<desc>` as the first two element children | accessibility | fail | Move and populate both elements before `<style>`/`<defs>`. |
| No external or relative assets; only embedded `data:` or local `#id` targets; local URL references resolve; `xml-stylesheet` processing instructions are rejected | renderer-safe assets / URL references | fail | Inline assets/styles and correct every `url(#id)` / fragment reference. |
| IDs are unique; exactly one `<marker id="arrow">`; every element/inline/inherited marker longhand or shorthand targets it; stylesheet marker rules are rejected because selectors are not resolved | marker contract | fail | Remove duplicate IDs/markers and use `url(#arrow)` directly on the element or an inline/ancestor presentation style. |
| The first graphics child is an opaque white rect covering the full viewBox | white background | fail | Put the full-size `#FFFFFF` canvas rect immediately after `<defs>`, before diagram content. |
| No gradients, filters, `fe*`, blur, or shadow CSS | flat style | fail | Remove effects; use flat family fills and hairline strokes. |
| Ordinary solid shapes do not overlap or contain each other | box overlap | fail; ambiguous complex path is warn | Move nodes apart. Only an outer shape explicitly marked `data-role="panel"` or `data-role="container"` may intentionally contain nodes. |
| No arrow segment cuts through an obstacle | arrow collisions | fail; ambiguous complex path is warn | Route around nodes with an orthogonal path and anchor endpoints on edges. |
| Obstacles stay inside the viewBox | box bounds vs viewBox | fail | Grow `Diagram(w, h)` or reposition the shape. |
| Hosted node text fits; free labels miss nodes and each other | text fit / label vs box / label vs label | warn | Resize, shorten, widen the gap, or change signed `label_offset`. |
| Geometry was not silently guessed | unsupported text geometry / transforms | warn | Flatten transforms and replace positioned `<tspan>` runs with separate plain `<text>` elements before trusting collision checks. |
| Type scale, baseline, warm palette, and final `</svg>` follow the contract | type scale / text baseline / warm palette / closing tag | fail or warn as reported | Use 14/12 text, central baselines, family colors, and a complete closing tag. |

Shape intersections are outline-aware for convex and concave rect/polygon/path outlines plus sampled circles and ellipses, so overlapping bounding boxes alone do not create a hard failure. Filled paths use parsed `M/L/H/V/C/S/Q/T/A/Z` geometry and curve extrema; arrow collisions sample the real quadratic/cubic/arc trajectory instead of testing a fictional endpoint chord. When a filled path has no reliable single outline, an AABB hit is only a warning candidate. Effective fill and visibility follow SVG defaults, ancestors, presentation attributes, inline style, display/visibility, numeric or percentage alpha, and alpha carried by `rgba()` / 4- or 8-digit hex colors.

Containment is semantic, not heuristic: only explicit `data-role="panel"` / `data-role="container"` allows an outer shape to hold nodes. `svgkit` emits those roles plus `node-text`, `arrow-label`, `legend-label`, and `container-label` automatically. Add them to hand-written SVG when needed; they do not affect rendering.

Current geometry limits are deliberate and visible: an element under an XML `transform`, CSS `transform`, or individual `translate` / `rotate` / `scale` property (inline or inherited from an ancestor) is skipped by obstacle/text/arrow geometry checks and produces a warning. Because stylesheet selectors are not resolved, any stylesheet rule using those transform properties conservatively skips all obstacle/text geometry with an explicit warning. A `<text>` with any child/nested run (including wrapped or positioned `<tspan>`) is not flattened into a fictional line, so its text geometry is skipped with a warning. Dashed shapes, hidden/fully transparent paint, cells smaller than 70×30, and very broad backdrop shapes (>70% of a viewBox dimension) are not treated as obstacles. Treat every warning as something to inspect even though it does not raise `ValidationError`.

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

The items above the rule remain judgement calls. In particular, the validator does not prove that wording is concise, a legend is semantically sufficient, or every endpoint was chosen at the best edge anchor.

- [ ] Labels ≤3 words; sentence case; plates only where needed.
- [ ] Box fills/strokes/text use the family tokens; arrows use family LINE colors.
- [ ] Meaning carried by color and (sparingly) dashing — not by arrowhead shape or line thickness.
- [ ] Legend present when 2+ families or 2+ arrow meanings appear.
- [ ] Canvas has clear margins and a dedicated legend row; connector endpoints are deliberately anchored on edges.

---

Everything below is enforced by `scripts/validate_svg.py` (and therefore by `d.save()`), with the fail/warn severity shown in §4.

- [ ] Valid XML and viewBox; non-empty `<title>` + `<desc>` are the first two element children.
- [ ] IDs are unique; exactly one `<marker id="arrow">`; every marker reference targets it and every local URL reference resolves.
- [ ] No remote assets; a white rect covers the viewBox; no gradient, filter, blur, or shadow.
- [ ] Ordinary nodes do not overlap/contain one another; only explicit panel/container roles allow intentional nesting.
- [ ] No arrow crosses a known obstacle; no obstacle spills the viewBox.
- [ ] Text-fit, label-vs-box, and label-vs-label checks have no unreviewed warnings.
- [ ] Type scale is 14/12 (plus at most one 15–16 heading); baselines and warm palette have no unreviewed warnings.
- [ ] No unreviewed warning says transformed or `<tspan>` geometry was skipped.
- [ ] The file ends with `</svg>`.

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
