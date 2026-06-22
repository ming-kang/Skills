# Diagram gallery — owned, on-style references by type

These are the skill's **own** reference diagrams, one per common diagram type, all in the single house style and all generated with `svgkit` (so they double as worked examples of the helper). They are license-clean — we drew them — and every file passes `scripts/validate_svg.py`. Read the one matching your task before drawing, then adapt.

Files live at `assets/gallery/<type>.svg`. Variants use a suffix, e.g. `data-flow_mobile.svg` for the narrow re-layout of the data-flow diagram.

| Type | File | Pattern it demonstrates |
|---|---|---|
| Architecture | `assets/gallery/architecture.svg` | Layered top-down: client → gateway → services → datastores; dashed service group; cylinders for stores; fan-out routed through row gutters. |
| Data flow | `assets/gallery/data-flow.svg` | Linear pipeline with every arrow labeled by data shape (stream / batch / query); read vs write legend. `data-flow_mobile.svg` is the narrow re-layout variant (`layout-patterns.md` §10). |
| Flowchart | `assets/gallery/flowchart.svg` | Decision **diamond** with yes/no branches and a terracotta feedback loop routed *around* the box (not through it). |
| Sequence | `assets/gallery/sequence.svg` | Actors over dashed **lifelines**; colored request/response messages; return arrows in neutral. |
| Comparison | `assets/gallery/comparison.svg` | Feature **matrix**; cell fill carries the verdict (green good / amber mixed / terracotta poor). |
| Mind map | `assets/gallery/mind-map.svg` | Central node with **curved (bezier) branches** to radial leaves; branch color = family. |
| Memory architecture | `assets/gallery/memory-architecture.svg` | Read/write split: manager writes to vector + graph stores, retrieval assembles context. |
| Agent loop | `assets/gallery/agent-loop.svg` | Large, dense, single-turn loop: intake → reasoning → tools → verify, with a feedback edge and a memory rail. Shows the style holding up at high information density. **Intentionally wide (1360×980) — a stress test, not a default canvas size.** |
| ER diagram | `assets/gallery/er-diagram.svg` | Three entities with header/attribute compartments; diamond relationships; cardinality labels `1` / `N`. |
| State machine | `assets/gallery/state-machine.svg` | Initial dot → states → decision diamond with guarded branches → final double circle. |
| Network topology | `assets/gallery/network-topology.svg` | Internet → firewall → core switch → internal hosts inside a dashed DMZ container. |
| Timeline / Gantt | `assets/gallery/timeline-gantt.svg` | Horizontal time axis (W1–W6) with category-colored `bar()` rows (Design → Develop → Test → Launch) and amber `diamond()` milestones. Shows the `bar` helper (h=28, under the obstacle floor) and the `.raw()` time-axis loop. |
| Class diagram | `assets/gallery/class-diagram.svg` | Three `class_box()` compartments (interface stereotype, abstract italic, attributes/methods). Inheritance and realization both expressed with the single open-chevron + `extends` / `«implements»` labels — the House-style UML prescription. |
| Use case | `assets/gallery/use-case.svg` | Two `actor()` figures outside a dashed system boundary, five `usecase()` ellipses inside, with dashed `«include»` / `«extend»` arrows routed through the row gutters around the ellipse obstacles. |
| Decision ladder | `assets/gallery/decision-ladder.svg` | Verdict-rails *compositing pattern* (`references/layout-patterns.md` §3), not a distinct diagram type — a chain of `.step()` checks between a green "Execute" bar and a terracotta "Blocked" bar; each gate allow-arrows up / deny-arrows down. |

## How these were made

All sixteen gallery SVGs (fifteen diagrams plus the `data-flow_mobile.svg` narrow variant) are drawn with the `svgkit` primitives — boxes / arrows / containers / legend, plus the shape helpers (`diamond`, `cylinder`, `lifeline`, `state_dot`, `entity`, `class_box`, `usecase`, `actor`, `step`, `panel`, `bar`), `.curve()` for the mind-map branches, `.scope()`/`.zone()` for frames/dividers, and `.raw()` for the occasional bespoke bit (matrix cells, turn-strip, plumbing rails, verdict rails). They double as worked examples of the helper.
