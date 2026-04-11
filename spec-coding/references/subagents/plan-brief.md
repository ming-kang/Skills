# Plan Subagent Brief — spec-coding Phase 3

This file is a prompt template for dispatching the Plan subagent during Phase 3. Read it, fill in the bracketed sections with actual context from Phase 2, and pass the result as the task description when invoking Plan.

---

## Prompt Template

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
Forbidden patterns: TBD, TODO, "implement later", "similar to Task N", "details to be determined".
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

**For milestones.md:** Define 3-5 meaningful checkpoints where the project reaches a demonstrably better state (something working end-to-end, a risk retired, a deliverable ready). Each milestone must have explicit target criteria.

---

When you are done, confirm both files are written. Do not summarize the plan back to me — the files are the output.
```

---

## Notes for the Main Agent

- Read plan-brief.md, fill in the three bracketed context sections, then dispatch Plan with the completed prompt.
- If Plan returns with a file containing any placeholder pattern, do not proceed to Phase 4. Send Plan back with explicit instructions to resolve each placeholder before continuing.
- The Plan subagent is read-only and cannot create directories. Ensure `.spec/plan/` exists and the template files are in place before dispatching.
