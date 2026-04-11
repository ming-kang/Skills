# Blocked Protocol

## Trigger Conditions

Invoke this protocol when **either** condition is met:

- A subtask has failed twice — same approach or two different approaches have both failed
- An implementation decision conflicts with a constraint in **Assumptions & Constraints** and cannot be resolved without user input

Two failures is the limit. A third attempt without user input is not persistence — it is wasted context.

## Steps

1. **Stop immediately.** Do not attempt further workarounds or alternatives.

2. **Update the progress file**:
   - Set `**Status**` to `BLOCKED`
   - Fill `**Blocked by**` with the root cause and what was already attempted (be specific — "tried X, got error Y; tried Z, got error W")
   - Set `**Resume point**` to the exact subtask where you stopped

3. **Update COMPASS.md**:
   - Change the Task entry from `- [ ]` to `- [!]` and append `⚠ BLOCKED`
   - Update **Current Status** to reflect the blocked state

4. **Report to the user** with three things:
   - What is blocked and where (task + subtask)
   - Why it is blocked (root cause, not symptoms)
   - What decision or information is needed to unblock — be specific about the options

## After the User Responds

- If the user provides a decision: update **Assumptions & Constraints** in COMPASS.md if it changes a constraint, update `**Blocked by**` to `N/A`, restore `**Status**` to `IN_PROGRESS`, restore the Task entry to `- [ ]` in COMPASS.md, and resume from `**Resume point**`.
- If the user instructs you to skip this Task: set `**Status**` to `SKIPPED`, mark `- [~]` in COMPASS.md, and proceed to the next Task.

**Do not proceed to the next Task unless the user explicitly instructs you to skip this one.**
