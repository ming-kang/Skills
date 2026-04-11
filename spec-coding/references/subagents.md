# Subagent Prompts

---

## Explore

### When to Use

Phase 1: Deep Project Analysis. Dispatch multiple Explore subagents in parallel, each assigned to a distinct architectural boundary.

### Prompt Template

> **Before dispatching**: Replace every `[BRACKETED]` section with actual content. Never send bracketed placeholder text to a subagent.

```
You are performing a focused codebase analysis for a spec-coding workflow.

Your target area: [SPECIFY — e.g., "the authentication and session management modules", "all database access layers", "the public API surface and routing layer"]

Working directory: [PROJECT ROOT]
Output mode: Report findings back to the main agent in your final message. Do not write to `.spec/analysis/*` files directly.

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

---

When you are done, provide:
1) a structured findings list that the main agent can paste into `.spec/analysis/*`
2) the most important finding in 2–3 sentences
3) any confidence gaps or unknowns
```

### Dispatching Notes

- Split by architectural boundary, not by file count. Example for a medium project:
  - Agent A: core domain logic + data models
  - Agent B: infrastructure layer (DB, external APIs, file I/O)
  - Agent C: entry points, routing, public API surface
- Dispatch all in parallel.
- If the project is small (<~20 files), a single Explore pass is sufficient.
- The main agent consolidates all reports and performs all writes to `.spec/analysis/*`.

---

## Plan

### When to Use

Phase 3: Task Decomposition. Dispatch one Plan subagent after all three analysis files are complete and the architecture direction is confirmed in COMPASS.md.

### Prompt Template

> **Before dispatching**: Fill in all three bracketed context sections with actual content from COMPASS.md. Ensure `.spec/plan/` exists and both template files are in place — Plan cannot create directories.

```
You are performing task decomposition for a spec-coding workflow. Your job is to produce a concrete, complete, actionable plan — no placeholders, no deferred decisions.

---

CONTEXT:

Confirmed task: [PASTE TASK DEFINITION FROM COMPASS.md]

Confirmed architecture direction: [PASTE ARCHITECTURE DIRECTION FROM COMPASS.md]

Assumptions & constraints (non-negotiable — do not plan around violating these):
[PASTE ASSUMPTIONS & CONSTRAINTS FROM COMPASS.md]

Analysis documents to read before doing anything else:
- .spec/analysis/architecture.md
- .spec/analysis/module-map.md
- .spec/analysis/risk-register.md

Output files (templates are already in place — fill them, do not create new files):
- .spec/plan/task-breakdown.md
- .spec/plan/milestones.md

---

TASK DECOMPOSITION RULES:

**No placeholders.** Every task and subtask must be fully specified before you write it down.
Forbidden: TBD, TODO, "implement later", "similar to Task N", "details to be determined", "to be specified".
If you cannot fully specify something yet, stop and think harder — do not write the placeholder.

**Order by dependency.** Foundational components before dependent ones. A task that another task depends on must be sequenced earlier.

**Each task must be independently verifiable.** There must be a clear way to confirm it is done — a test, a working build, a demonstrable behavior, a diff that can be reviewed.

**For each Task, define:**
- Description: what to do, specifically
- Priority: P0 (must have), P1 (should have), P2 (nice to have)
- Effort: S (hours), M (1-2 days), L (3-5 days), XL (>1 week)
- Dependencies: which other Tasks must be complete first
- Acceptance criteria: the conditions that make this Task done — concrete and checkable

**For each Task, decompose into subtasks.** Each subtask should be completable in a single focused session. If a subtask would take more than a few hours, decompose further.

**Include a Mermaid dependency graph** in task-breakdown.md showing Task relationships.

**For milestones.md:** Define 3–5 meaningful checkpoints where the project reaches a demonstrably better state — something working end-to-end, a risk retired, a deliverable ready. Each milestone must have explicit target criteria.

---

When you are done, confirm both files are written. Do not summarize the plan back to me — the files are the output.
```

### Notes

- If Plan returns with any forbidden placeholder pattern, send it back with a list of every occurrence. Do not proceed to Phase 4 with an incomplete plan.
