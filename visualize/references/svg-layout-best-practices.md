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
- **A label must be shorter than the arrow it rides.** The gap between neighbouring boxes is often only ~40px, but a few words of text easily exceed that — a centered label wider than its arrow spills into the boxes on both ends. When the natural wording is too long, either shorten it (`top-k chunks` → `top-k`) or widen the gap so the arrow is long enough to carry it. Never let a label overhang into an adjacent box.

## 4. Collision / clearance model (DRC pass)

Borrow the mental model from EDA or game collision checks: every visible item gets a simple bounding object, then the diagram must pass a design-rule check before export.

- **Obstacle objects**: solid rects / ellipses / circles / polygons / filled paths ≥70×30, including nodes, decision diamonds, use-case ellipses, datastores, panels, and large custom art.
- **Non-obstacles**: dashed containers, `fill="none"` frames, tiny chips/cells/swatches <70 wide or <30 tall, and panels larger than 70% of the viewBox.
- **Text objects**: each `<text>` run counts as its own box. Text may live inside its host box; outside text must not touch nodes, other labels, or arrow strokes unless a white plate protects it.
- **Arrow objects**: each routed segment is a stroke object. A segment may touch its endpoint box edge, but must not pass through any obstacle interior.
- **Clearance**: solid sibling obstacles keep at least **8px** of air. Normal node-to-node gaps remain much larger: 40–75px horizontally and 56–60px vertically.
- **Paint order**: no filled shape may be painted after text it overlaps. Use the house z-order so color blocks never cover labels.

This is a check pass, not an automatic router. If a rule fails, fix the layout: move boxes, widen gutters, shorten labels, add a white label plate, or route an orthogonal L-bend through empty space.

## 5. Self-check pass (run it before finalizing)

This is an explicit pass, not a vibe. After placing everything, walk the diagram:

- **Box vs box** — no two solid sibling boxes overlap; keep at least 8px clearance.
- **Arrow vs box** — trace each arrow path against every obstacle; reroute straight hits as orthogonal L-bends. Anchor endpoints on edges.
- **Text vs box** — every label fits its host box, no caption sits on a box edge, and outside labels do not touch nodes.
- **Label vs label** — no two arrow labels overlap; nudge offsets or stagger by 20px.
- **Label vs arrow** — every arrow label is shorter than its arrow segment and does not sit on a stroke unless it has a white plate.
- **Legend vs node** — the legend row clears every node; if the bottom row of nodes runs into it, grow the canvas ~40px or move the legend to an empty corner.
- **Paint order** — containers → arrows → plates → boxes → box text → labels → legend; never paint a color block after text it would cover.

The validator (`scripts/validate_svg.py`) automates the DRC pass: paint-order occlusion, sibling obstacle spacing, arrow-vs-obstacle crossings, text fit, text-vs-node/label/arrow collisions, and box bounds vs the viewBox. Run it; fix anything it flags before declaring done.

## 6. Z-order (SVG render order; top of file = back)

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

## 7. The flat rule

- **No** drop shadows, gradients, `<filter>`s, or blur. Ever.
- Hairline box strokes (`0.5`), 1.5px round-cap lines, open-chevron heads.
- Warm palette only (`references/style.md`) — no cold gray/blue Tailwind values.
- Self-contained: inline font in `<style>`, no `@import`, no remote `url()/href/src`.

## Pre-export checklist

- [ ] `<title>` + `<desc>` are the first children.
- [ ] Every box width was computed from its text (CJK ≈ 2× Latin); nothing clips.
- [ ] Only two font sizes (14 / 12); labels in sentence case.
- [ ] Exactly one `<marker id="arrow">` in `<defs>`; every `marker-end` references it.
- [ ] White background rect; nothing relies on a page background.
- [ ] Box fills/strokes/text use the family tokens; arrows use family LINE colors.
- [ ] No solid sibling obstacles overlap; tight pairs have at least 8px clearance.
- [ ] No arrow crosses a box interior; endpoints sit on edges.
- [ ] Labels ≤3 words; plates only where needed.
- [ ] Every arrow label is shorter than its arrow — no overhang into a neighbouring box or unplated arrow stroke.
- [ ] No filled shape is painted after text it overlaps.
- [ ] Legend clears all nodes — canvas is tall enough for a legend row at the bottom.
- [ ] Legend present when 2+ families or 2+ arrow meanings appear.
- [ ] Flat: no shadow/gradient/filter; strokes 0.5 (boxes) / 1.5 (lines).
- [ ] Ends with `</svg>`. Passes `python3 scripts/validate_svg.py`.

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
| Arrow label wider than its arrow, overhanging into a box | Shorten the label, or widen the gap so the arrow carries it |
| Legend overlaps a bottom-row node | Grow the canvas ~40px for a legend row, or move the legend to an empty corner |
