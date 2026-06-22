# Visualize

Visualize is an Agent Skill for generating clean technical diagrams as self-contained SVG files. It works with agents that support skills, including Cursor, Codex, Claude Code, and similar tools.

Use it when you want an architecture diagram, flowchart, sequence diagram, memory architecture, data flow, UML-style diagram, comparison matrix, timeline, or another technical visual from a plain-language prompt.

![RAG pipeline example](../visualize/assets/samples/hero.svg)

![Agent loop example](../visualize/assets/samples/sample-agent-loop.svg)

## How To Use

Describe the diagram you want in natural language:

```text
Draw a RAG pipeline diagram.
Draw a Mem0 memory architecture diagram and save it to ~/Desktop/.
Draw a microservice architecture diagram: Client -> API Gateway -> User Service / Order Service -> PostgreSQL + Redis.
```

The agent identifies the diagram type, opens the matching reference from `assets/gallery/<type>.svg`, and writes an SVG in the Visualize house style.

## What It Produces

Visualize writes SVG by default. The SVG is editable, scalable, and can be opened directly in a browser or embedded in documentation.

When Python 3 is available, the skill uses the included `svgkit` helper to size boxes from their text, anchor arrows on box edges, and keep the SVG structure valid. If Python is not available, the agent can still write the SVG directly.

No dependencies are installed by this skill.

## Supported Diagram Types

| Type | Use it for |
|---|---|
| Architecture | Services, components, cloud infrastructure, layered systems |
| Data flow | Pipelines with labeled payloads and transformations |
| Flowchart | Decisions, branches, process loops |
| Agent architecture | LLM, tools, memory, planning, output layers |
| Memory architecture | Mem0 or MemGPT-style read and write paths |
| Sequence | Time-ordered requests and responses with lifelines |
| State machine | UML states, transitions, guards, initial and final states |
| Class diagram | UML-style classes with attributes, methods, and relationships |
| Use case | Actors, use cases, include and extend relationships |
| ER diagram | Entities, relationships, and cardinality labels |
| Network topology | Firewalls, switches, DMZs, internal and external zones |
| Comparison | Feature matrices and capability comparisons |
| Mind map | Central concept with curved branches |
| Timeline / Gantt | Phases, milestones, and duration bars |

Every supported type has an owned reference diagram under `assets/gallery/<type>.svg`. See [`references/diagram-gallery.md`](../visualize/references/diagram-gallery.md) for the full index.

The gallery also ships `decision-ladder.svg` — not a separate type, but a compositing-pattern example (a step-by-step allow/deny chain) documented in [`references/layout-patterns.md`](../visualize/references/layout-patterns.md) §3.

## Style

Visualize uses one fixed style: a white canvas, warm cream or tinted boxes, thin open-chevron arrows, flat shapes, no shadows, no gradients, and no remote assets.

Color carries meaning:

| Family | Meaning |
|---|---|
| Neutral | Default boxes and plumbing |
| Green | Primary path, success, retrieval |
| Purple | Alternate or parallel path |
| Terracotta | Warning, limitation, failure |
| Amber | Highlighted or special module |

The exact tokens live in [`references/style.md`](../visualize/references/style.md).

## Repository Map

```text
visualize/
├── SKILL.md                         # Runtime entry point for the agent
├── references/                      # On-demand knowledge files
│   ├── style.md                     # Visual tokens and hard style rules
│   ├── svg-cookbook.md              # svgkit API and SVG snippets
│   ├── svg-layout-best-practices.md # Layout, routing, and spacing rules
│   ├── layout-patterns.md           # Compositing patterns (panels, steps, zones)
│   ├── diagram-types.md             # Per-type layout rules
│   ├── diagram-gallery.md           # Gallery index
│   ├── shape-vocabulary.md          # Color-family-to-meaning mapping
│   ├── product-colors.md            # Optional brand-color lookup
│   └── icons.md                     # Optional pictorial shape snippets
├── scripts/
│   ├── svgkit.py                    # Default zero-dependency SVG helper
│   ├── validate_svg.py              # SVG quality validator
│   └── check_palette.py             # Palette drift check (style ↔ svgkit ↔ validator)
└── assets/
    ├── gallery/                     # Reference diagrams by type
    └── samples/                     # Showcase examples
```

## License

MIT
