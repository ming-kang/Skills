# Implementation Phase

Load this file when you enter the Implementation Phase (after Phase 4 hand-off is confirmed by the user).

---

## At the start of every Task

1. Read `.spec/COMPASS.md` to confirm current position and re-read **Assumptions & Constraints**.
2. Open the relevant `.spec/tasks/task-N-<name>.md` and set **Status** to `IN_PROGRESS`.
3. In COMPASS.md: mark the Task as `[~]` and add `← Active` indicator.

## During each Task

- Work through subtasks one at a time.
- After completing a subtask:
  - Check its box in the Task file.
  - Immediately update the `(X/N)` count in COMPASS.md.
- Record any decisions, surprises, or blockers in the Task file's **Notes** section.
- Record important technical decisions in COMPASS.md's **Decision Log**.

## When a subtask fails twice OR hits a constraint conflict

Invoke the Blocked Protocol immediately — see `blocked-protocol.md`.

## At the end of every Task

- Verify all acceptance criteria are met.
- Set the Task file's **Status** to `COMPLETE`.
- In COMPASS.md: mark the Task as `[x]` and remove the `← Active` indicator.
- Update **Current Status** and **Next Steps** in COMPASS.md.
- Inform the user which Task was completed and what comes next.

## When all Tasks are complete

Inform the user and suggest archiving the cycle's artifacts. Wait for explicit confirmation, then load `archive.md`.

---

## Analysis Document Updates

If during implementation you discover the analysis is outdated:

- **Minor discrepancies** (don't affect overall plan): record in the Task file's Notes section only.
- **Major discrepancies** (affect subsequent Tasks):
  1. Pause current Task.
  2. Update the relevant analysis document(s).
  3. In COMPASS.md Analysis section, mark: `*(Updated YYYY-MM-DD)*`.
  4. Add entry to Decision Log: `Analysis updated: <reason>`.
  5. Evaluate if subsequent Tasks need adjustment:
     - Update affected Task files if needed; explain in Notes.
     - Create new Task files if necessary; update Task Overview.
  6. Report changes to user and confirm before continuing.
