# Explore Subagent Brief — spec-coding Phase 1

This file is a prompt template for dispatching Explore subagents during Phase 1. Read it, adapt the bracketed sections to your specific analysis target, and pass the result as the task description when invoking Explore.

---

## Prompt Template

```
You are performing a focused codebase analysis for a spec-coding workflow.

Your target area: [SPECIFY — e.g., "the authentication and session management modules", "all database access layers", "the public API surface and routing layer"]

Working directory: [PROJECT ROOT]
Output file: .spec/analysis/[FILENAME] — write your findings directly to this file using the template already present there.

---

RULES:
- Record facts only. Do not suggest solutions, refactors, or improvements.
- If you have an opinion about whether something is good or bad, record it as a risk or complexity flag — not as a recommendation.
- Be precise about locations: include file paths and line numbers where relevant.
- If you find something surprising or undocumented, flag it explicitly.

---

ANALYSIS TARGETS:

For each module or component in your assigned area, record:

1. **Responsibility** — What does this module do? One sentence.
2. **Public API surface** — What does it expose to the rest of the codebase? (exports, interfaces, entry points)
3. **Internal dependencies** — Which other internal modules does it depend on?
4. **External dependencies** — Which third-party libraries does it use directly?
5. **Approximate size** — Line count or rough complexity (trivial / small / medium / large / very large)
6. **Complexity signals** — Anything that would make this hard to change: complex algorithms, platform-specific code, tightly coupled state, missing tests, undocumented behavior

For [architecture.md / module-map.md / risk-register.md — pick the relevant one]:
[Add file-specific instructions here based on which file this Explore instance is writing to]

---

When you are done, confirm the file has been written and summarize in 2-3 sentences what the most important finding was in your assigned area.
```

---

## Dispatching Multiple Explore Instances

For Phase 1, dispatch Explore subagents in parallel to cover different areas simultaneously. Split the work by architectural boundary, not by file count — one agent per logical area is more useful than one agent per directory.

Example splits for a medium-sized project:
- Agent A: core domain logic + data models
- Agent B: infrastructure layer (DB, external APIs, file I/O)
- Agent C: entry points, routing, public API surface

Each agent writes to a different section of the same output file, or writes to a scratch area that the main agent consolidates. Decide the approach before dispatching and include it in the brief.

If the project is small (< ~20 files), a single Explore pass is sufficient.
