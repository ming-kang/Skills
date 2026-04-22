# Implementation Phase

Load this file when you enter the Implementation Phase (Phase 4, after the Phase 3 hand-off is confirmed by the user).

---

## At the start of every Task

1. Read `.biu/COMPASS.md` for current position; re-read **Assumptions & Constraints** from `.biu/plan.md`.
2. In COMPASS.md Task Overview: change the corresponding line's symbol from `[ ]` to `[~]`.
3. Open the relevant `.biu/tasks/task-N-<name>.md` and set **Status** to `IN_PROGRESS`.

_Rationale_: COMPASS-first ordering keeps the Task Overview showing the intended active Task even if the turn is interrupted between steps 2 and 3; SKILL.md's Continuity Check reconciles any remaining mismatch on resume by trusting the task file (per Behavioral Rule `R-authority`, "Authority on disagreement").

## During each Task

- Work through subtasks one at a time.
- After completing a subtask:
  - Check its box in the Task file.
  - Immediately update the `(X/N)` count in COMPASS.md Task Overview.
- Record any decisions, surprises, or blockers in the Task file's **Notes** section.
- Record important technical decisions in COMPASS.md's **Decision Log** (append-only).

## When a subtask fails twice OR hits a constraint conflict

Invoke the Blocked Protocol immediately — see `blocked-protocol.md`.

## At the end of every Task

- Verify all acceptance criteria are met.
- Set the Task file's **Status** to `COMPLETE`.
- In COMPASS.md Task Overview: change the symbol from `[~]` to `[x]`.
- If any noteworthy decision or plan change came up, append to `## Decision Log`.
- Inform the user which Task was completed and what comes next.
- **STOP here.** Do NOT start the next Task automatically. Wait for the user to explicitly instruct "continue with Task N+1" (or equivalent). Auto-advancing to the next Task is a violation of the workflow contract.

## When all Tasks are complete

Inform the user and suggest archiving the cycle's artifacts. Wait for explicit confirmation, then load `archive.md`.

---

## Analysis Document Updates

If during implementation you discover the analysis is outdated:

- **Minor discrepancies** (don't affect overall plan): record in the Task file's Notes section only.
- **Major discrepancies** (affect subsequent Tasks):
  1. Pause current Task.
  2. Update the relevant analysis document(s).
  3. In `.biu/plan.md`'s `## Analysis` section, mark: `*(Updated YYYY-MM-DD)*`.
  4. Add entry to Decision Log: `Analysis updated: <reason>`.
  5. Evaluate if subsequent Tasks need adjustment:
     - Update affected Task files if needed; explain in Notes.
     - Create new Task files if necessary; update Task Overview.
  6. Report changes to user and confirm before continuing.
