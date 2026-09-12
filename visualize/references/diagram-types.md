# Diagram types and notation

Read the relevant type below and open its [gallery example](diagram-gallery.md). [Style](style.md) defines the shared tokens; [layout patterns](layout-patterns.md) covers composite explanations.

## Architecture

Group components by responsibility, deployment location, or ownership. Client → gateway → services → storage is one useful layout, not a required architecture. Use a boundary only when it carries meaning. Label whether connections represent requests, data, or dependencies, and keep that convention consistent.

Align peers and route fan-out through a shared unheaded rail, with arrowheads at destination nodes. A component list inside a container does not imply that its items execute in sequence.

## Data flow

Arrows follow the payload from producer to consumer. Label each with the data it carries: events, vectors, passages, files, or rows. A store → query engine edge carries data; a query request travels in the opposite direction. Keep control signals distinct when both appear.

For RAG, show both inputs to generation: **the original question and retrieved context**. Embeddings feed retrieval; they do not replace the question. An offline indexing group may show document chunking and embedding separately from query-time work.

## Flowchart / process

Use process boxes and decision diamonds with labeled exits. Put the common path on one axis and returns in an outside gutter. A condition's branches should cover its outcomes; label a default where applicable.

Numbered steps communicate order. In an ordered policy ladder, distinguish final allow, final deny, and no match/continue. The gallery's policy groups are illustrative, not a product implementation.

## Agent architecture

Show the loop actually being explained: input/context → model decision → tool or output → observation → next decision. Include an exit when the loop can finish. A tool-assisted editing example need not represent every possible agent behavior.

Show tools, memory, verification, and persistence only when the described system uses them. Progress indicators must distinguish completed work from the current step. Name feedback payloads instead of using a generic loop arrow.

## Memory architecture

Separate writes from query-driven reads. Label the information stored and the context returned. Group stores or memory categories without implying an unsupported conversion chain between them. Working, episodic, semantic, and procedural memory are not universal successive stages.

Use the product's actual operations and boundaries when a specific implementation is requested. The generic gallery demonstrates routing through vector and graph stores, not a complete Mem0 or MemGPT architecture.

## Sequence

Participants occupy vertical lifelines; horizontal messages run in time order from top to bottom. Start messages below the participant headers. Dashed returns should remain visually distinct from the lifelines and must be explained in the legend.

Use `alt`, `opt`, or loop frames with room for headings and guards. Show a real message in each alternative. An optional authenticated call needs both a valid token and the required permission. Anchor to activation-bar edges (`cx ± 6` for a 12px bar).

The authorization-code example abbreviates the protocol to show redirects and token exchange. Authentication/consent precede code issuance; a browser must receive a code before forwarding it. Add state, PKCE, errors, and other protocol details when those are part of the requested explanation.

## Comparison

Use the same criteria, units, and status definitions across columns. Align row labels and keep cell dimensions consistent. Distinguish “supported,” “planned,” “unavailable,” and “unknown” rather than assigning unsupported good/bad scores.

For mechanism comparisons, use matched panels with the same input and output; put concise comparison rows underneath. A color can identify a method without ranking it. Label fictional examples and source real performance claims.

## Timeline / Gantt

Derive task starts, bar widths, tick marks, and milestones from one time scale. Width represents duration; shorten or move a label instead of widening its bar. Use a shared fill for peer phases unless color carries a specific category. Put milestone captions outside their small marks.

## Mind map / concept map

Balance branches around one central concept. Curved, unheaded links express association. Use directional arrows only for a stated dependency or transfer. Peers can share one accent family. A radial trade-off map may pair each option with a small consequence note.

## Class diagram

Use name, attribute, and method compartments. Keep `+`/`-`/`#` visibility notation, interface stereotypes, and abstract names readable. A stereotype and class name need separate baselines; `class_box()` provides a 48px header when a stereotype is present.

The house style uses open chevrons with explicit labels, rather than standard UML arrowhead shapes:

- `extends`: child → parent, solid.
- `«implements»`: class → interface, dashed.
- `uses`: dependent → dependency, dashed.
- Association, aggregation, and composition: state the relationship and multiplicity explicitly.

Label this as a house-style UML diagram when strict notation fidelity matters.

## Use case

Actors stay outside a named system boundary; use-case ellipses contain verb phrases. `«include»` points from base to included behavior. `«extend»` points from optional extension to base. In the house style both use dashed open chevrons with labels.

Route around neighboring ellipses and keep the actor's label clear. The actor helper returns anchors; its entire figure is not modeled as a collision obstacle.

## State machine

Name states as conditions, and transitions as `event [guard] / action`. Use a filled initial dot, a ringed final dot, and guarded choice exits where needed. A final state has no outgoing transitions; a recoverable failure may have a labeled retry.

Keep events consistent with the source state. The job example queues, runs, evaluates the result, then succeeds or fails. Anchor initial/final connections at their 8px/12px boundaries. Composite states need an explicit panel role.

## Entity relationship

Choose conceptual relationships or a physical schema before drawing. The gallery uses relationship diamonds and explicit cardinalities. A physical many-to-many schema needs an associative entity or join table. Mark keys consistently with `(PK)` and `(FK)`.

Place cardinalities close to their entity endpoints. Unrelated relationships need separate ports; a shared rail would imply a junction. Open chevrons in the gallery organize reading direction, not record flow.

## Network topology

State whether the diagram is physical or logical. Label devices, protocols, and relevant addresses. Put boundary devices clearly relative to the zones they connect. Use arrowheads only when traffic direction is part of the explanation; identify other line meanings in the legend.

## Charts and explanatory composites

For retention funnels, annotated curves, qualitative axes, shared-input lanes, and miniature mechanisms, use [layout-patterns.md](layout-patterns.md). Keep numeric scales faithful to data and distinguish illustrative values from measurements.
