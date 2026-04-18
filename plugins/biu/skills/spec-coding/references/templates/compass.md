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

<Non-negotiable boundaries. Examples:>
- Must not break the public API
- stdlib only — no new dependencies
- Must support Node 18+

## Analysis

- [project-overview.md](./analysis/project-overview.md)
- [module-inventory.md](./analysis/module-inventory.md)
- [risk-assessment.md](./analysis/risk-assessment.md)

## Task Overview

<Populated by Phase 3 (architect subagent). One line per Task.>

- [ ] Task 1: setup-build (0/5) — [details](./tasks/task-1-setup-build.md)
- [ ] Task 2: migrate-core (0/8) — [details](./tasks/task-2-migrate-core.md)
- [ ] Task 3: integration-tests (0/4) — [details](./tasks/task-3-integration-tests.md)

## Skipped Tasks

<Append-only. Populated only when a task is skipped via the Blocked Protocol.>

- Task N: <name> — Reason: <why skipped>

## Decision Log

<Append-only. Record important technical decisions and plan changes discovered during Implementation.>

- **YYYY-MM-DD**: <decision or change and its reason>
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
2. **COMPASS symbol and task-file `**Status**:` must agree.** When one changes, the other must change in the same turn. Task file is authoritative on disagreement.
3. **`(X/N)` is derived from the task file's subtask checkboxes.** When a subtask checkbox flips, update `(X/N)` in the same turn.

---

## What NOT to include

These fields were present in earlier versions and have been **removed** to reduce drift:

- ~~`## Current Status`~~ — derivable from the `[~]` line and its Resume point; narrative drifted easily
- ~~`## Next Steps`~~ — derivable likewise
- ~~`← Active` annotation~~ — redundant with `[~]` symbol

If you need to record something non-derivable, that is what `## Decision Log` is for.
