---
name: spec-coding
description: >-
  Triggers when the user mentions "spec coding" / "spec-coding", or directly /spec-coding.
version: 1.1.4
---

# Spec-Coding

A skill for **Spec-Coding** workflow: Standardized development pipeline for complex tasks.

---

## Directory Structure

All spec-coding artifacts live under `.spec/`. This directory is **never committed to version control** — ensure `.spec/` is present in `.gitignore` before creating any files.

```
.spec/
├── COMPASS.md                    # Main control file — always read this first
├── analysis/
│   ├── project-overview.md
│   ├── module-inventory.md
│   └── risk-assessment.md
├── tasks/
│   └── task-N-<short-name>.md    # One file per Task
└── archived/
    └── YYYY-MM-DD-NN/            # Completed development cycles
        ├── COMPASS.md
        ├── analysis/
        └── tasks/
```

---

## Behavioral Rules

1. **Never skip User's Confirmation.** Confirm with the user at each phase boundary. This includes archiving — never archive without explicit user approval.
2. **Document decisions.** If you make a judgment call, record it in the relevant task file's Notes section.
3. **Progress updates are mandatory.** After completing any subtask, immediately update the checkbox AND COMPASS.md counts.
4. **New conversation = read COMPASS.md first.** Non-negotiable. It is your memory.
5. **Archive when done.** When all Tasks are complete, suggest archiving and wait for confirmation. Don't leave stale artifacts in the working area indefinitely.
6. **`.spec/` is always gitignored.** Verify this at the start of every fresh session before writing any files.
7. **Stop before you spiral.** If a subtask fails twice or hits a constraint conflict, invoke the Blocked Protocol immediately.

---

## Continuity Check

**CRITICAL**: Before starting any phase, check whether `.spec/COMPASS.md` exists.

- **If it exists**: Read it immediately. You are resuming an in-progress session. Identify the current phase or task, what has already been completed, and continue from exactly where the previous conversation ended. Do NOT restart from Phase 1.
- **If it does not exist**: This is a fresh start. Check whether `.spec/` is in `.gitignore`. If not, add it. Then proceed to *Begin: Intent Recognition*.

---

## Begin: Intent Recognition

**Goal**: Understand exactly what the user wants before any analysis begins.

**Actions**:

1. Ask the user to describe their goal if they haven't already. A brief description is enough — detailed planning questions will follow in Phase 2 after codebase analysis.

2. Confirm your understanding of the high-level intent with the user before proceeding.

**Output**: A rough task direction. Proceed to Phase 1.

---

## Phase 1: Deep Project Analysis

**Goal**: Build a comprehensive understanding of the current codebase.

**Action**: Spawn analyzer subagents that read `agents/analyzer.md`. Scale the number of subagents to the size and complexity of the codebase — more subagents for larger projects, a single one for small ones.

**Output**: Complete `.spec/analysis/` directory with three documents:
- `project-overview.md` — Architecture, tech stack, entry points, build system
- `module-inventory.md` — Every module with: responsibility, dependencies, size, complexity rating
- `risk-assessment.md` — Technical risks, compatibility risks, complexity hotspots

When analysis is complete, present a brief summary of findings to the user and confirm before proceeding to Phase 2.

---

## Phase 2: Plan Refinement

**Goal**: Refine the task definition using analysis findings, then lock in a confirmed plan.

**Action**: Use analysis findings to ask targeted clarifying questions with `AskUserQuestion`. Cover any concerns surfaced by analysis that affect scope, approach, or constraints.

**After confirming the plan**, create `.spec/COMPASS.md` with the following sections:

```markdown
# COMPASS

## Task Definition
<Confirmed description of what is being built or transformed>

## Assumptions & Constraints
<Non-negotiable boundaries, e.g.:>
- Must not break public API
- stdlib only
- Must support Node 18+

## Analysis
- [project-overview.md](./analysis/project-overview.md)
- [module-inventory.md](./analysis/module-inventory.md)
- [risk-assessment.md](./analysis/risk-assessment.md)

## Task Overview
<Populated by Phase 3>

## Current Status
Phase 2 complete. Proceeding to Phase 3: Task Decomposition.

## Next Steps
Spawn architect subagent to decompose the confirmed task.
```

**Output**: `.spec/COMPASS.md` with a confirmed task definition.

---

## Phase 3: Task Decomposition

**Goal**: Break the transformation into concrete, trackable Tasks organized into logical groups.

**Action**: Spawn an architect subagent that reads `agents/architect.md`. The architect reads both `.spec/COMPASS.md` and the analysis documents, then produces the task files and updates COMPASS.

**Output**: Complete `.spec/tasks/` directory with one file per Task, and COMPASS.md updated with the Task Overview.

When decomposition is complete, present the full task breakdown to the user and confirm before proceeding.

---

## Phase 4: Hand-off

**Goal**: Present all preparation artifacts and confirm readiness to begin implementation.

**Actions**:

1. Present a structured summary:
   - Confirmed task definition
   - Key findings from analysis
   - Task overview with task names and subtask counts

2. List all generated artifacts:
   ```
   .spec/
   ├── COMPASS.md
   ├── analysis/
   │   ├── project-overview.md
   │   ├── module-inventory.md
   │   └── risk-assessment.md
   └── tasks/
       └── task-N-*.md  (one per Task)
   ```

3. Ask the user: **"Preparation complete. Ready to start Implementation Phase?"**

**Output**: User confirmation to begin implementation.

---

## Implementation

**At the start of every Task**:
1. Read `.spec/COMPASS.md` to confirm current position and re-read **Assumptions & Constraints**
2. Open the relevant `.spec/tasks/task-N-<name>.md` and set **Status** to `IN_PROGRESS`

**During each Task**:
- Work through subtasks one at a time
- After completing a subtask: check its box in the task file, update the completion count in COMPASS.md
- Record any decisions, surprises, or blockers in the task file's Notes section

**Blocked Protocol** — if a subtask fails twice in a row, or if you encounter a constraint conflict you cannot resolve without user input:
1. Stop immediately. Do not attempt further workarounds.
2. Set the task file's **Status** to `BLOCKED`. Fill in **Blocked by** with the root cause and what was already attempted. Set **Resume point** to the current subtask.
3. Mark the Task as `[!] BLOCKED` in COMPASS.md and update **Current Status** accordingly.
4. Report to the user: what was blocked, why, and what decision or information is needed to unblock. Do not proceed to the next Task unless the user explicitly instructs you to skip this one.

**At the end of every Task**:
- Verify all acceptance criteria are met
- Set the task file's **Status** to `COMPLETE`
- Mark the Task complete in COMPASS.md
- Update **Current Status** and **Next Steps** in COMPASS.md
- Inform the user which Task was completed and what comes next

**When all Tasks are complete**: Inform the user that all Tasks are done and suggest archiving the cycle's artifacts. Wait for explicit confirmation before proceeding to the Archive phase.

---

## Archive

**Trigger**: All tasks in `.spec/COMPASS.md` are marked `[x]`, and the user has confirmed they are ready to archive.

**Goal**: Preserve this development cycle's artifacts so the next cycle starts clean.

**Actions**:

1. Announce to the user that all Tasks are complete.

2. Determine the archive folder name:
   - Format: `YYYY-MM-DD-NN` where `NN` is a two-digit sequence starting at `01`
   - Check `.spec/archived/` for existing folders with today's date and increment `NN` accordingly
   - Example: `.spec/archived/2026-04-13-01/`

3. Move all current working artifacts into the archive folder, preserving internal structure:
   ```
   .spec/archived/YYYY-MM-DD-NN/
   ├── COMPASS.md
   ├── analysis/
   └── tasks/
   ```

4. The `.spec/` root is now empty (except `archived/`), ready for the next development cycle.

5. Confirm to the user:
   - What was archived and where.
   - That `.spec/` is clean and ready for the next cycle.
   - Suggest committing any production code changes from this cycle to version control if not already done.

**Output**: A clean `.spec/` workspace. Past cycle preserved.

---

## Reference Files

The `agents/` directory contains instructions for specialized subagents. Read them when you need to spawn the relevant subagent.

- `agents/analyzer.md` — How to analyze the codebase and what to output.
- `agents/architect.md` — How to turn the confirmed plan into tasks and what to output.

The `references/templates/` directory contains document templates.

- `references/templates/analysis.md` — Templates for the three analysis documents.
- `references/templates/task.md` — Template for task files in `.spec/tasks/`.
