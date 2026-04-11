# Phase 1: Deep Project Analysis

**Goal**: Build a comprehensive, factual understanding of the current codebase. No opinions, no suggestions — only what exists.

---

## Before You Begin

Confirm that `.spec/analysis/` exists and that the three template files are in place:
- `.spec/analysis/architecture.md`
- `.spec/analysis/module-map.md`
- `.spec/analysis/risk-register.md`

If they are missing, copy them from `assets/templates/analysis/` in the spec-coding skill directory. Do not create them from scratch.

---

## Dispatching Explore Subagents

Read `references/subagents/explore-brief.md` for the prompt template. Adapt it for each subagent you dispatch.

**Split the work by architectural boundary**, not by file count. One agent per logical area is more effective than one agent per directory. Examples:

- Core domain logic + data models
- Infrastructure layer (DB, external APIs, file I/O)
- Entry points, routing, public API surface

Dispatch all agents in parallel. Each agent should write its findings to a designated section of the relevant output file, or write to a scratch area that you consolidate afterward — decide the approach before dispatching and include it in the brief.

**If the project is small** (roughly 20 files or fewer), a single Explore pass is sufficient.

---

## Output: `.spec/analysis/`

Each file must be fully filled in before Phase 2 begins. Incomplete sections must be explicitly marked as "not found" — do not leave template placeholders.

### `architecture.md`
- Technology stack (all layers)
- All entry points with paths and purposes
- Build, run, test, and lint commands
- High-level architecture description (2–5 paragraphs)
- Architectural patterns observed, with file evidence
- External integrations

### `module-map.md`
- Every significant module: responsibility, public API, internal deps, external deps, size, complexity rating
- Do not omit modules because they seem unimportant — flag them as "trivial" if needed
- Dependency summary at the end

### `risk-register.md`
- Every risk that could affect the plan: complexity, coupling, missing tests, platform-specific code, external constraints
- Hotspot summary: the 2–3 areas most likely to cause problems
- External constraints

---

## Phase Boundary

Phase 1 is complete when all three files are filled and contain no template placeholders.

Do not share the analysis documents with the user at this stage — that happens in Phase 2.
Proceed to Phase 2 immediately.
