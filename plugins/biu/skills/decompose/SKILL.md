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

Typical usage is as follows: `/biu:interview` → `/biu:decompose` → Implement → `/biu:archive`

However, this is not a requirement. User can skip or reorder them as needed.

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

Read `.biu/SPEC.md`. If `status` is not `ready`, or `## Open Questions` still has unresolved items, stop and tell the user to complete the SPEC via `/biu:interview` first. Also, assess any identified `## Risks` to ensure they can be effectively mitigated within the upcoming implementation tasks.

### Decompose

Inspect code only as needed to identify natural task boundaries. Give each task a short unique name reflecting its objective.

Present a draft task list to the user before writing files. Explain:
- How the SPEC maps to these tasks.
- Dependencies between tasks.
- Which AC IDs each task covers.
- The intended approach for each task: key files or modules involved, and any design decisions already made for the executor.
- Any specific risks from SPEC that apply to the task, and how they should be mitigated.
- Why each task is scoped the way it is — briefly justify any non-obvious boundary.

Discuss and adjust until the user agrees on the shape.

### Check

Before writing, verify:

- Every AC in SPEC is covered by at least one task.
- Every `depends_on` reference resolves to another task in the set, and the dependency graph is acyclic.
- Each task has a single clear objective and is specific enough for another agent to execute without extra context.

Surface any issues and adjust with the user. After the checks pass and the user confirms, write tasks one at a time — create each `.biu/tasks/TASK-*.md` with `status: ready` sequentially before proceeding to the next. Once all tasks are written, report the generated files.

## Task Lifecycle

Tasks are written with `status: ready` by decompose. During execution, the executing agent updates the frontmatter:

- `in_progress` — work has started.
- `completed` — work is done and verified.

When significant decisions are made during execution — choices not already in Context, unexpected pivots, or user-directed changes — the executing agent records them in `## Implementation Decisions`.

## Reference

Template: `${CLAUDE_SKILL_DIR}/references/task-template.md`
