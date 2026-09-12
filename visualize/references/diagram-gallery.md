# Diagram gallery — owned, on-style references by type

These are the skill's **own** reference diagrams, one per common diagram type, all in the single house style and all generated with `svgkit` (so they double as worked examples of the helper). They are license-clean — we drew them — and every file passes `scripts/validate_svg.py`. Read the one matching your task before drawing, then adapt.

Files live at `assets/gallery/<type>.svg`. Variants use a suffix, e.g. `data-flow_mobile.svg` for the narrow re-layout of the data-flow diagram.

| Type | File | Pattern it demonstrates |
|---|---|---|
| Architecture | `assets/gallery/architecture.svg` | Layered top-down: client → gateway → services → datastores; dashed service group; cylinders for stores; fan-out routed through row gutters. |
| Data flow | `assets/gallery/data-flow.svg` | Linear pipeline with every arrow labeled by data shape (stream / batch / query); read vs write legend. `data-flow_mobile.svg` is the narrow re-layout variant (`layout-patterns.md` §10). |
| Flowchart | `assets/gallery/flowchart.svg` | Decision **diamond** with yes/no branches and a terracotta feedback loop routed *around* the box (not through it). |
| Sequence | `assets/gallery/sequence.svg` | Actors over dashed **lifelines**; colored messages, dashed returns, and a line-style legend. |
| Comparison | `assets/gallery/comparison.svg` | Feature **matrix**; cell fill carries the verdict (green good / amber mixed / terracotta poor). |
| Mind map | `assets/gallery/mind-map.svg` | Centered core loop with balanced **curved (bezier) branches**; one accent family for peer capabilities. |
| Memory architecture | `assets/gallery/memory-architecture.svg` | Purple writes and green reads through vector + graph stores; shared rails end at actual nodes, and retrieval produces a context card. |
| Agent loop | `assets/gallery/agent-loop.svg` | Intake → reasoning → tools → verify, with a separate dashed memory rail and a retry route above the finalization row. **Intentionally wide (1360×924): a dense reference rather than a default canvas size.** |
| ER diagram | `assets/gallery/er-diagram.svg` | Three entities with header/attribute compartments, orthogonal routes, diamond relationships, and `1` / `N` / `M` cardinality labels. |
| State machine | `assets/gallery/state-machine.svg` | Initial dot → states → decision diamond with guarded branches → final double circle. |
| Network topology | `assets/gallery/network-topology.svg` | Internet → firewall → core switch → application hosts; the firewall is outside a clearly labeled DMZ subnet. |
| Timeline / Gantt | `assets/gallery/timeline-gantt.svg` | W1–W6 column guides, aligned task bars, and amber milestones at exact week boundaries. Phase names and bar details have separate roles. |
| Class diagram | `assets/gallery/class-diagram.svg` | Three `class_box()` compartments (interface stereotype, abstract italic, attributes/methods). Inheritance and realization both expressed with the single open-chevron + `extends` / `«implements»` labels — the House-style UML prescription. |
| Use case | `assets/gallery/use-case.svg` | Two `actor()` figures outside a dashed system boundary, five `usecase()` ellipses inside, with dashed `«include»` / `«extend»` arrows routed through the row gutters around the ellipse obstacles. |
| Decision ladder | `assets/gallery/decision-ladder.svg` | Verdict-rails *compositing pattern* (`references/layout-patterns.md` §3), not a distinct diagram type — a chain of `.step()` checks between a green "Execute" bar and a terracotta "Blocked" bar; each gate allow-arrows up / deny-arrows down. |
| Sequence (frames) | `assets/gallery/sequence-frames.svg` | Alt/opt scope frames with both token and rejection outcomes, activation bars with visible edge-anchored arrowheads, and a solid/dashed line key. |

## How these were made

All 17 gallery SVGs use `svgkit` primitives, shape helpers, and a small amount of raw SVG for shared rails, grid lines, and legend line samples. Fourteen are standard diagram types; the remaining three show a decision ladder, sequence frames, and a narrow data-flow layout. The SVGs are self-contained and can be adapted without the repository's development tools.

---

## Skeletons — minimal starting points

Copy one as a starting scaffold instead of adapting the full gallery entry. Each skeleton is a compact, complete example of its notation and passes the validator clean. Replace the example labels, then recalculate widths and anchors.

Files live at `assets/gallery/skeletons/<type>.svg`.

| Type | File | What it shows |
|---|---|---|
| Architecture | `skeletons/architecture.svg` | A compact, centered Client → Service → Database stack with a cylinder |
| Data flow | `skeletons/data-flow.svg` | Three-node linear pipeline with a legend |
| Flowchart | `skeletons/flowchart.svg` | Start → Process → Decision with yes/no exits and a complete retry return |
| Sequence | `skeletons/sequence.svg` | Two lifelines; messages below the headers; dashed response and line key |
| Comparison | `skeletons/comparison.svg` | 2×2 feature matrix with verdict fills |
| State machine | `skeletons/state-machine.svg` | Initial dot → one state → final dot |

## Showcase samples

These four samples complete the 27 bundled SVG assets:

| File | Pattern it demonstrates |
|---|---|
| `assets/samples/hero.svg` | RAG query spine alongside an offline knowledge-base group; aligned vector-store connection and complete legend. |
| `assets/samples/sample-agent-loop.svg` | Chinese labels, an LLM decision, a tool call, and a feedback route in a compact composition. |
| `assets/samples/sample-comparison.svg` | Three aligned Chinese comparison rows with method, mechanism, and trade-off columns. |
| `assets/samples/svgkit-rag.svg` | A compact horizontal pipeline with mixed Chinese/English labels and space for connector captions. |
