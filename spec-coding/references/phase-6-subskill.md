# Phase 6: Sub-skill Generation

**Goal**: Generate a project-scoped sub-skill that encodes this project's implementation standards and continuity protocol.

---

## Scope and Location

Install the sub-skill at **project scope only**: `.claude/skills/` in the project root (not `~/.claude/skills/`).

This sub-skill is tied to this development cycle. It is removed when the Archive Phase runs.

The sub-skill name should follow the pattern `spec-coding-<project-name>` where `<project-name>` is a short kebab-case identifier for the project.

---

## Generating the Sub-skill

Delegate creation to the **`skill-creator`** skill via the `Skill` tool. Provide it:
- The task context from COMPASS.md
- The sub-skill name
- The content outline below

**If `skill-creator` is not installed**: Tell the user it is required for this phase and instruct them to install it with: `npx skills add anthropics/skills --skill skill-creator`. Do not install it on their behalf. Once installed, return to this phase.

---

## Required Sub-skill Content

The generated sub-skill must instruct the agent to do the following.

### Session Startup (every conversation, non-negotiable)

1. Read `.spec/COMPASS.md` first — before any other file, before any action
2. Identify the active Task from the Task Overview table
3. Open that Task's progress file in `.spec/progress/`
4. Populate TaskCreate with all unchecked subtasks; set the current subtask to `in_progress`, remainder to `pending`
5. Re-read **Assumptions & Constraints** from COMPASS.md before touching any code

### During Implementation

- Before each implementation decision, check it against **Assumptions & Constraints** — if it conflicts, stop and invoke the Blocked Protocol rather than working around it
- After completing a subtask: check its box in the progress file, update the `(K/X)` count in COMPASS.md, and mark the TaskCreate item complete
- Record decisions, surprises, and discovered context in the **Notes** section of the progress file — not in conversation text
- Dual-write: TaskCreate for real-time visibility; Markdown files for cross-conversation persistence. Do not rely on TaskCreate alone.

### Blocked Protocol

Include the full content of `references/blocked-protocol.md` from the spec-coding skill directory verbatim in the sub-skill. Do not paraphrase it.

### Task Completion

- Verify all acceptance criteria before marking a Task complete
- Set progress file Status to `COMPLETE`
- Mark `[x]` in COMPASS.md Task Overview, update subtask count to `(X/X)`
- Update **Current Status** and **Next Steps** in COMPASS.md
- Check `milestones.md`: if this Task's completion satisfies a milestone's target criteria, update it to `[x]` in COMPASS.md and notify the user
- When all Tasks are `[x]`, trigger the Archive Phase automatically

### Project-Specific Standards

Fill in based on Phase 0 context and the analysis from Phase 1:
- Technology stack conventions and coding standards for this project
- Naming rules, file organization, structural conventions
- Testing requirements and what constitutes a passing subtask

---

## Phase Boundary

Phase 6 is complete when the sub-skill is installed and the user can confirm it is visible (e.g., via `/skills` or equivalent).

Proceed to Handoff.
