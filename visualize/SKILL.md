---
name: visualize
description: Generate clean, self-contained SVG technical diagrams in one consistent house style — architecture, flowchart, sequence, ER, network topology, and more. Use for any request to draw, visualize, explain, or edit a diagram, chart, graph, or SVG.
---

# Visualize

Generate production-quality, self-contained SVG technical diagrams in one consistent house style: warm, flat, restrained, and built for technical clarity. Zero required third-party dependencies.

**The style in one line:** white canvas, warm cream/tinted rounded boxes, thin open-chevron arrows that recolor themselves, completely flat (no shadows, no gradients, no filters). Meaning comes from a small set of **color families** used as box fills.

Paths below are relative to this skill folder. Resolve the installed folder before importing helpers or running the validator from another working directory.

## Reference gallery — read one before you draw

The skill ships its own on-style reference diagrams, one per common type, at `assets/gallery/<type>.svg`. They are all generated with `svgkit`, all pass the validator, and are the ground truth for the look. **Before drawing, open the gallery entry that matches the request** and adapt it.

Index: `references/diagram-gallery.md` — 33 SVGs: 17 diagram examples, six explanatory compositions, six skeletons, and four showcases. The compositions in `assets/gallery/patterns/` cover feedback, funnels, mechanism comparisons, parallel pipelines, annotated charts, and qualitative axes. Notation guidance lives in `references/diagram-types.md`.

## Reading order

- **Core** (always relevant): `references/style.md` → `references/svg-cookbook.md`
- **Per-task**: `references/diagram-types.md` + `references/layout-patterns.md`
- **Diagnostic**: `references/svg-layout-best-practices.md`
- **Validation CLI and coverage**: `references/validation.md`
- **Design heuristics**: `references/shape-vocabulary.md`
- **Conditional**: `references/product-colors.md` (when brand treatment matters); `references/product-colors-azure.md` (Azure naming and boundaries)

## Workflow

1. **Understand the request** — Identify the entities, relationships, and the question the diagram should answer. Choose the notation using `references/diagram-types.md` and the composition using `references/layout-patterns.md`. Preserve the actual payload direction, conditions, and data; product names alone do not determine the architecture.
2. **Plan the layout** — Pick a viewBox (width ~680–760 is typical), 40px margins, 56px two-line boxes, ≥56px vertical gaps. For a minimal scaffold, start from `assets/gallery/skeletons/<type>.svg` instead of the full gallery entry. For anything non-trivial (≥6 nodes or multi-layer) read `references/svg-layout-best-practices.md`. If the request is a trust-boundary split, a numbered recipe, an allow/deny decision chain, a repeating scope, or any structure a flat graph hides, read `references/layout-patterns.md` and use its `svgkit` one-liners (`.step/.panel/.scope/.zone`). If the user wants a **mobile / narrow** version, re-lay-out per `references/layout-patterns.md` §10 (a separate `<name>_mobile.svg`).
3. **Assign color families by meaning** — Neutral cream for plumbing; **Green** for the primary / happy path / retrieval; **Purple** for an alternate or parallel branch; **Terracotta** for warnings / limitations / failure; **Amber** for a highlighted special module. Exact tokens: `references/style.md`. **Default to fewer families** — one accent + Neutral often beats three; see the Restraint subsection in `references/style.md` and the tint-within-family technique before reaching for a second family. Per-type guidance: `references/diagram-types.md`. Shape choices: `references/shape-vocabulary.md`. Product icons (optional): `references/product-colors.md`.
4. **Write the SVG** — With Python 3.10+, use **`svgkit`** (`references/svg-cookbook.md` §0) for estimated text sizing, edge anchors, layer order, and the standard SVG structure. Otherwise adapt a complete gallery SVG or skeleton directly.
5. **Save SVG** — Default to the working directory, or the path the user gave (`--output /path/` or `输出到 /path/`). Semantic kebab-case filename.
6. **Validate.** `d.save()` writes the SVG, reports findings, and raises `svgkit.ValidationError` for hard failures; the file remains available for inspection. Fix failures and review warnings. For manual SVG or a batch, run `python3 scripts/validate_svg.py --strict -q <file-or-directory>`. Files, recursive directories, quoted globs, and JSON reports are supported. See `references/validation.md` for the CLI, findings, and geometry limits.
7. **Inspect the rendered result** when a browser renderer is available. Read every label at the intended display size and trace each connection. Check alignment, arrowheads hidden by shapes, container header clearance, and legend spacing; XML and geometry checks do not prove these are visually correct.

> A worked example shipped with the skill: `assets/samples/hero.svg` (a RAG pipeline) — open it to see every token in context.

## Single style

One style only — see `references/style.md`. No `-s` flag, no second theme, no variants.

## The non-negotiables

What makes the output look right. **Exact tokens (every hex value, the marker XML, the type scale) live in `references/style.md` — that is the single source of truth; don't re-copy values here.** `svgkit` (below) bakes all of these in.

- **Size boxes from their labels.** Use the text-width estimate in `references/style.md`, including CJK glyphs, and verify the rendered fit. Equal peers can share a common width. Data marks keep their represented values; move their labels if needed.
- **Locked type scale.** Two sizes only — 14 (titles, weight 500) and 12 (rest); one optional 15–16 heading. Labels in sentence case (or natural Chinese).
- **Warm palette, colors as fills.** Five families (Neutral / Green / Purple / Terracotta / Amber) used as box fills for meaning. Values: `references/style.md`.
- **One arrow marker** — the open chevron that recolors per line via `context-stroke`; lines 1.5px, round caps, colored with a family LINE color. Encode meaning with **color** and, sparingly, **dashing** (`dashed=True` for returns, async / optional edges, and UML realization — `«implements»`, `«include»`, `«extend»`, `uses`) — never by swapping the head shape or thickening the line. Define each line meaning in the legend.
- **White background**, flat — no shadows, gradients, filters, or blur.
- **Self-contained** — font inline in `<style>`, no `@import`, no remote `url()/href/src`. `<title>`+`<desc>` first. Always end with `</svg>`.
- **Clean presentation attributes** (`fill="…"`), not a duplicated `style="…"`.
- **Legend** whenever 2+ families or 2+ arrow meanings appear.
- **Explain visually.** Use light, unheaded leaders for side notes; matched inputs and baselines for comparisons; and scaled marks for quantities. Label illustrative data and keep real measurements faithful to their source. Recipes and examples: `references/layout-patterns.md`.

## SVG generation

Use the complete runnable example and API in `references/svg-cookbook.md`. `Diagram.raw()` supports custom marks on named layers; panel backgrounds belong behind connectors, and fixed-size chart marks keep their represented values.

`d.save()` validates the file it writes. Inspect failures, fix their causes, and review any unsupported geometry in a renderer. A clean report does not establish that the content or reading order is correct.

## Layout Essentials

- Spacing: ≥40–75px between nodes horizontally, ≥56–60px vertically (connector lives in the gap), 40px margin. Snap coordinates to integers.
- Equal peers may share the largest computed box width. Align vertical chains by their centers, not their left edges; auto-sized labels otherwise produce slanted connectors. Compact matrix cells and unconnected parallel choices can use smaller gaps.
- Arrows anchor on box **edges**, never centers; orthogonal L-paths for branches and crossings; only the arriving segment carries the marker.
- Draw shared branch/merge rails without arrowheads. Put one arrowhead at each actual destination. Keep feedback rails clear of both boxes and unrelated success paths.
- Text: title 14/500, sub 12/400, captions 12. Centered text uses `text-anchor="middle" dominant-baseline="central"`.
- Arrow labels: usually ≤3 words, offset 6–15px. If text approaches a neighboring node, shorten it, widen the gap, or change the label side (`label_offset=-8`). A white plate may clear a crossing line; it cannot repair text over a node.

Full routing, spacing, and the validation checklist: `references/svg-layout-best-practices.md`.

## Output

Default: `./[name].svg`. Custom: `--output /path/` or `输出到 /path/`. Always tell the user the SVG path.

## Semantic checks

Use the relevant notes in `references/diagram-types.md`: RAG generation needs the question and retrieved context; memory reads need a query; state events must agree with their source states; comparisons use the same criteria and evidence; parallel layout must preserve actual dependencies. Treat gallery content as an adaptable example, not a universal product architecture.
