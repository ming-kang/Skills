# Task File Template

This template defines the structure for each `task-N-<short-name>.md` file in `.spec/tasks/`.

---

## Template

```markdown
# Task N: <Task Name>

**Status**: IN_PROGRESS | BLOCKED | COMPLETE
**Blocked by**: <describe the blocker, or N/A>
**Resume point**: <which subtask to continue from next session, or N/A>

---

## Goal

<One sentence: what does completing this task achieve?>

## Dependencies

<Tasks that must be complete before this one can start, or "None".>

## Subtasks

- [ ] <Subtask 1 — be specific: name the function, file, or line if known>
- [ ] <Subtask 2>
- [ ] <Subtask 3>
...

## Acceptance Criteria

- [ ] <Verifiable condition — prefer runnable checks over subjective ones>
- [ ] <e.g., "All existing tests pass with no modifications">
- [ ] <e.g., "`npm run build` completes without errors">
...

## Notes

<Decisions made, blockers encountered, surprises found during implementation. Add entries as you go.>

- **YYYY-MM-DD**: <note>
```

---

## Usage Notes

- **Status header**: Update `Status` to `IN_PROGRESS` when starting, `BLOCKED` when stuck, `COMPLETE` when done.
- **Blocked by**: Fill in when blocked — root cause + what was already attempted.
- **Resume point**: Set to the first unchecked subtask when leaving a task mid-session, so the next conversation knows exactly where to pick up.
- **Subtasks**: Write them in execution order. Each subtask should be completable in one focused step.
- **Notes**: Append, don't overwrite. This is a running log for cross-conversation context.
