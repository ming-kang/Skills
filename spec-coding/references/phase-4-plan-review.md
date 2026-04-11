# Phase 4: Plan Review & Approval

**Goal**: Get explicit user approval on the complete plan before any implementation begins. No code, no scaffolding, no pseudo-code until the user approves.

---

## Step 1: Present the Plan

Present the plan in a readable summary — do not paste the raw files. Cover:

1. **Task overview**: All Tasks with names, priorities, effort estimates, and dependencies (a table works well)
2. **Milestone overview**: All milestones and their target criteria
3. **Total scope**: Rough sense of overall effort (sum of estimates, number of Tasks)
4. **Key risks that the plan addresses**: Tie back to the risk register — how does the plan handle the top risks?

---

## Step 2: Invite Scrutiny

Explicitly ask the user to check:
- Are all the right things included?
- Is anything scoped too broadly or too narrowly?
- Do the priorities look right?
- Are the acceptance criteria strong enough?

Do not rush this. A plan with a wrong Task is worse than a slower review.

---

## Step 3: Handle Feedback

When the user requests changes, diagnose the root cause of the feedback before acting:

| Feedback type | Root cause | Action |
|--------------|-----------|--------|
| Task description unclear, wrong granularity, missing functionality | Plan subagent output is incomplete | Return to Phase 3: re-dispatch Plan with corrected instructions |
| Analysis missed a module, misread the tech stack, major factual gap | Phase 1 analysis is wrong | Return to Phase 1: dispatch targeted Explore for the missed area, update the analysis file, then re-run Phase 3 |
| Confirmed architecture direction is wrong | Phase 2 decision was wrong | Return to Phase 2: re-present options with the new information, get a new confirmation, then re-run Phase 3 |
| Scope or constraints changed | Phase 0 assumptions are outdated | Update Assumptions & Constraints in COMPASS.md, then return to Phase 2 or Phase 3 as appropriate |
| Minor wording fix, small reprioritization, cosmetic change | No root cause — surface fix only | Edit the plan file directly, no phase return needed |

State the diagnosis to the user before acting: "This looks like a Phase 3 issue — the analysis is correct but the decomposition missed X. I'll re-run the planner with updated instructions." Confirm with the user before returning to a prior phase.

---

## Phase Boundary

Phase 4 is complete when the user explicitly approves the plan (e.g., "looks good", "approved", "proceed").

Update COMPASS.md:
- Add links to both plan documents in the Plan section
- Fill in the Task Overview table (all Tasks, initial status 0/X subtasks)
- Fill in the Milestones table (all milestones, initial status pending)

Then proceed to Phase 5.
