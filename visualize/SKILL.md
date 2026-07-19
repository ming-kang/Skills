---
name: visualize
description: >
  Generate clean, self-contained SVG technical diagrams in one house style
  (architecture, data-flow, flowchart, sequence, ER, class, state, network,
  comparison, mind-map, timeline/Gantt, agent/memory diagrams). Use whenever
  the user asks to draw, diagram, visualize, sketch a system, or export an
  SVG figure — even if they do not say "visualize".
disable-model-invocation: true
---

# Visualize

Generate production-quality, self-contained SVG technical diagrams in one consistent house style: warm, flat, restrained, technical clarity. Zero required dependencies.

**The style in one line:** warm paper canvas, cream/tinted rounded boxes, thin open-chevron arrows that recolor themselves, completely flat (no shadows, no gradients, no filters). Meaning comes from a small set of **color families** used as box fills.

## Progressive loading — read only what you need

Do **not** load every reference file. Token cost and latency scale with what you open.

| Situation | Read |
|---|---|
| **Fast path** — linear pipeline / simple row-col, ≤5 nodes, no special shapes | This file only. Use `svgkit` (`row`/`col` + `chain` + `fit`/`save`). |
| Standard type (architecture, sequence, ER, …) | Matching `assets/gallery/<type>.svg` (index: `references/diagram-gallery.md`) |
| Complex routing, ≥6 nodes, or multi-layer | + `references/svg-layout-best-practices.md` |
| Trust boundary / steps / decision ladder / scope / panel / mobile re-layout | + `references/layout-patterns.md` |
| Per-type notation (UML compartments, cardinality, lifelines) | + `references/diagram-types.md` |
| Exact hex tokens without `svgkit`, or hand-editing markup | + `references/style.md` |
| Shape meaning / dashed vs solid arrows | + `references/shape-vocabulary.md` |
| Snippet paste / full API list | + `references/svg-cookbook.md` |

Gallery files are the ground truth for the look — when you open one, adapt it; do not re-derive the style from prose.

## Workflow

1. **Classify** — diagram type + entities/relationships. Prefer the fast path when it fits.
2. **Layout plan** — viewBox width ~680–760 typical; 40px margins; 56px two-line boxes; ≥56px vertical gaps. Prefer `d.row` / `d.col` over hand-picked x/y. For non-trivial graphs use `d.connect` / `d.fanout` so edges land on box sides and diagonals become L-paths.
3. **Color by meaning** — Neutral cream = plumbing; **Green** = primary/happy path/retrieval; **Purple** = alternate/parallel; **Terracotta** = warning/failure; **Amber** = highlight. **Default to fewer families** — one accent + Neutral often beats three. Sibling stages of one path: same family with `opacity=0.9/0.55/0.4` rather than a second family.
4. **Build with `svgkit`** (Python 3 stdlib only) — sizes boxes from text (CJK ≈ 2× Latin), owns marker/z-order/`</svg>`, auto-grows canvas on `save()`. Hand-write XML only if Python is unavailable.
5. **Save** — default working directory or the path the user gave; semantic kebab-case name. Tell the user the path.
6. **Validate** — `python3 scripts/validate_svg.py <file>`. Fix anything it flags before declaring done.

> Worked sample: `assets/samples/hero.svg` (RAG). Minimal `svgkit` parity sample: `assets/samples/svgkit-rag.svg`.

## Single style

One style only — see `references/style.md`. No `-s` flag, no second theme, no variants.

## Non-negotiables

Exact tokens live in `references/style.md` (single source of truth). `svgkit` bakes them in.

- **Size boxes from text** — never guess width; text overflow is the #1 failure. `svgkit.node()` measures labels.
- **Locked type scale** — 14/500 titles, 12/400 everything else; optional one 15–16 heading. Sentence case (or natural Chinese).
- **Warm palette, colors as fills** — five families; flat white canvas; hairline 0.5 box strokes; 1.5 round-cap lines.
- **One open-chevron marker** — recolors via `context-stroke`; no filled triangles.
- **Self-contained** — font in `<style>`, no `@import`/remote assets; `<title>`+`<desc>` first; ends with `</svg>`.
- **Legend** when 2+ families or 2+ arrow meanings appear.
- **No** shadows, gradients, filters, blur.

## SVG generation — default `svgkit`

```python
python3 << 'EOF'
import sys; sys.path.insert(0, 'scripts')  # skill's scripts/ dir
from svgkit import Diagram

d = Diagram(760, 200, title="RAG pipeline", desc="Query to grounded answer.")
boxes = d.row([
    {"title": "Query", "sub": "user question"},
    {"title": "Retriever", "sub": "top-k", "family": "green"},
    {"title": "LLM", "sub": "answer", "family": "purple"},
], x=40, y=80, gap=56)
d.chain(boxes, labels=[None, "context"])          # edge-anchored connectors
d.legend([("green", "retrieval"), ("purple", "generation")])
d.save("rag-pipeline.svg")                        # fit() grows canvas automatically
print("SVG generated")
EOF
```

**Prefer these helpers (quality + speed):**

| Helper | When |
|---|---|
| `row` / `col` | Equal-gap pipelines and stacks — avoid hand math |
| `chain(boxes, labels=…)` | Connect consecutive boxes on a spine |
| `connect(a, b, …)` | Any pair — picks edges; diagonals → orthogonal L-path |
| `fanout(parent, children, …)` | One-to-many branch with a shared bus |
| `arrow` / `lpath` / `curve` | Only when you need a precise anchor or free path |
| `dashed=True` | Async, optional, dependency, «include»/«implements» |
| `opacity=…` on `node` | Tint-within-family sibling stages |
| `fit()` / `save()` | Canvas clears content + legend (default on save) |
| `raw(svg, layer=…)` | Custom art outside the primitive set |

Full API: `references/svg-cookbook.md` §0.

**Fallback — Python list method** (no `python3`, or full manual control). One `lines.append(...)` per element so the file cannot truncate mid-tag. Z-order: background → containers → arrows → plates → boxes → box text → labels → legend. End with `</svg>`.

**Error recovery:** first failure → targeted fix; second → switch method; third → stop and report. Never retry the same failing approach.

## Layout essentials

- Spacing: ≥40–75px horizontal gaps, ≥56–60px vertical, 40px margin; integer coordinates.
- Arrows on **edges**, never centers; use `connect`/`fanout` so this is automatic.
- Never run a straight segment through a box — `connect(route="auto")` L-bends diagonals.
- Arrow labels ≤3 words; shorter than the segment they ride.
- Reserve room for the legend — `legend()` + `save()` handles this when using `svgkit`.

Full checklist: `references/svg-layout-best-practices.md`.

## Output

Default: `./[name].svg`. Custom: `--output /path/` or `输出到 /path/`. Always report the SVG path.

## Domain shortcuts

```
RAG Pipeline       Query → Embed → VectorSearch → Retrieve → LLM → Response
Agentic RAG        adds an Agent loop with Tool use between Query and LLM
Agentic Search     Query → Planner → [Search/Calc/Code] → Synthesizer → Response
Mem0 Memory        Input → Memory Manager → [VectorDB + GraphDB] / [Retrieve+Rank] → Context
Agent Memory       Sensory → Working → Episodic → Semantic → Procedural
Multi-Agent        Orchestrator → [SubAgent A/B/C] → Aggregator → Output
Tool Call Flow     LLM → Tool Selector → Execution → Parser → LLM (loop)
```
