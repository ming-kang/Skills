---
name: decompose
description: Decompose .biu/SPEC.md into .biu/tasks/TASK-*.md handoff files.
disable-model-invocation: true
---

# Biu Decompose

Use this skill to turn `.biu/SPEC.md` into implementation tasks under `.biu/tasks/`.

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

`.biu/SPEC.md` is the required input. `.biu/tasks/` will contain TASK files for the current SPEC.

**Pre-flight checks:**
- Read `.biu/SPEC.md`
- Verify `status` is `ready`
- Verify `## Open Questions` has no unresolved items
- Assess identified `## Risks` for mitigation feasibility

If checks fail, stop and tell the user to complete the SPEC via `/biu:interview` first.

### Explore

Explore the codebase to map the SPEC to code reality. Identify natural task boundaries and give each task a short unique name reflecting its objective.

**Reuse-First**: Before proposing new code, search for existing functions, utilities, and patterns that can be reused. Reference them by file path. Prefer extension over reinvention.

Capture findings incrementally as you explore — don't wait until exploration is complete to start forming the task structure. Do not ask the user anything that can be answered by reading the code.

### Align

Present the proposed task structure to the user — start with the high-level breakdown before elaborating per-task detail.

Explain:
- How the SPEC maps to these tasks
- Dependencies between tasks
- Which AC IDs each task covers
- The intended approach for each task:
  - Critical files (3-5, with paths)
  - Existing code identified for reuse
  - Design decisions already made for the executor
- Any specific risks from SPEC that apply to the task, and how to mitigate them
- Why each task is scoped the way it is — briefly justify any non-obvious boundary

For non-obvious decomposition decisions that can't be resolved from the SPEC or codebase — scope boundaries, sequencing trade-offs, approach choices — surface them for the user. If such ambiguities are frequent, the SPEC needs further refinement first.

Before confirming, verify:
- Every AC in SPEC is covered by at least one task.
- Every `depends_on` reference resolves to another task in the set, and the dependency graph is acyclic.
- Each task has a single clear objective and is specific enough for another agent to execute without extra context.

Surface any issues and adjust. The structure is ready when checks pass and the user confirms.

### Write

When writing each task's `## Verify` section, describe the approach based on what the task changes. Match strategy to change type:

- **Frontend / UI**: start dev server, exercise the UI flow, check console errors
- **Backend / API**: run endpoints with valid and invalid inputs, verify response shape and status
- **CLI / script**: run with representative and edge inputs, check stdout/stderr and exit codes
- **Migration / schema**: run up and down, verify schema, test against existing data
- **Refactor**: existing test suite must pass unchanged; spot-check observable behavior
- **Bug fix**: reproduce the original bug first, then verify the fix removes it

Start the checklist with the baseline (build succeeds, existing tests pass, linter clean), then add task-specific items that probe edge cases and error states — not just the happy path.

Write tasks one at a time — create each `.biu/tasks/TASK-*.md` with `status: ready` sequentially before moving to the next. Once all tasks are written, report the generated files.

## Task Lifecycle

Tasks are written with `status: ready` by decompose. During execution, the executing agent updates the frontmatter:

- `ready` → written by decompose, not yet started
- `in_progress` → work has started
- `completed` → work is done and verified

When significant decisions are made during execution — choices not already in Context, unexpected pivots, user-directed changes — the executing agent records them in `## Implementation Decisions`.

## Reference

Template: `${CLAUDE_SKILL_DIR}/references/task-template.md`
