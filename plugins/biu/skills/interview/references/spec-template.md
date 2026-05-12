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

## Background
<!--
✶ Include only if the Goal alone doesn't explain why this matters.
Ask: would someone unfamiliar with this project understand the motivation?
-->
<Context that Goal alone doesn't capture.>

## Scope
<!--
✶ Be specific. "User authentication" is vague;
"login, registration, password reset" is actionable.
-->
- <What this spec covers.>

## Non-Goals
<!--
✶ Boundaries prevent scope creep. Each item should name
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

## Decisions
<!--
Record key decisions made during the interview.
Each decision can include the alternatives that were rejected.
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
