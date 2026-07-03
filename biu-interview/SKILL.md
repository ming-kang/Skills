---
name: biu-interview
description: Interview the user to clarify intention & goal, and produce a cycle SPEC.md under .biu/cycles/.
disable-model-invocation: true
---

# Biu Interview

Use this skill to turn a vague idea into a clear cycle SPEC at `.biu/cycles/<short-name>/SPEC.md`.

## Biu Workflow

<!-- Shared section: keep in sync across biu-interview / biu-decompose / biu-archive. -->

Biu provides three skills covering the full development cycle from idea to archive:

| Skill | Role |
|:-----:|:----:|
| `interview` | Clarify requirements through relentless interview, producing the cycle's `SPEC.md` |
| `decompose` | Decompose SPEC into `tasks/TASK-*.md` implementation handoffs |
| `archive` | Verify outcomes, distill learnings, and archive the completed cycle |

Typical usage: `biu-interview` -> `biu-decompose` -> Implement -> `biu-archive`

This is not a requirement. The user can skip or reorder them as needed.

### Directory Layout

```text
.biu/
├── LEARNINGS.md                    # Cross-cycle knowledge (append-only)
├── cycles/                         # Active cycles, one directory each
│   └── <short-name>/
│       ├── SPEC.md                 # Development Specification
│       └── tasks/                  # Implementation Tasks
│           └── TASK-<short-name>.md
└── archived/                       # Completed Cycles
    └── YYYY-MM-DD-<short-name>/
        ├── SPEC.md
        ├── Summary.md
        └── tasks/
            └── TASK-<short-name>.md
```

`LEARNINGS.md` carries knowledge across cycles: `interview` and `decompose` read it before starting, `archive` appends to it.

**Selecting the working cycle**: if the user named one, use it; if exactly one directory exists under `cycles/`, use it; if several exist, list them (with each SPEC's `owner`) and ask. Never maintain a "current cycle" pointer.

**Legacy layout**: if `.biu/SPEC.md` exists at the root (pre-cycles layout), migrate first — derive a short name from the SPEC title, create `.biu/cycles/<short-name>/`, move `SPEC.md` and `tasks/` into it, and tell the user. Leave `archived/` untouched.

### Version Control

Biu only reads from git (`rev-parse`, `diff`, `config`) and never writes to it — no `add`, `commit`, or `push`. It reminds the user to commit at natural points instead.

How `.biu/` relates to version control (never add or remove the `.gitignore` entry yourself):

- **Not a git repository** → plain local directory; omit git-derived fields (`owner`, `baseline_commit`).
- **Git repo, `.gitignore` does not mention `.biu/`** → `.biu/` is tracked (the default). Cycles, archives, and learnings are shared team assets.
- **Git repo, `.gitignore` ignores `.biu/`** → respect it; the user chose to keep biu private. Mention once that removing the line enables shared use.

## Process

### Interview

Read `.biu/LEARNINGS.md` first if it exists — past cycles may have settled decisions or documented pitfalls relevant to this one. Also scan the most recent archive's `Summary.md` for open `Gaps & Follow-Ups`, and surface any that relate to the new intention.

Determine the working cycle. Continuing an existing cycle under `.biu/cycles/` means refining its SPEC — ask whether the user wants to continue refining it, make a local edit, or replace it. A new intention means a new cycle: name its directory with a kebab-case `<short-name>` that reflects the goal.

Start every interview by asking the user's intention first. It can be ambiguous at the start — the interview will sharpen it.

**Work in the open.** After the first substantive exchange — once you understand the basic intent — create `.biu/cycles/<short-name>/SPEC.md` as a rough skeleton. Fill in what you know (Goal, a tentative Scope, initial Open Questions). Leave the rest as placeholders. Don't wait until you have "enough context" in your head; the SPEC grows with the conversation.

From there, iterate:

1. **Ask** one question following the Interview Rules below.
2. **Update the SPEC** — capture the answer immediately. Add sections, refine the Goal, narrow the Scope, record a Decision, close an Open Question. Don't batch updates; write them while they're fresh.
3. **Repeat** until the SPEC is solid.

Interview relentlessly about every aspect of the plan until you reach shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one by one.

**Interview Rules:**

1. **Strict Evidence Rule**  
   If a question can be answered by exploring the codebase (code, tests, docs), explore it directly. **Do not ask process questions** (e.g., "Should I check the code?"). Ask the user ONLY about product intent, preferences, scope boundaries, or risk tolerance.

2. **One Question at a Time**  
   Never overwhelm the user. Ask only one question per message.

3. **Structured Questions**  
   Each question MUST include:
   - The decision needed
   - Why the answer matters
   - Your recommended answer
   - Trade-offs if the user chooses differently

4. **Push Deeper**  
   Push on edge cases and error states — don't settle for the happy path. Never rush to mark the SPEC ready; the goal is thorough understanding, not speed.

5. **Scale Depth to Ambiguity**  
   Match interview depth to how unclear the goal is, not to its perceived size. A vague feature direction needs many rounds; a focused bug fix or well-scoped change needs only one or two. Don't pad with questions for completeness — when the SPEC is solid, stop.

You can ask the user to read `SPEC.md` directly — it makes discussion more efficient.

### Draft and Refine

The SPEC starts as a skeleton and solidifies through the Ask → Update → Repeat loop above. Keep `status` as `draft` throughout the interview.

As the SPEC matures, fill in sections that started as placeholders: Architecture and Design once the structure is clear, Risks as you identify them, Acceptance Criteria as decisions lock in. Add, remove, or clarify sections as the conversation evolves.

Before marking the status as `ready`, you MUST ensure:
- All Open Questions are resolved.
- Acceptance Criteria are strictly testable/verifiable.
- The user has explicitly approved the final state.

### Git Fields

If the repository uses Git, fill two frontmatter fields when creating the SPEC: record the current commit hash in `baseline_commit`, and the developer name from `git config user.name` in `owner`. Leave both empty otherwise.

## Reference

Template: `references/spec-template.md` relative to this skill directory.
