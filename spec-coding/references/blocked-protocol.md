# Blocked Protocol

## Trigger Conditions

Invoke this protocol when **any** of these conditions is met:

- A subtask has failed twice
- An implementation decision conflicts with **Assumptions & Constraints** and needs user input
- Enough new risks appear during execution that the current plan may be stale

Two failed attempts is the default limit. Do not keep trying the same subtask without changing the plan.

## Steps

1. **Stop the current Task immediately.** Do not move to another Task unless the user explicitly changes the plan.

2. **Update the progress file**:
   - Mark the stuck subtask as `[blocked]`
   - Add a note with the root cause, what was already attempted, and what is still unknown

3. **Update `COMPASS.md`**:
   - Change the parent Task entry to `- [blocked] Task N`
   - Update **Current Status**
   - Set **Active Task** to the blocked Task or `none`, whichever matches the current situation
   - Update **Next Step**
   - Add or refresh the related item in **Risk Watchlist** if needed

4. **Report to the user** with three things:
   - what is blocked and where
   - why it is blocked
   - what decision, information, or change is needed to unblock it

## After the User Responds

- If the user provides a decision: update **Assumptions & Constraints** in `COMPASS.md` if needed, restore the subtask from `[blocked]` to `[ ]`, restore the Task entry to `pending` or `active`, update **Current Status** and **Next Step**, and resume from the blocked subtask.
- If the user changes the plan: update `COMPASS.md` first, then update the affected progress files.
- If the user instructs you to skip this Task: mark it `done` in `COMPASS.md` with a `SKIPPED` note inline and move on only after the user confirms the next active Task.

**Do not proceed to the next Task unless the user explicitly resolves or changes the blocked plan.**
