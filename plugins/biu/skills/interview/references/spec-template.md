---
title: <short title>
status: draft | ready
created: YYYY-MM-DD
updated: YYYY-MM-DD
baseline_commit: <sha or "none">
---

# SPEC: <short title>

## Goal
<!--
✶ 1-2 sentences. If you can't state it this concisely,
the interview hasn't gone deep enough — keep asking.
-->
<One or two sentences describing the problem to solve and the expected outcome.>

## Background & Facts
<!--
✶ Include only if the Goal alone doesn't explain why this matters.
✶ List concrete facts verified from the codebase during the interview
  (e.g., "The current API returns XML", "The DB already has a users table").
  This grounds downstream implementation tasks.
-->
<Context and verified current-state facts.>

## Scope
<!--
✶ Be specific. "User authentication" is vague;
"login, registration, password reset" is actionable.
-->
- <What this spec covers.>

## Non-Goals
<!--
✶ Boundaries prevent scope creep. Each item names
something you deliberately chose NOT to do and briefly why.
This section is as important as Scope — don't skip it.
-->
- <What this spec does NOT cover, and why.>

## Constraints
<!--
✶ Hard requirements. Ask explicitly: are there constraints
the user hasn't mentioned? Tech stack, deadlines, compatibility,
performance budgets — users often assume you already know.
-->
- <Hard requirements: tech, compatibility, deadlines, regulations.>

## Architecture
<!--
✶ Include when the task involves significant structural change.
Cover whatever is useful: current state, target state, key changes, diagrams.
Use the form that communicates structure most clearly — prose, ASCII, Mermaid, etc.
Omit for small self-contained changes.
-->
<Architectural context and/or target design.>

## Design
<!--
✶ Include when Architecture alone isn't enough to implement without ambiguity.
✶ Useful candidates: module responsibilities, key interfaces and contracts,
  data models, important flows or sequences, compatibility and migration notes.
✶ Cover only what reduces ambiguity — don't over-specify what can be left to the implementer.
-->
<Design details that matter for implementation.>

## Decisions
<!--
Record key decisions made during the interview.
Each decision can list the alternatives that were rejected.
-->

- **Decision**: <what we decided>
  - Reasoning: <why>
  - Alternatives considered: <what else we looked at and why it was rejected>

## Risks
<!--
✶ For each risk, ask: what's the worst case, and how likely is it?
Surface high-severity risks even if they seem unlikely —
those are the ones that sink projects.
-->
- **Risk**: <what could go wrong>
  - Impact: <what happens if it does>
  - Mitigation: <how we reduce likelihood or severity>

## Open Questions
<!--
This section MUST be EMPTY before the spec can be marked "ready".
Use it during drafting to track unresolved items.
-->

- [ ] <question>

## Acceptance Criteria
<!--
Stable IDs: AC1, AC2, ...
Editing text does not change the ID.
New items get the next integer; deleted IDs are never reused.
-->

- [ ] AC1: <Verifiable condition, e.g. "When X, then Y.">
- [ ] AC2: <Verifiable condition.>
