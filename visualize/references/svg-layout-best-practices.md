# Layout and rendered review

Use [style.md](style.md) for tokens and [validation.md](validation.md) for the CLI and supported geometry. These are layout decisions that automated checks cannot make for you.

## 1. Canvas and alignment

Start around 680–800px wide with 40px outside margins; grow the canvas for the content. Ordinary two-line nodes are 56px high. Estimate their text width, including Chinese glyphs, then give equivalent peers the largest required width.

Align the centers of a vertical chain. `col()` aligns left edges and does not center differently sized nodes. Start with 40–75px horizontal gaps and 56–60px vertical gaps for ordinary labeled flows. Compact chart marks and repeated miniature mechanisms can use smaller gaps if their labels and arrowheads remain readable.

Reserve space for headings, container labels, side notes, and the full legend before placing the body. Keep the lowest shape at least 24px above a footer divider. A narrow version needs a new layout with the same graph, not merely a smaller display width.

## 2. Route through clear gutters

- Anchor on node edges. Use state-circle boundaries and activation-bar sides where applicable.
- Put feedback routes outside the main spine. Keep unrelated returns separate.
- Draw shared trunks once, without an arrowhead; branch heads belong at actual destinations.
- Route through row or column gutters before allowing a crossing. Make junctions intentional and unambiguous.
- Use unheaded, light leaders for annotations. A note linked to a node is not another processing stage.

Trace every edge from source to destination after layout changes. Moving parallel panels must not turn them into sequential stages or reverse a payload's direction.

## 3. Fit labels without hiding the diagram

Use short 12px connector labels, usually offset 8–12px. Positive `label_offset` is right of a vertical segment or above a horizontal one; negative is left or below. `lpath()` puts the label on its longest segment.

If a label overlaps a node, shorten it, widen the gap, or change sides. A white label plate may clear a crossing line, but it cannot repair insufficient room or text over a node. Long explanations belong in a side note. Keep the original font scale; move labels outside fixed-size data marks when necessary.

Curved nodes need corner clearance as well as enough total width. Use the helper's automatic sizing as a starting point and check actual glyphs in the renderer. Estimated metrics are not a guarantee of text fit.

## 4. Validate, then inspect the image

`d.save()` validates its output and raises `ValidationError` on hard failures. For batches or manual SVG:

```bash
python SKILL_DIR/scripts/validate_svg.py --strict -q output-directory/
```

See [validation.md](validation.md) for severity, JSON output, CSS coverage, and unsupported constructs. A warning about skipped geometry means that geometry has not been checked.

At the intended display size:

1. Read every label, including long Chinese text, subscripts, and legends.
2. Follow the main path, then each branch and return. Confirm payloads and conditions match their arrows.
3. Check that arrowheads remain visible, header bands clear their text, and panel backgrounds stay behind connectors.
4. Compare peer alignment, emphasis, and density. Inspect notes and lower rows as carefully as the main nodes.
5. Check chart ticks, point positions, counts, and represented widths against their data.

Generating screenshots or passing automated text checks is not the same as looking at the rendered result.

## 5. Paint order

Background → containers and panel backgrounds → connectors → label plates → nodes → node text → free labels → legend.

`svgkit` maintains this order. With raw SVG, mark intentional group shapes `panel`/`container`, ordinary obstacles `node`, and fixed-size chart marks `data-mark`. These roles explain intent to the validator; they do not establish a correct layout or exempt canvas overflow.
