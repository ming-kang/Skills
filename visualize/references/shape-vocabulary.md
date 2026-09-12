# Shape and color vocabulary

Use shape to express structure, labels to name it, and color to reinforce a small number of meanings. [style.md](style.md) owns the exact family tokens and typography.

## Choose the primitive by meaning

| Meaning | Primitive | Notes |
|---|---|---|
| Process, service, model, agent, tool | Rounded box | `node()`; size from text, then align peers. |
| Storage | Cylinder or labeled box | `cylinder()` when the storage shape helps recognition. |
| Decision | Diamond | `diamond()` with explicit conditions on its exits. |
| Group, scope, ownership boundary | Container, panel, frame | `container()`, `panel()`, `scope()`, or `zone()`; grouping alone does not imply execution order. |
| UML class or entity | Compartmented box | `class_box()` or `entity()`; keep fields aligned. |
| Use case | Ellipse | `usecase()`; leave extra room near the curved ends. |
| Participant | Actor and/or lifeline | `actor()` or `lifeline()` according to the notation. |
| State start/end | Filled or ringed dot | `state_dot()`; anchors lie on its outer boundary. |
| Duration or retained quantity | Scaled bar/band | Geometry follows the value, not the text. |
| Item, token, repeated state | Small circle or cell | Equal items use equal shapes and spacing; captions explain what repetition means. |

The last two rows often make a mechanism clearer than another large process box. See [mechanism comparison](../assets/gallery/patterns/mechanism-comparison.svg) and [record retention](../assets/gallery/patterns/annotated-funnel.svg).

## Color relationships

Start with Neutral plus one accent. Use Green for a primary path or success, Purple for an alternative or parallel lane, Terracotta for an actual failure/constraint, and Amber for a focal step or special condition. Within a comparison, an accent can identify a method without rating it. Keep peer items consistent.

The [feature matrix](../assets/gallery/comparison.svg) distinguishes supported, planned, and unavailable with both text and fill. It does not turn every comparison into a winner/loser judgment. The [parallel lanes](../assets/gallery/patterns/parallel-pipelines.svg) keep one color per platform across all stages.

## Connections are a separate vocabulary

- **Flow:** a 1.5px line with the shared open chevron, anchored to the destination edge.
- **Return, optional path, or UML relationship:** the same chevron with a defined dashed-line meaning and a label where needed.
- **Association or shared rail:** an unheaded connection; do not suggest a destination that does not exist.
- **Explanation:** a light 0.5–0.75px unheaded leader, optionally dashed.
- **Data series:** a line and/or points whose positions follow the scale; no flow arrowheads on a series.

Use a legend that repeats the actual symbol: a fill swatch for categories, a line sample for an edge meaning, or a line and point for a plotted series. All visual distinctions should still be understandable from their labels.

## Compound shapes and validation roles

Ordinary shapes are routing obstacles. Explicit `panel` or `container` roles allow intentional containment. `node-part` identifies a component such as a cylinder cap; `data-mark` identifies value-driven geometry. Small marks still receive canvas-bound checks. For manual markup and validation limits, see [validation.md](validation.md).
