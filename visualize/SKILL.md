---
name: visualize
description: Generate clean, self-contained SVG diagrams in one consistent house style.
disable-model-invocation: true
---

# Visualize

Generate production-quality, self-contained SVG technical diagrams in one consistent house style: warm, flat, restrained, and built for technical clarity. Zero required dependencies.

**The style in one line:** warm paper canvas, cream/tinted rounded boxes, thin open-chevron arrows that recolor themselves, completely flat (no shadows, no gradients, no filters). Meaning comes from a small set of **color families** used as box fills.

## Reference gallery — read one before you draw

The skill ships its own on-style reference diagrams, one per common type, at `assets/gallery/<type>.svg`. They are all generated with `svgkit`, all pass the validator, and are the ground truth for the look. **Before drawing, open the gallery entry that matches the request** and adapt it.

Index with a one-line description of each: `references/diagram-gallery.md` — one reference diagram per supported type (fourteen standard types), plus the decision-ladder compositing-pattern example and the `data-flow_mobile.svg` narrow re-layout variant. The full list of supported types with layout rules lives in `references/diagram-types.md`.

## Workflow

1. **Understand the request** — Identify the diagram type (architecture, data flow, flowchart, agent architecture, memory architecture, sequence, comparison, mind map, ER, state machine, network, class, use case, timeline/gantt; full per-type rules in `references/diagram-types.md`) and the entities / relationships.
2. **Plan the layout** — Pick a viewBox (width ~680–760 is typical), 40px margins, 56px two-line boxes, ≥56px vertical gaps. For anything non-trivial (≥6 nodes or multi-layer) read `references/svg-layout-best-practices.md`. If the request is a trust-boundary split, a numbered recipe, an allow/deny decision chain, a repeating scope, or any structure a flat graph hides, read `references/layout-patterns.md` and use its `svgkit` one-liners (`.step/.panel/.scope/.zone`). If the user wants a **mobile / narrow** version, re-lay-out per `references/layout-patterns.md` §10 (a separate `<name>_mobile.svg`).

   **Quick rule**: simple pipeline (≤5 nodes) → skip to step 3; anything else → read both layout files before drawing.
3. **Assign color families by meaning** — Neutral cream for plumbing; **Green** for the primary / happy path / retrieval; **Purple** for an alternate or parallel branch; **Terracotta** for warnings / limitations / failure; **Amber** for a highlighted special module. Exact tokens: `references/style.md`. **Default to fewer families** — one accent + Neutral often beats three; see the Restraint subsection in `references/style.md` and the tint-within-family technique before reaching for a second family. Per-type guidance: `references/diagram-types.md`. Shape choices: `references/shape-vocabulary.md`. Product icons (optional, **at most 1-2 per diagram** — cold colors, will trip validator if overused): `references/product-colors.md`.
4. **Write the SVG** — If `python3` is available, build it with the **`svgkit` helper** (`references/svg-cookbook.md` §0): you write the layout and it computes box widths from the text, anchors arrows on edges, and guarantees the marker / z-order / closing tag. Otherwise assemble the skeleton and snippets from the cookbook by hand (Python list method, one `lines.append(...)` per line so the file cannot be truncated mid-tag).
5. **Save SVG** — Default to the working directory, or the path the user gave (`--output /path/` or `输出到 /path/`). Semantic kebab-case filename.
6. **Self-check pass before declaring done** — trace every arrow against every box (reroute straight hits as L-bends), confirm no label overlaps, confirm no text clips its box. Run `python3 scripts/validate_svg.py <file>` if available.

> A worked example shipped with the skill: `assets/samples/hero.svg` (a RAG pipeline) — open it to see every token in context.

## Single style

One style only — see `references/style.md`. No `-s` flag, no second theme, no variants.

## The non-negotiables

What makes the output look right. **Exact tokens (every hex value, the marker XML, the type scale) live in `references/style.md` — that is the single source of truth; don't re-copy values here.** `svgkit` (below) bakes all of these in.

- **Size every box from its text — compute, don't guess.** Text overflow is the #1 failure; the width is measured from the label (CJK ≈ 2× Latin — critical for Chinese), not eyeballed. Exact formula in `references/style.md`; `svgkit.node()` and the validator's text-fit check both apply it.
- **Locked type scale.** Two sizes only — 14 (titles, weight 500) and 12 (rest); one optional 15–16 heading. Labels in sentence case (or natural Chinese).
- **Warm palette, colors as fills.** Five families (Neutral / Green / Purple / Terracotta / Amber) used as box fills for meaning. Values: `references/style.md`.
- **One arrow marker** — the open chevron that recolors per line via `context-stroke`; lines 1.5px, round caps, colored with a family LINE color.
- **White background**, flat — no shadows, gradients, filters, or blur.
- **Self-contained** — font inline in `<style>`, no `@import`, no remote `url()/href/src`. `<title>`+`<desc>` first. Always end with `</svg>`.
- **Clean presentation attributes** (`fill="…"`), not a duplicated `style="…"`.
- **Legend** whenever 2+ families or 2+ arrow meanings appear.

## SVG Generation Method

**Default — the `svgkit` helper (zero third-party deps, `python3` stdlib only).** It does the boring math so you don't guess: box widths from text, edge-anchored arrows, automatic z-order, the single marker, white background, `<title>`/`<desc>`, and a guaranteed `</svg>`. You write the layout; it writes correct markup. Full API and a worked example: `references/svg-cookbook.md` §0.

```python
python3 << 'EOF'
import sys; sys.path.insert(0, 'scripts')   # path to the skill's scripts/ dir
from svgkit import Diagram
d = Diagram(760, 240, title="RAG pipeline", desc="A query reaches the retriever.")
q = d.node(40, 100, "Query", "user question")
r = d.node(d.right_of(q, 56), 100, "Retriever", "top-k", family="green")
d.arrow(q.right, r.left, color="green", label="vector")
d.save("rag-pipeline.svg")
EOF
```

Use `d.raw(svg, layer=...)` for custom art (scatter points, patch grids, vector bars) that falls outside the box/arrow/container/legend vocabulary.

**Fallback — the Python list method** (no `python3`, or full manual control). Append one line per element so the file cannot be truncated mid-tag:

```python
python3 << 'EOF'
lines = []
lines.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 460" width="760" height="460" role="img">')
lines.append('  <title>...</title>')
lines.append('  <desc>...</desc>')
lines.append('  <style>text { font-family: ... }</style>')
lines.append('  <defs>')  # the single open-chevron marker
lines.append('  </defs>')
lines.append('  <rect width="760" height="460" fill="#FFFFFF"/>')
# one append per element: containers, then arrows, then boxes+text, then legend
lines.append('</svg>')
open('output.svg', 'w', encoding='utf-8').write('\n'.join(lines))
print("SVG generated")
EOF
```

**Z-order** (write back to front): background → containers → arrows → arrow-label plates → boxes → box text → arrow-label text → legend. (`svgkit` does this for you; the fallback must order appends this way.)

**Common pitfalls**: unquoted attrs (`fill=#fff` → `fill="#ffffff"`); missing `text-anchor="middle"`; comma-less path coords (`L 290220` → `L 290,220`); running a straight arrow *through* a box (route an L-path around it); using a filled-triangle arrowhead instead of the open chevron; cold gray/blue colors instead of the warm palette.

**Error recovery**: first error → targeted fix; second → switch method; third → stop and report. Never retry the same failing approach.

## Layout Essentials

- Spacing: ≥40–75px between nodes horizontally, ≥56–60px vertically (connector lives in the gap), 40px margin. Snap coordinates to integers.
- Arrows anchor on box **edges**, never centers; orthogonal L-paths for branches and crossings; only the arriving segment carries the marker.
- Text: title 14/500, sub 12/400, captions 12. Centered text uses `text-anchor="middle" dominant-baseline="central"`.
- Arrow labels: ≤3 words; midpoint offset 6–15px; add a `#FFFFFF` background plate only if it would overlap a line or box.

Full routing, spacing, and the validation checklist: `references/svg-layout-best-practices.md`.

## Output

Default: `./[name].svg`. Custom: `--output /path/` or `输出到 /path/`. Always tell the user the SVG path.

## Domain Shortcuts

Recognize these on sight:

```
RAG Pipeline       Query → Embed → VectorSearch → Retrieve → LLM → Response
Agentic RAG        adds an Agent loop with Tool use between Query and LLM
Agentic Search     Query → Planner → [Search/Calc/Code] → Synthesizer → Response
Mem0 Memory        Input → Memory Manager → [VectorDB + GraphDB] / [Retrieve+Rank] → Context
Agent Memory       Sensory → Working → Episodic → Semantic → Procedural
Multi-Agent        Orchestrator → [SubAgent A/B/C] → Aggregator → Output
Tool Call Flow     LLM → Tool Selector → Execution → Parser → LLM (loop)
```
