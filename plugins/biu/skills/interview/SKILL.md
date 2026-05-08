---
name: interview
description: Interview the user to clarify intention & goal, and produce .biu/SPEC.md.
disable-model-invocation: true
---

# Biu Interview

Use this skill to turn a vague idea into a clear `.biu/SPEC.md`.

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

`.biu/SPEC.md` is the current spec. If it already exists, ask whether the user wants to continue refining it, make a local edit, or replace it.

## Process

### Interview

Start every interview by asking  the user's intention first. It may be ambiguous at the beginning, but we'll make it clearer in further interview.

Interview the user about literally anything: technical implementation, UI & UX, concerns, tradeoffs, acceptance criteria, etc. but make sure the questions are not obvious. Be very in depth and interviewing the user continually until the SPEC is complete.

You can suggest the user to read `SPEC.md` directly. In that way, your discussion would be more efficient.

### Draft and Refine

When enough context exists, create `.biu/SPEC.md` using the template, marking its status as `draft`.

Refine the spec alongside ongoing interviews; add, remove, or clarify sections as needed.

Only mark the status as `ready` after the user explicitly approves.

### Baseline

If the repository uses Git, record the current commit hash in `baseline_commit`. Leave it empty otherwise.

## Reference

Template: `${CLAUDE_SKILL_DIR}/references/spec-template.md`
