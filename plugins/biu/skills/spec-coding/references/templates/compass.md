# COMPASS.md Template

This template defines the canonical structure of `.spec/COMPASS.md`. It is the **single source of truth** for what sections COMPASS has, what each is for, and how the Task Overview is formatted.

Every file that reads or writes COMPASS (SKILL.md, agents/architect.md, references/implementation.md, references/blocked-protocol.md) should reference this template instead of restating the structure inline.

---

## Template

```markdown
# COMPASS

## Task Definition

<One paragraph: what is being built or transformed, confirmed with the user in Phase 2.>

## Assumptions & Constraints

<Non-negotiable boundaries locked in during Phase 2.>

## Analysis

- [project-overview.md](./analysis/project-overview.md)
- [module-inventory.md](./analysis/module-inventory.md)
- [risk-assessment.md](./analysis/risk-assessment.md)

## Task Overview

<Populated by Phase 3>

## Skipped Tasks

*(Populated only if a task is skipped via the Blocked Protocol during Implementation.)*

## Decision Log

*(Append-only. Important technical decisions and plan changes discovered during Implementation will be recorded here.)*
```

---

## Section semantics

| Section | Written by | Mutation pattern |
|---|---|---|
| `## Task Definition` | Phase 2 (main agent) | Written once; only changed if scope fundamentally shifts |
| `## Assumptions & Constraints` | Phase 2 (main agent) | Written once; only changed via explicit user decision |
| `## Analysis` | Phase 2 (main agent) | Links; may gain `*(Updated YYYY-MM-DD)*` annotation if analysis docs are revised mid-cycle |
| `## Task Overview` | Phase 3 (architect); then Implementation (main agent) | Status symbol + `(X/N)` count mutate per transition. Order of lines does NOT change after Phase 3. |
| `## Skipped Tasks` | Implementation (main agent) | **Append-only** |
| `## Decision Log` | Implementation (main agent) | **Append-only** |

---

## Task Overview — format per line

```
- [STATUS] Task N: <short-name> (X/N) — [details](./tasks/task-N-<short-name>.md)
```

- `N` — sequential task number, starting at 1
- `<short-name>` — matches the filename kebab-case suffix
- `X` — number of subtasks currently checked `[x]` in the task file
- `N` (second one) — total number of subtasks in the task file
- `STATUS` — one of the five symbols below

### Status symbols

| Symbol | Meaning | Mirror of task-file `**Status**:` |
|---|---|---|
| `[ ]` | Pending (not started) | `PENDING` |
| `[~]` | In Progress | `IN_PROGRESS` |
| `[x]` | Complete | `COMPLETE` |
| `[!]` | Blocked | `BLOCKED` |
| `[-]` | Skipped | `SKIPPED` |

### Invariants

1. **At most one `[~]` at any time.** Before starting a new Task, the currently-active Task must be transitioned to `[x]`, `[!]`, or `[-]` first. This invariant is enforced by SKILL.md Behavioral Rule #2 (no auto-advance) and by the workflow contract.

The disagreement-resolution invariants — "task file is authoritative when COMPASS symbol and `**Status**:` disagree", and "checkbox tally is authoritative when COMPASS `(X/N)` and task-file checkboxes disagree" — live in SKILL.md as Behavioral Rule #10 ("Authority on disagreement"), so every session picks them up without loading this template. Referenced here rather than duplicated.
