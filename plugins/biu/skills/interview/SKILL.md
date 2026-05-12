---
name: interview
description: Interview the user to clarify intention & goal, and produce .biu/SPEC.md.
disable-model-invocation: true
---

# Biu Interview

Use this skill to turn a vague idea into a clear `.biu/SPEC.md`.

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

### Interview

`.biu/SPEC.md` is the current spec. If it already exists, ask whether the user wants to continue refining it, make a local edit, or replace it.

Start every interview by asking the user's intention first. It may be ambiguous at the beginning — the interview will make it clearer.

Interview relentlessly about every aspect of the plan until a shared understanding is reached. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask one question at a time. If a question can be answered by exploring the codebase, explore the codebase instead of asking.

Push deeper on edge cases and error states — don't settle for the happy path. Never rush toward marking the SPEC as ready; the goal is thorough understanding, not speed.

You can suggest the user read `SPEC.md` directly — this makes discussion more efficient.

### Draft and Refine

When enough context exists, create `.biu/SPEC.md` using the template, marking its status as `draft`.

Refine the spec alongside ongoing interviews; add, remove, or clarify sections as needed.

Only mark the status as `ready` after the user explicitly approves.

### Baseline

If the repository uses Git, record the current commit hash in `baseline_commit`. Leave it empty otherwise.

## Reference

Template: `${CLAUDE_SKILL_DIR}/references/spec-template.md`
