---
id: TASK-<short-name>
title: <Title>
status: ready | in_progress | completed
depends_on: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# TASK-<short-name>: <Title>

When executing this task, set frontmatter `status` to `in_progress` and update `updated` to today. When done, set `status` to `completed` and refresh `updated`.

## Objective

<What this task achieves and where it stops.>

## Context

<!--
What the executor needs to know:
- Key files to modify (with paths)
- Existing code to reuse (name + path + what it does)
- Patterns and conventions to follow
- Boundaries not to cross
- Design decisions already made
Cover only what reduces ambiguity — do not over-specify what can be left to the implementer.
-->

## Steps

- [ ] <Meaningful checkpoint. Design decisions belong in Context, not here.>
- [ ] <Meaningful checkpoint.>

## Verify

If a subagent is available, spawn one to verify this task independently — it must not modify any project files. Approach: <what to run and what edge cases to probe>.

**The goal is to break it, not confirm it works.** Do not read code and narrate — run it. Do not stop when the happy path works; test edge cases and error states.

- [ ] <Verifiable condition.>

## Covers

<!--
List the AC IDs from SPEC that this task contributes to.
-->

- AC1

## Implementation Decisions

<!--
Record key decisions made during execution that are not already captured in Context:
choices between approaches, responses to unexpected situations, direction changes prompted by the user.
Leave empty if no significant decisions were made.
-->

## Notes

<!--
Append notes freely during execution. Useful candidates: failures and what caused them,
ideas for improvement, observations worth preserving.
When in doubt, write it down.
-->

- <Note.>
