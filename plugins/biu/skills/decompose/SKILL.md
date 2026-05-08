---
name: decompose
description: Decompose .biu/SPEC.md into .biu/tasks/TASK-*.md handoff files.
disable-model-invocation: true
---

# Biu Decompose

Use this skill to turn `.biu/SPEC.md` into implementation tasks under `.biu/tasks/`.

## Workspace

`.biu/` must be git-ignored. Before writing, check `.gitignore` and add `.biu/` if missing.

```text
.biu/
├── SPEC.md							# Development Specification
├── tasks/							# Implementation Tasks
│   └── TASK-<short-name>.md
└── archived/						# Completed Cycles
	└── YYYY-MM-DD-NN/
		├── SPEC.md
		├── Summary.md
		└── tasks/
			└── TASK-<short-name>.md
```

`.biu/SPEC.md` is the required input. `.biu/tasks/` would contain TASK files for the current SPEC.

## Process

### Assess

Read `.biu/SPEC.md`. If `status` is not `ready`, or `## Open Questions` still has unresolved items, stop and tell the user to complete the SPEC via `/biu:interview` first.

### Decompose

Inspect code only as needed to identify natural task boundaries. Give each task a short unique name reflecting its objective.

Present a draft task list to the user before writing files. Explain:
- How the SPEC maps to these tasks.
- Dependencies between tasks.
- Which AC IDs each task covers.

Discuss and adjust until the user agrees on the shape.

### Check

Before writing, verify:

- Every AC in SPEC is covered by at least one task.
- Every `depends_on` reference resolves to another task in the set, and the dependency graph is acyclic.
- Each task has a single clear objective and is specific enough for another agent to execute without extra context.

Surface any issues and adjust with the user. After the checks pass and the user confirms, write `.biu/tasks/TASK-*.md` with `status: ready` using the template, then report the generated files.

## Task Lifecycle

Tasks are written with `status: ready` by decompose. During execution, the executing agent updates the frontmatter:

- `in_progress` — work has started.
- `completed` — work is done and verified.

## Reference

Template: `${CLAUDE_SKILL_DIR}/references/task-template.md`
