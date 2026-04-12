# Blocked Protocol

## Trigger Conditions

Invoke this protocol only for the current `**ACTIVE**` Task.

Invoke this protocol when **any** of these conditions is met:

- A subtask has failed twice
- An implementation decision conflicts with **Assumptions & Constraints** and needs user input
- A required dependency is missing, unavailable, or inconsistent, and the current `**ACTIVE**` Task cannot continue without it
- A newly discovered risk affects the overall reliability of the current `COMPASS` plan
- A newly discovered risk is uncertain enough that user intervention is required before the current `**ACTIVE**` Task can continue

Do not invoke this protocol just because another Task is waiting on dependencies. Downstream waiting stays `**PENDING**`.
Task-local issues that can still be handled within the current Task belong in progress `Notes`. Risks that may affect other Tasks belong in `COMPASS.md > Risk Watchlist`.
Two failed attempts is the default limit. Do not keep trying the same subtask without changing the plan.

## Steps

1. **Stop the current Task immediately.** Do not move to another Task unless the user explicitly changes the plan.

2. **Update the progress file**:
   - Change `## Summary > **Status**` to `**BLOCKED**`
   - Mark the stuck subtask as `- [ ] N.x **BLOCKED**: <description>`
   - Add a note with the root cause, what was already attempted, and what is still unknown

3. **Update `COMPASS.md`**:
   - Change the parent Task entry to `- **BLOCKED** Task N`
   - Update **Current Status** to say which Task is blocked and what decision, input, or dependency is missing
   - Set **Active Task** to `none`
   - Add or refresh the related item in **Risk Watchlist** if needed
   - Leave downstream dependent Tasks as `**PENDING**`

4. **Report to the user** with three things:
   - what is blocked and where
   - why it is blocked
   - what decision, information, or change is needed to unblock it

## After the User Responds

- If the user provides a decision: update **Assumptions & Constraints** in `COMPASS.md` if needed, restore the blocked subtask to a normal unchecked line if work remains, restore the progress file `**Status**` and the parent Task entry to `**ACTIVE**` or `**PENDING**`, update **Current Status** and **Active Task**, then resume only when one Task is explicitly `**ACTIVE**`.
- If the user changes the plan: update `COMPASS.md` first, then update the affected progress files. Use `**PENDING**` for deferred Tasks unless the user explicitly reactivates one.
- If the user instructs you to skip this Task: mark it `**DONE**` in `COMPASS.md` with a `SKIPPED` note inline, change the progress file `**Status**` to `**DONE**`, record the skip reason in `Notes`, and move on only after the user confirms the next active Task or confirms final review.

**Do not proceed to the next Task unless the user explicitly resolves or changes the blocked plan.**
