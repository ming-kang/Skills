# Diagram gallery

Open the example closest to the requested relationship, then adapt its content, widths, and routes. All 33 bundled SVGs are self-contained and generated with `svgkit`: 17 diagram examples, six explanatory compositions, six skeletons, and four showcases. They work without the repository's development tools.

Notation guidance is in [diagram-types.md](diagram-types.md); compositing recipes are in [layout-patterns.md](layout-patterns.md). Example content is illustrative. Preserve the actual system or data when adapting it.

## Diagram examples

| Diagram | Example | What to learn |
|---|---|---|
| Architecture | [architecture.svg](../assets/gallery/architecture.svg) | Aligned layers, grouped services, shared routing rails, and storage shapes. |
| Data flow | [data-flow.svg](../assets/gallery/data-flow.svg) | Producer-to-consumer payloads: stream, batch, and files. |
| Narrow data flow | [data-flow_mobile.svg](../assets/gallery/data-flow_mobile.svg) | The same graph rearranged as one vertical spine. |
| Flowchart | [flowchart.svg](../assets/gallery/flowchart.svg) | A decision with yes/no branches and a complete revision return. |
| Sequence | [sequence.svg](../assets/gallery/sequence.svg) | Simplified authorization-code redirects and token exchange; requests and returns have distinct line styles. |
| Sequence frames | [sequence-frames.svg](../assets/gallery/sequence-frames.svg) | `alt`/`opt` guards, activation bars, and an optional call requiring a valid token and permission. |
| Comparison | [comparison.svg](../assets/gallery/comparison.svg) | Fictional feature coverage with supported, planned, and unavailable statuses. |
| Mind map | [mind-map.svg](../assets/gallery/mind-map.svg) | Balanced curved branches and one accent for equivalent capabilities. |
| Memory architecture | [memory-architecture.svg](../assets/gallery/memory-architecture.svg) | Separate write and query-driven read paths through two stores. |
| Agent loop | [agent-loop.svg](../assets/gallery/agent-loop.svg) | Intake, tools, verification, memory, and a retry gutter. A deliberately dense 1360×924 example. |
| Entity relationship | [er-diagram.svg](../assets/gallery/er-diagram.svg) | Conceptual relationships, entity compartments, and explicit cardinalities. |
| State machine | [state-machine.svg](../assets/gallery/state-machine.svg) | A job lifecycle with meaningful events, guarded outcomes, retry, and a final state. |
| Network | [network-topology.svg](../assets/gallery/network-topology.svg) | Filtered ingress, a named subnet, and clearly placed boundary devices. |
| Timeline / Gantt | [timeline-gantt.svg](../assets/gallery/timeline-gantt.svg) | Durations and milestones derived from one week scale. |
| Class | [class-diagram.svg](../assets/gallery/class-diagram.svg) | Stereotypes, compartments, and labeled house-style inheritance/implementation. |
| Use case | [use-case.svg](../assets/gallery/use-case.svg) | Actors outside a boundary; routed include/extend relationships between ellipses. |
| Decision ladder | [decision-ladder.svg](../assets/gallery/decision-ladder.svg) | Ordered policy groups with final allow/deny exits, no-match continuation, and an explicit default. |

## Explanatory compositions

These six examples distill reusable design methods from the supplied visual references. They use the same palette and type scale as the rest of the skill.

| Example | Adapt it for |
|---|---|
| [feedback-pipeline.svg](../assets/gallery/patterns/feedback-pipeline.svg) | A primary sequence with a revision gutter and a local explanatory panel. |
| [annotated-funnel.svg](../assets/gallery/patterns/annotated-funnel.svg) | Successive filtering, retained counts, and aligned removal notes. Widths follow explicit illustrative data. |
| [mechanism-comparison.svg](../assets/gallery/patterns/mechanism-comparison.svg) | Matched input/output panels, miniature data shapes, and aligned comparison rows; includes Chinese text. |
| [parallel-pipelines.svg](../assets/gallery/patterns/parallel-pipelines.svg) | A shared source, repeated lane structure, and an explicit output merge. |
| [annotated-chart.svg](../assets/gallery/patterns/annotated-chart.svg) | Scaled ticks and points, a local callout, and a legend matching the plotted series. |
| [quadrant-map.svg](../assets/gallery/patterns/quadrant-map.svg) | Two qualitative dimensions with labeled regions and restrained emphasis. |

## Skeletons

Each is a complete SVG starting point. Replace its labels, recalculate sizes, and re-anchor the connections.

| Skeleton | Structure |
|---|---|
| [architecture.svg](../assets/gallery/skeletons/architecture.svg) | Client → service → database. |
| [data-flow.svg](../assets/gallery/skeletons/data-flow.svg) | Three stages with payload labels. |
| [flowchart.svg](../assets/gallery/skeletons/flowchart.svg) | Process, decision, completion, and retry. |
| [sequence.svg](../assets/gallery/skeletons/sequence.svg) | Two lifelines with request/return messages. |
| [comparison.svg](../assets/gallery/skeletons/comparison.svg) | A fictional two-by-two availability matrix. |
| [state-machine.svg](../assets/gallery/skeletons/state-machine.svg) | Initial marker, one state, final marker. |

## Showcase samples

| Sample | Structure |
|---|---|
| [hero.svg](../assets/samples/hero.svg) | A RAG query spine with both question and context reaching the LLM, plus offline indexing. |
| [sample-agent-loop.svg](../assets/samples/sample-agent-loop.svg) | Chinese tool-use loop with a direct final-answer branch. |
| [sample-comparison.svg](../assets/samples/sample-comparison.svg) | Three Chinese request-processing rows with success, pending, and failure outcomes. |
| [svgkit-rag.svg](../assets/samples/svgkit-rag.svg) | A compact RAG layout with a separate original-question path above retrieval. |
