# Blocked Protocol

Load this file when a subtask fails twice in a row, or when you encounter a constraint conflict you cannot resolve without user input.

---

## Entering BLOCKED state

1. **In the Task file**:
   - Set **Status** to `BLOCKED`.
   - Set **Blocked by** to `[DECISION|TECHNICAL|INFO] <specific description>`.
   - Set **Resume point** to the current subtask number.
   - In **Notes**: record what was attempted and why it failed.

2. **In COMPASS.md Task Overview**:
   - Change the Task's symbol from `[~]` to `[!]`.

3. **Report to the user**:
   - What is blocked.
   - Why it's blocked (what was already tried).
   - What is needed to unblock (decision / information / technical solution).

---

## Exiting BLOCKED state

After the user provides a solution:

1. **In the Task file**:
   - Set **Status** to `IN_PROGRESS`.
   - Set **Blocked by** to `N/A`.
   - In **Notes**: add `YYYY-MM-DD: Unblocked — <solution>`.
   - Keep **Resume point** until that subtask is completed.

2. **In COMPASS.md Task Overview**:
   - Change the Task's symbol from `[!]` to `[~]`.

3. Continue from the Resume point.

---

## Skipping BLOCKED Tasks

If the user explicitly instructs to skip a blocked Task:

1. **In the Task file**:
   - Set **Status** to `SKIPPED`.
   - In **Notes**: record skip reason and potential impact.

2. **In COMPASS.md**:
   - Change the Task's symbol from `[!]` to `[-]` in Task Overview.
   - Append an entry to `## Skipped Tasks`: `Task N: <name> — Reason: <why skipped>`.

3. Continue to the next Task, but check dependencies before starting each subsequent Task.
