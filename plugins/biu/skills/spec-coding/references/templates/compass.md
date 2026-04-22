# COMPASS.md Template

This template defines the canonical structure of `.biu/COMPASS.md`. It is the **single source of truth** for what sections COMPASS has, what each is for, and how the Task Overview is formatted.

COMPASS is a pure **state router** for a spec-coding cycle. Spec content (Task Definition, Assumptions & Constraints, Analysis links) lives in `.biu/plan.md` — see `templates/plan.md`.

Every file that reads or writes COMPASS (SKILL.md, agents/architect.md, references/implementation.md, references/blocked-protocol.md) should reference this template instead of restating the structure inline.

---

## Template

```markdown
# COMPASS

**Plan**: [plan.md](./plan.md)

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
| `**Plan**:` pointer | Phase 2 (main agent) | Written once; static link to `plan.md` |
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

1. **At most one `[~]` at any time.** Before starting a new Task, the currently-active Task must be transitioned to `[x]`, `[!]`, or `[-]` first. This invariant is enforced by SKILL.md Behavioral Rule `R-no-auto-advance` ("One Task at a time. Never auto-advance.") and by the workflow contract.

The disagreement-resolution invariants — "task file is authoritative when COMPASS symbol and `**Status**:` disagree", and "checkbox tally is authoritative when COMPASS `(X/N)` and task-file checkboxes disagree" — live in SKILL.md as Behavioral Rule `R-authority` ("Authority on disagreement"), so every session picks them up without loading this template. Referenced here rather than duplicated.
