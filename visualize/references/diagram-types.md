# Diagram Types — Full Layout Rules

This file contains detailed layout rules for each diagram type. Load when generating a diagram.

> **Style first.** All colors, fonts, radii, the open-chevron arrow marker, and spacing come from `references/style.md`; ready-made snippets are in `references/svg-cookbook.md`. The notes below are about *layout and notation*. Default canvas width is ~720; height grows to fit the content (40px margins).
>
> **Color families by role** (tinted box fills, not arrow-only accents): Neutral cream = plumbing/default · **Green** = primary / happy path / retrieval · **Purple** = alternate or parallel branch · **Terracotta** = warning / limitation / failure · **Amber** = highlighted special module. Pick the family by meaning and stay consistent within a diagram.

## Architecture Diagram

Nodes = services/components. Group into **horizontal layers** (top→bottom or left→right).

- Typical layers: Client → Gateway/LB → Services → Data/Storage
- Use `<rect>` dashed containers to group related services in the same layer
- Arrow direction follows data/request flow
- Align centers within each vertical chain. Use shared rails without arrowheads for fan-out/fan-in, with heads only where a connection reaches a node.
- ViewBox: width ~720, height grows with content (taller for many layers)
- **Trust-boundary / deployment split**: when nodes sit on opposite sides of a boundary (client↔server, on-prem↔cloud), separate them with a `.zone()` divider and let the cross-zone edges carry the story (`references/layout-patterns.md` §1). A titled `.panel()` groups a cluster that needs a stronger frame than a dashed container (§4).

## Data Flow Diagram

Emphasizes **what data moves where**. Focus on data transformation.

- Label every arrow with the data type (e.g., "embeddings", "query", "context")
- Mark the primary data path with a family LINE color (Green `#1D9E75`); keep all line widths at 1.5 — distinguish by color, not by thickness
- Dashed lines for control/trigger flows
- Color arrows by data category using the families in `references/style.md`

## Flowchart / Process Flow

Sequential decision/process steps.

- Top-to-bottom preferred; left-to-right for wide flows
- Diamond shapes for decisions, rounded rects for processes, parallelograms for I/O
- Keep node labels short (≤3 words); put detail in sub-labels
- Align the main flow on one centerline, size boxes from labels, and reserve routing gutters before placing side branches
- **Numbered recipe / pipeline**: use `.step()` cards (circled badge + title) so order reads without an arrow on every link (`references/layout-patterns.md` §2).
- **Allow/deny ladder**: a chain of checks bracketed by a green "Execute" rail and a terracotta "Blocked" rail — green arrows up = pass, terracotta down = fail (§3). A long feedback return routes up the right gutter (§6).

## Agent Architecture Diagram

Shows how an AI agent reasons, uses tools, and manages memory.

Key conceptual layers:
- **Input layer**: User, query, trigger
- **Agent core**: LLM, reasoning loop, planner
- **Memory layer**: Short-term (context window), Long-term (vector/graph DB), Episodic
- **Tool layer**: Tool calls, APIs, search, code execution
- **Output layer**: Response, action, side-effects

Use cyclic arrows (loop arcs) for iterative reasoning. Separate memory types visually.

## Memory Architecture Diagram (Mem0, MemGPT-style)

Specialized agent diagram focused on memory operations.

- Show memory **write path** and **read path** separately (different arrow colors)
- Memory tiers: Working Memory → Short-term → Long-term → External Store
- Label memory operations: `store()`, `retrieve()`, `forget()`, `consolidate()`
- Use stacked rects or layered cylinders for storage tiers

## Sequence Diagram

Time-ordered message exchanges between participants.

- Participants as vertical **lifelines** (top labels + vertical dashed lines)
- Messages as horizontal arrows between lifelines, top-to-bottom time order
- Activation boxes (thin filled rects on lifeline) show active processing
- Group with `<rect>` loop/alt frames with label in top-left corner
- Start messages at least 40px below the participant boxes, use roughly 48–60px between messages, and reserve a separate legend area below the lifelines
- Anchor messages on activation-bar edges when present, so the bars cannot cover arrowheads; a 12px activation uses `cx ± 6`
- Reserve a left gutter for frame names and guards; place real messages in each `alt` branch and keep them clear of the frame header
- **Payload messages**: when an arrow carries both a name and literal data, stack a 12/CAPTION label above the line and a monospace payload below — monospace is the only place a non-system font appears (`references/layout-patterns.md` §8).
- **Repeating region**: wrap a span of messages in a `.scope()` frame labelled `EACH TURN` / `PER REQUEST` rather than a plain loop box (§5); out-of-band events (notifications, telemetry) hang off a dashed side-rail (§7).

## Comparison / Feature Matrix

Side-by-side comparison of approaches, systems, or components.

- Column headers = systems, row headers = attributes
- Row height: 40px; column width: min 120px; header row height: 50px
- Use equal column widths and 16–24px gutters; keep row labels in a dedicated, consistently aligned column
- "Has it" cell: tinted family background (Green `#E1F5EE` + `✓` in `#0F6E56`); "lacks it" cell: neutral `#F5F4ED` (or a Terracotta `#FAECE7` ✗ when it's a real downside)
- Keep the grid quiet: white rows with hairline `rgba(31,30,29,0.3)` dividers
- Max readable columns: 5; beyond that, split into two diagrams

## Timeline / Gantt

Horizontal time axis showing durations, phases, and milestones.

- X-axis = time (weeks/months/quarters); Y-axis = items/tasks/phases
- Bars: rounded rects, colored by category, labeled inside or beside
- Milestone markers: diamond or filled circle at specific x position with label above
- Derive bars, week guides, and milestones from the same time scale. Use one fill family for peer phases unless color encodes a distinct category; avoid repeating the row name inside every bar.
- ViewBox: width ~720 (wider for many time periods), height grows with content
- Helpers: `.bar(x, y, w, label, family=...)` per bar — the width is the time span, not the label (default height 28); `diamond(..., hw=8, hh=8, family="amber")` for milestones with an external label; the time axis is a `.raw()` loop of `<line>` guides + `<text>` labels. See `assets/gallery/timeline-gantt.svg`.

## Mind Map / Concept Map

Radial layout from central concept.

- Center the core node in the available body area, leaving room for the heading and legend
- Balance first-level branches around the center; paired left/right rows can be easier to read than a strict angular distribution
- Second-level branches: branch off first-level at 30-45° offset
- Use curved `<path>` with cubic bezier for branches, not straight lines

## Class Diagram (UML)

Static structure showing classes, attributes, methods, and relationships.

- **Class box**: 3-compartment rect (name / attributes / methods), min width 160px
  - Top: class name, bold, centered (abstract = *italic* via `font-style`)
  - Middle: attributes with visibility (`+` public, `-` private, `#` protected)
  - Bottom: method signatures, same visibility notation
- **Relationships (House-style)** — this skill keeps a single open-chevron marker for every relationship; distinguish them by **line style + text label**, never by swapping arrowhead shapes:
  - Inheritance: solid line + chevron + label `extends` (child → parent)
  - Implementation: dashed line (`stroke-dasharray="4 3"`) + chevron + label `«implements»` (class → interface)
  - Association: solid line + chevron + multiplicity labels (`1`, `0..*`, `1..*`)
  - Aggregation / Composition: solid line + chevron + label `aggregates` / `composes` + multiplicity (the label carries the meaning instead of a diamond on the container side)
  - Dependency: dashed line + chevron + label `uses`
- **Interface**: `<<interface>>` stereotype above name; **Enum**: `<<enumeration>>`
- Allow a 48px title compartment for a stereotype plus name, with distinct text baselines; the plain name compartment is 30px
- Layout: parent classes top, children below; interfaces to the left/right
- ViewBox: width ~720, height grows with content (taller for deep hierarchies)
- Helper: `.class_box(x, y, name, attrs, methods, family=..., abstract=False, stereotype="interface")` renders the 3-compartment box (min width 160, abstract name italic). Realization / dependency lines are `dashed=True` on `.arrow()` / `.lpath()`. See `assets/gallery/class-diagram.svg`.

## Use Case Diagram (UML)

System functionality from user perspective.

- **Actor**: stick figure (circle head + body line) outside system boundary
  - Label below figure, **14px** (family TITLE color)
  - Primary actors on left, secondary on right
- **Use case**: ellipse with label centered, min 140×60px
  - Verb phrases: "Create order", "Process payment"
- **System boundary**: large dashed rect + system name in top-left
- **Relationships (House-style)** — single open-chevron marker, distinguished by line style + label:
  - Include: dashed line + chevron + label `«include»` (base → included)
  - Extend: dashed line + chevron + label `«extend»` (extension → base)
  - Generalization (actor or use case): solid line + chevron + label `extends`
- ViewBox: width ~720, height grows with content
- Helpers: `.actor(cx, y, label, family=...)` (stick figure + 14px label; returns a Box for anchoring, and is NOT a collision obstacle — keep actors outside the boundary), `.usecase(x, y, label, family=...)` (ellipse min 140×60). **Ellipses ARE obstacles**, so route `«include»`/`«extend»` arrows with `.lpath(..., dashed=True)` through the row gutters around neighbouring ellipses. See `assets/gallery/use-case.svg`.

## State Machine Diagram (UML)

Lifecycle states and transitions of an entity.

- **State**: rounded rect with name, min width 120px; height 40 for one line or 56 for two
  - Internal activities: `entry/ action`, `exit/ action`, `do/ activity`
- **Initial state**: filled black circle (r=8), one outgoing arrow
- **Final state**: filled circle (r=8) inside hollow circle (r=12)
- **Choice**: small diamond, guard labels `[condition]`
- **Transition**: arrow with `event [guard] / action`
- Anchor initial/final connections at the circle boundary (8px / 12px from the center) so the state marker cannot hide the arrowhead
- **Composite state**: larger rect containing sub-states, with name tab. For hand-written SVG, mark the outer rect `data-role="panel"` and its title `data-role="container-label"`; otherwise ordinary node containment correctly fails validation.
- **Fork/join**: thick black bar (synchronization)
- Layout: initial top-left, final bottom-right, flow top→bottom
- ViewBox: width ~720, height grows with content

## ER Diagram (Entity-Relationship)

Database schema and data relationships.

- **Entity**: rect with name header (bold), attributes below
  - Primary key: underline or `(PK)`; Foreign key: italic or `(FK)`
  - Min width: 160px; attribute font-size: 12px
- **Relationship**: diamond shape on connecting line
  - Label: "has", "belongs to"; Cardinality: `1`, `N`, `M`, `0..1`, `0..*`, `1..*`
- Put cardinality labels close to their entity endpoints. Use separate ports for unrelated relationships; a shared rail would imply a connection that is not present.
- **Weak entity**: double-bordered rect with double diamond
- **Associative entity**: rect with diamond inside
- Solid lines for identifying, dashed for non-identifying relationships
- Layout: entities in 2-3 rows, relationships between related entities
- ViewBox: width ~720 (wider for many entities), height grows with content

## Network Topology

Physical or logical network infrastructure.

- **Devices**: labeled rounded rectangles for routers, switches, servers, firewalls, and load balancers; use a cylinder when the storage role matters
- **Connections**: solid or dashed paths with short protocol/bandwidth labels; explain different line meanings in the legend
- **Subnets/Zones**: dashed rect containers (DMZ, Internal, External)
- Keep boundary devices clearly placed relative to zones, with room between each container header and its nodes
- **Labels**: hostname at 14px, IP or protocol detail at 12px
- Layout: tiered Internet → Edge → Core → Access → Endpoints
- ViewBox: width ~720, height grows with content

## UML Coverage Map

| UML Diagram | Supported As | Notes |
|-------------|-------------|-------|
| Class | Class Diagram | House-style: 3-compartment boxes; relationships via line-style + label (no per-relation markers) |
| Component | Architecture Diagram | Colored fills per type |
| Deployment | Architecture Diagram | Node/instance labels |
| Package | Architecture Diagram | Dashed grouping containers |
| Composite Structure | Architecture Diagram | Nested rects |
| Object | Class Diagram | Underlined instance names |
| Use Case | Use Case Diagram | House-style: actor + ellipse + dashed «include»/«extend» |
| Activity | Flowchart | Add fork/join bars |
| State Machine | State Machine Diagram | States, guards, initial/final markers, and labeled transitions in the house style |
| Sequence | Sequence Diagram | alt/opt/loop frames |
| Communication | — | Approximate with Sequence |
| Timing | Timeline | Adapt time axis |
| Interaction Overview | Flowchart | Activity + sequence fragments |
| ER Diagram | ER Diagram | Entity compartments, relationship diamonds, and explicit cardinality labels |
