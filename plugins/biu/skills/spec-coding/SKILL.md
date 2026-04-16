---
name: spec-coding
description: >-
  Triggers when the user mentions "spec coding" / "spec-coding", or directly /spec-coding.
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
2. **Document decisions.** Record important technical decisions and plan changes in COMPASS.md's Decision Log. Record implementation details in the relevant Task file's Notes section.
3. **Progress updates are mandatory.** After completing any subtask: check its box in the Task file, immediately update the (X/N) count in COMPASS.md.
4. **New conversation = read COMPASS.md first.** Non-negotiable. It is your memory.
5. **Archive when done.** When all Tasks are complete, suggest archiving and wait for confirmation. Don't leave stale artifacts in the working area indefinitely.
6. **`.spec/` is always gitignored.** Verify this at the start of every fresh session before writing any files.
7. **Stop before you spiral.** If a subtask fails twice or hits a constraint conflict, invoke the Blocked Protocol immediately.

---

## Continuity Check

**CRITICAL**: Before starting any phase, check whether `.spec/COMPASS.md` exists.

- **If it exists**: Read it immediately. You are resuming an in-progress session. Identify the current phase or Task, what has already been completed, and continue from exactly where the previous conversation ended. Do NOT restart from Phase 1.
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

**Action**: 
1. Use the Agent tool to spawn the `analyzer` subagent with the user's intent and codebase context
2. For large codebases, you may spawn multiple analyzer subagents in parallel to analyze different modules
3. Collect analyzer outputs and synthesize into the three analysis documents:
   - project-overview.md
   - module-inventory.md
   - risk-assessment.md

Example invocation:
```
Agent({
  description: "Analyze codebase for spec-coding Phase 1",
  subagent_type: "analyzer",
  prompt: "Analyze the codebase at [path] for [user's intent]. Focus on: structure, modules, architecture, and transformation risks."
})
```

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

## Skipped Tasks
<Populated during Implementation if Tasks are skipped>

## Decision Log
<Record important technical decisions and plan changes during Implementation>

## Current Status
Phase 2 complete. Proceeding to Phase 3: Task Decomposition.

## Next Steps
Spawn architect subagent to decompose the confirmed task.
```

**Output**: `.spec/COMPASS.md` with a confirmed task definition.

---

## Phase 3: Task Decomposition

**Goal**: Break the transformation into concrete, trackable Tasks organized into logical groups.

**Action**: Use the Agent tool to spawn the `architect` subagent. The architect reads both `.spec/COMPASS.md` and the analysis documents, then produces the Task files and updates COMPASS.

Example invocation:
```
Agent({
  description: "Decompose confirmed plan into tasks for spec-coding Phase 3",
  subagent_type: "architect",
  prompt: "Read .spec/COMPASS.md and all analysis documents. Break down the confirmed plan into concrete tasks with dependencies and acceptance criteria. Write task files to .spec/tasks/ and update COMPASS.md with the task overview."
})
```

**Output**: Complete `.spec/tasks/` directory with one file per Task, and COMPASS.md updated with the Task Overview.

When decomposition is complete, present the full task breakdown to the user and confirm before proceeding.

---

## Phase 4: Hand-off

**Goal**: Present all preparation artifacts and confirm readiness to begin implementation.

**Actions**:

1. Present a structured summary:
   - Confirmed task definition
   - Key findings from analysis
   - Task overview with Task names and subtask counts

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
3. In COMPASS.md: mark the Task as `[~]` and add `← Active` indicator

**During each Task**:
- Work through subtasks one at a time
- After completing a subtask: 
  - Check its box in the Task file
  - Immediately update the (X/N) count in COMPASS.md
- Record any decisions, surprises, or blockers in the Task file's Notes section
- Record important technical decisions in COMPASS.md's Decision Log

**Blocked Protocol** — if a subtask fails twice in a row, or if you encounter a constraint conflict you cannot resolve without user input:

**Entering BLOCKED state:**
1. In the Task file:
   - Set **Status** to `BLOCKED`
   - Set **Blocked by** to `[DECISION|TECHNICAL|INFO] <specific description>`
   - Set **Resume point** to the current subtask number
   - In **Notes**: record what was attempted and why it failed

2. In COMPASS.md:
   - Mark the Task as `[!]`
   - Update **Current Status** to `Task N blocked: <brief reason>`

3. Report to the user:
   - What is blocked
   - Why it's blocked (what was already tried)
   - What is needed to unblock (decision/information/technical solution)

**Exiting BLOCKED state:**

After the user provides a solution:
1. In the Task file:
   - Set **Status** to `IN_PROGRESS`
   - Set **Blocked by** to `N/A`
   - In **Notes**: add `YYYY-MM-DD: Unblocked — <solution>`
   - Keep **Resume point** until that subtask is completed

2. In COMPASS.md:
   - Change `[!]` to `[~]`
   - Update **Current Status** to `Task N resumed: <brief note>`

3. Continue from the Resume point

**Skipping BLOCKED Tasks:**

If the user explicitly instructs to skip a blocked Task:
1. In the Task file:
   - Set **Status** to `SKIPPED`
   - In **Notes**: record skip reason and potential impact

2. In COMPASS.md:
   - Change `[!]` to `[-]`
   - Add entry to **Skipped Tasks** section: `Task N: <name> — Reason: <why skipped>`

3. Continue to the next Task, but check dependencies before starting each subsequent Task

**At the end of every Task**:
- Verify all acceptance criteria are met
- Set the Task file's **Status** to `COMPLETE`
- In COMPASS.md: mark the Task as `[x]` and remove `← Active` indicator
- Update **Current Status** and **Next Steps** in COMPASS.md
- Inform the user which Task was completed and what comes next

**When all Tasks are complete**: Inform the user that all Tasks are done and suggest archiving the cycle's artifacts. Wait for explicit confirmation before proceeding to the Archive phase.

**Analysis Document Updates:**

If during implementation you discover the analysis is outdated:

- **Minor discrepancies** (don't affect overall plan): Record in the Task file's Notes section only
- **Major discrepancies** (affect subsequent Tasks):
  1. Pause current Task
  2. Update the relevant analysis document(s)
  3. In COMPASS.md Analysis section, mark: `*(Updated YYYY-MM-DD)*`
  4. Add entry to Decision Log: `Analysis updated: <reason>`
  5. Evaluate if subsequent Tasks need adjustment:
     - Update affected Task files if needed, explain in Notes
     - Create new Task files if necessary, update Task Overview
  6. Report changes to user and confirm before continuing

---

## Archive

**Trigger**: All Tasks in `.spec/COMPASS.md` are marked `[x]` or `[-]`, and the user has confirmed they are ready to archive.

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

The plugin's `agents/` directory contains specialized subagents that are automatically available when the biu plugin is enabled:

- `analyzer` — Codebase analysis subagent (invoked via Agent tool in Phase 1)
- `architect` — Task decomposition subagent (invoked via Agent tool in Phase 3)

The `references/templates/` directory contains document templates:

- `references/templates/analysis.md` — Templates for the three analysis documents
- `references/templates/task.md` — Template for task files in `.spec/tasks/`
