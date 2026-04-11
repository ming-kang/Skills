# Phase 5: Progress Tracking Setup

**Goal**: Create the per-Task progress files and complete COMPASS.md so a fresh agent can orient itself in under 30 seconds.

---

## Step 1: Create Progress Files

For each Task in `task-breakdown.md`, create `.spec/progress/task-N-<short-name>.md`.

Use the template at `assets/templates/progress/task.md`. For each file:
- Copy the subtasks from `task-breakdown.md` for that Task
- Copy the acceptance criteria inline under each subtask
- Set `**Status**` in each progress file: `IN_PROGRESS` for the first Task, `PENDING` for all others
  (This is the progress file's own Status header — it uses the enum: PENDING | IN_PROGRESS | BLOCKED | COMPLETE | SKIPPED)
- COMPASS.md Task Overview uses `[ ]` checkboxes — those are separate and already templated; do not modify them here
- Leave Blocked by and Resume point as `N/A`
- Leave the Notes section empty

Naming convention: use a short (2-4 word) kebab-case name derived from the Task name.
Example: Task 3 "Refactor authentication layer" → `task-3-refactor-auth.md`

---

## Step 2: Complete COMPASS.md

Fill in the two remaining sections:

**Current Status**: "Phase 5 complete. Ready to begin Task 1: `<name>`."

**Next Steps**:
- Read `.spec/plan/task-breakdown.md` to understand the full scope
- Open `.spec/progress/task-1-<name>.md` and begin the first subtask
- Re-read Assumptions & Constraints before touching any code

---

## Phase Boundary

Phase 5 is complete when:
- One progress file exists per Task
- COMPASS.md Current Status and Next Steps are filled
- All template placeholders in progress files are replaced with actual content

Proceed to Phase 6.
