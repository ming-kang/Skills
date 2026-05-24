---
name: archive
description: Archive the current biu cycle and summarize SPEC/TASK outcomes.
disable-model-invocation: true
---

# Biu Archive

Use this skill to close the current biu cycle: summarize outcomes under `.biu/`, then archive SPEC, TASKs, and Summary together into `.biu/archived/YYYY-MM-DD-NN/`.

## Biu Workflow

Biu provides three skills covering the full development cycle from idea to archive:

| Skill | Role |
|:-----:|:----:|
| `interview` | Clarify requirements through relentless interview, producing `.biu/SPEC.md` |
| `decompose` | Decompose SPEC into `.biu/tasks/TASK-*.md` implementation handoffs |
| `archive` | Summarize outcomes and archive the completed cycle |

Typical usage: `/biu:interview` → `/biu:decompose` → Implement → `/biu:archive`

This is not a requirement. The user can skip or reorder them as needed.

### Directory Layout

`.biu/` must be git-ignored. Before writing, check `.gitignore` and add `.biu/` if missing.

```text
.biu/
├── SPEC.md                         # Development Specification
├── tasks/                          # Implementation Tasks
│   └── TASK-<short-name>.md
└── archived/                       # Completed Cycles
    └── YYYY-MM-DD-NN/
        ├── SPEC.md
        ├── Summary.md
        └── tasks/
            └── TASK-<short-name>.md
```

## Process

### Assess

Active cycle inputs are `.biu/SPEC.md` and `.biu/tasks/TASK-*.md`. Archive output lives under `.biu/archived/YYYY-MM-DD-NN/`.

**Pre-flight checks:**
- Verify `.biu/SPEC.md` exists
- Verify `.biu/tasks/` contains TASK files
- Read all SPEC and TASK files

**Status evaluation:**
- **All completed** → proceed to summarize
- **Any in_progress or ready** → list them and ask the user how to close:
  - Continue work
  - Mark selected tasks
  - Archive as-is

Do not proceed until the user decides.

**Baseline context:**
Read `baseline_commit` from SPEC frontmatter. If it resolves in the current repo, run `git diff --stat <baseline>..HEAD` as context for the Summary. Treat a missing or unresolvable baseline as "no diff available."

### Summarize

Analyze the cycle and draft `Summary.md` directly under `.biu/`. The primary source material is each TASK's `## Implementation Decisions` and `## Notes`.

- **Outcome** — what was actually achieved, and how it differs from the SPEC's goal
- **Decisions & Discoveries** — synthesize from each TASK's Implementation Decisions and Notes
  - During discussion, explicitly ask the user whether any significant decisions or new domain knowledge discovered during implementation are missing from the task files
  - Exclude decisions already recorded in SPEC
- **Deviations** — what changed mid-cycle from the original SPEC and what triggered it
- **Task Results** — group by AC, not TASK order
  - Use the task's own frontmatter status (`completed` / `in_progress` / `ready`)
  - Notes column: brief evaluation of key issues encountered for that AC and how they were resolved
- **Gaps & Follow-Ups** — what was not verified, and items the next cycle can pick up

Present the draft to the user. Discuss and adjust until confirmed.

### Archive

Determine the archive directory: `.biu/archived/YYYY-MM-DD-NN/`, where `NN` starts at `01` and increments for the same date. Scan existing directories and pick the first unused `NN`.

If the repository uses Git, run `git rev-parse HEAD` and record the result as `head_commit` in `Summary.md` frontmatter.

Create the archive directory. Move `SPEC.md`, `tasks/`, `Summary.md`, and any other temporary cycle artifacts into it. Confirm `.biu/` now contains only `archived/`.

If `## Gaps & Follow-Ups` in Summary is non-empty, remind the user they can pick up these items when starting the next cycle.

## Reference

Template: `${CLAUDE_SKILL_DIR}/references/summary-template.md`
