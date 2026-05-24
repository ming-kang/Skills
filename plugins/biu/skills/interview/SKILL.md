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

### Interview

`.biu/SPEC.md` is the current spec. If it already exists, ask whether the user wants to continue refining it, make a local edit, or replace it.

Start every interview by asking the user's intention first. It can be ambiguous at the start — the interview will sharpen it.

**Work in the open.** After the first substantive exchange — once you understand the basic intent — create `.biu/SPEC.md` as a rough skeleton. Fill in what you know (Goal, a tentative Scope, initial Open Questions). Leave the rest as placeholders. Don't wait until you have "enough context" in your head; the SPEC grows with the conversation.

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

### Baseline

If the repository uses Git, record the current commit hash in `baseline_commit`. Leave it empty otherwise.

## Reference

Template: `${CLAUDE_SKILL_DIR}/references/spec-template.md`
