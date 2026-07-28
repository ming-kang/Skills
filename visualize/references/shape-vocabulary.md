# Shape & Color Vocabulary

How to map meaning onto the page in the one house style. Read with `references/style.md` (exact tokens) and `references/svg-cookbook.md` (snippets).

The core idea: **meaning is carried by COLOR FAMILY, not by ornament.** Boxes are simple flat rounded rectangles; you tell things apart by their tint and label, not by gradients, double borders, drop shadows, or icons.

## Color families = semantic roles

Pick a family by what a node *means*, and stay consistent across the diagram.

| Role in the diagram | Family | Box fill / stroke |
|---|---|---|
| Default node, plumbing, "just a step" | **Neutral** | `#F5F4ED` / `rgba(31,30,29,0.3)` |
| Primary / happy path, success, retrieval, "the good way" | **Green** | `#E1F5EE` / `#0F6E56` |
| Alternate path, parallel branch, secondary option | **Purple** | `#EEEDFE` / `#534AB7` |
| Warning, limitation, failure, bottleneck, "the problem" | **Terracotta** | `#FAECE7` / `#993C1D` |
| Highlight, special module, the thing to look at | **Amber** | `#FAEEDA` / `#854F0B` |

Use 2–4 families per diagram, no more — beyond that it reads as noise. When 2+ families appear, add a legend. Full text/sub colors per family: `references/style.md`.

## Shapes (kept few and flat)

A small, honest set. Render every one flat with a hairline `0.5` stroke — no gradients, no shadows, no icon clip-art.

| Concept | Shape | How to draw it |
|---|---|---|
| Process / step / service / component / **LLM** / **agent** / **tool** | **Rounded rect** | `rx="8"`, family fill. The default for almost everything — distinguish by label + family. |
| Group / layer / boundary | **Dashed container** | `rx="14"`, `fill="none"`, `stroke-dasharray="4 3"`, label top-left. |
| Region / section panel | **Solid panel** | `rx="20"`, `fill="#F5F4ED"`. |
| Decision | **Diamond** | Flowcharts only; family stroke, two labeled exits. |
| Datastore / vector store / DB | **Cylinder** *or* a labelled rounded rect | A labelled rect is often cleaner; use a cylinder when the "storage" read matters. |
| Point / item / actor | **Circle** | `r=5` scatter point (family fill+stroke); larger for an actor. |
| Sequence / alternating pattern | **Striped strip** | Row of small `14×18 rx3` rects alternating two LINE colors. |
| Vector / embedding | **Bars** | Stack of `rx3` rects, varying width + opacity, one family. |
| UML class / multi-compartment | **Three-compartment rect** | `class_box()` / `entity()`; hairline dividers, left-aligned attrs/methods. |
| UML use case | **Ellipse** | `usecase()`, min 140×60; centred label. Note: ellipses ARE collision obstacles. |

> Retired: "LLM = double-bordered rect", "Agent = hexagon with gradient", icon badges, folded-corner docs, browser chrome. In this style an LLM, an agent and a tool are all rounded rects; you read them by their **label** and **family** (e.g. agent core Neutral, tools Amber, final answer Green).

Raw fallback snippets for diamond / cylinder / actor (each with the `svgkit` helper it prefers): see `references/icons.md`.

## Arrows & their meaning

One marker only — the open chevron — recolored per line via `context-stroke` (definition in `references/style.md`). All lines are `1.5` wide with round caps; encode meaning with **color** and, sparingly, **dashing** — never thickness.

| Meaning | Line color | Style |
|---|---|---|
| Default flow / sequence | `#73726C` neutral | solid |
| Primary / retrieval / read | `#1D9E75` green | solid |
| Alternate branch | `#7F77DD` purple | solid |
| Warning / error path | `#C75B38` terracotta | solid |
| Async / optional / "also" | match the family | `stroke-dasharray="4 3"` |
| Leader / callout (not a real flow) | `#73726C` | `0.5` dashed + small `r=2` anchor dot |

```xml
<!-- standard flow arrow (chevron inherits the stroke) -->
<line x1="" y1="" x2="" y2="" stroke="#1D9E75" stroke-width="1.5"
      stroke-linecap="round" marker-end="url(#arrow)"/>

<!-- orthogonal route around a box; only the arriving segment carries the marker -->
<path d="M200,100 L200,250 L400,250" fill="none" stroke="#73726C"
      stroke-width="1.5" stroke-linecap="round" marker-end="url(#arrow)"/>

<!-- arrow label (offset-first; add a #FFFFFF plate only if it overlaps) -->
<text x="200" y="240" text-anchor="middle" font-size="12" fill="#3D3D3A">embeddings</text>
```

Branches split/merge with orthogonal L-paths. Two arrows meaning different things → legend with one line sample each.

## Legend Pattern

Include when 2+ families or 2+ arrow meanings appear.

```xml
<rect x="40" y="H-40" width="12" height="12" rx="3" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
<text x="58" y="H-34" dominant-baseline="central" font-size="12" fill="#3D3D3A">Retrieval (read)</text>
<rect x="200" y="H-40" width="12" height="12" rx="3" fill="#EEEDFE" stroke="#534AB7" stroke-width="0.5"/>
<text x="218" y="H-34" dominant-baseline="central" font-size="12" fill="#3D3D3A">Index (write)</text>
```

For arrow-meaning legends, draw a short line sample with the marker instead of a swatch.

## Worked patterns (which families to reach for)

- **Pipeline with a branch** — spine Neutral; the two branches Green and Purple; merge to Neutral; outcome Green. (`assets/gallery/data-flow.svg`)
- **Comparison of approaches** — cell fill carries the verdict: Terracotta for losing cells, Green for winning, Amber for mixed; header row in titles. (`assets/gallery/comparison.svg`)
- **Decision flow** — neutral steps; an Amber decision diamond; the failure branch Terracotta, routed back around the box. (`assets/gallery/flowchart.svg`)
- **Agent loop** — intake/reasoning Neutral & Purple; tools Amber; the answer Green; the feedback arrow Terracotta, called out in the legend. (`assets/gallery/agent-loop.svg`)
