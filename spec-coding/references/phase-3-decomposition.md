# Phase 3: Task Decomposition

**Goal**: Break the confirmed approach into concrete, trackable Tasks with no placeholders and clear acceptance criteria.

---

## Before You Begin

Confirm that `.spec/plan/` exists and that the two template files are in place:
- `.spec/plan/task-breakdown.md`
- `.spec/plan/milestones.md`

If they are missing, copy them from `assets/templates/plan/` in the spec-coding skill directory.

Confirm COMPASS.md contains a confirmed architecture direction. If it does not, Phase 2 was not completed — do not proceed.

---

## Dispatching the Plan Subagent

Read `references/subagents/plan-brief.md` for the prompt template. Fill in:
- The task definition from COMPASS.md
- The confirmed architecture direction from COMPASS.md
- The full Assumptions & Constraints from COMPASS.md

Dispatch Plan after the template is filled. Plan will read all three analysis files before producing output.

---

## Placeholder Enforcement

When Plan returns, scan both output files for forbidden patterns before accepting the output:

**Forbidden**: TBD, TODO, "implement later", "similar to Task N", "details to be determined", "to be specified", blank acceptance criteria fields, blank effort fields.

If any forbidden pattern is found: send Plan back with a list of every occurrence and the instruction to resolve each one before returning. Do not proceed to Phase 4 with an incomplete plan.

---

## Output: `.spec/plan/`

### `task-breakdown.md`
- Every Task with: description, priority (P0/P1/P2), effort (S/M/L/XL), dependencies, subtasks, acceptance criteria
- A Mermaid dependency graph showing Task relationships
- Tasks ordered by dependency: foundational before dependent

### `milestones.md`
- 3–5 milestones
- Each milestone is an end-to-end working state, a retired risk, or a deliverable — not just a Task completion
- Each milestone has explicit, demonstrable target criteria

---

## Phase Boundary

Phase 3 is complete when both plan files are filled, contain no forbidden patterns, and every Task has full detail.

Do not update COMPASS.md yet — that happens at the end of Phase 4 after user approval.
Proceed to Phase 4 immediately.
