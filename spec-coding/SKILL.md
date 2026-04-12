---
name: spec-coding
description: >-
  Triggers only when the user wants to do spec coding.
disable-model-invocation: true
metadata:
  version: "2.1.0"
---

# Spec-Coding

You are executing the **Spec-Coding** workflow — a modular workflow for complex development.

This skill is organized into three capability modules: **Project Analysis**, **Goal & Task Planning**, and **Task Execution**. Use the section that matches the current need, but keep the shared state model consistent across all three.

If a file or tool mentioned here is unavailable, use the closest equivalent available in your environment and preserve the workflow behavior.

---

## Shared Rules

1. **Read state before acting.** If `.spec/COMPASS.md` exists, read it first. If not, start with `.spec/analysis/`.
2. **`COMPASS.md` is the control file for the current cycle.** It holds the Goal, Task overview, current status, and the global Risk Watchlist.
3. **Progress files are task-local.** Subtasks, detailed notes, verification, and blocked context belong in `.spec/progress/task-N-<name>.md`.
4. **No implementation before plan approval.** Analysis and planning come first; code starts only after the Goal and Task list are confirmed.
5. **Only one `ACTIVE` Task at a time.** Do not run multiple Tasks in parallel inside this workflow.
6. **Blocked means stop.** Do not silently move to the next Task; update state and ask the user to resolve it.
7. **Verify before claiming done.** If something was not verified, say so explicitly in the progress file and to the user.
8. **Keep project facts separate from cycle decisions.** `.spec/analysis/` is long-lived; cycle-specific decisions belong in `COMPASS.md` and progress files.
9. **Use behavior, not tool names, as the source of truth.** If the environment changes, preserve the workflow intent rather than a specific command or UI.
10. **Archive only cycle docs.** `analysis/` stays in place across cycles; archive `COMPASS.md` and `progress/` when the cycle is finished.
11. **Keep `.spec/` out of version control.** In a fresh project, ensure `.spec/` is gitignored before writing cycle files.

---

## Directory Structure

All spec-coding artifacts live under `.spec/`. `analysis/` is reusable project memory; `COMPASS.md` and `progress/` belong to the current development cycle.

```
.spec/
├── analysis/
│   ├── architecture.md           # Reusable project-level facts
│   └── module-map.md             # Reusable module and dependency map
├── archived/
│   └── YYYY-MM-DD-NN/
│       ├── COMPASS.md
│       └── progress/
├── COMPASS.md                    # Current cycle control file
└── progress/
    └── task-N-<short-name>.md    # One file per Task in the current cycle
```

Templates for all files above are in the skill directory at `assets/templates/`.

---

## Task State Model

Use the same Task-level states everywhere in the current cycle:

- `**PENDING**`
- `**ACTIVE**`
- `**BLOCKED**`
- `**DONE**`

### Where Each State Appears

- In `COMPASS.md`, write Task states as `**PENDING**`, `**ACTIVE**`, `**BLOCKED**`, or `**DONE**`.
- In each progress file, keep `## Summary > **Status**` aligned with the same Task-level state shown in `COMPASS.md`.
- Inside `## Subtasks`, use markdown checkboxes for subtask progress:
  - `[ ]` for not done yet
  - `[x]` for done
  - `- [ ] N.x **BLOCKED**: <subtask description>` when a specific subtask is blocked
- Write blocked detail, attempts, and missing decisions in `## Notes`, not in the subtask line itself.

### State Definitions

- **`PENDING`**: The Task belongs to the current cycle but is not being worked right now. This may mean not started yet, waiting on dependencies, or deliberately deferred. Use `Depends on`, `Current Status`, `Next Step`, and notes to explain which case applies.
- **`ACTIVE`**: The single Task currently being executed. Only one Task may be `ACTIVE` at a time.
- **`BLOCKED`**: The current interruption point. This Task cannot continue without user input, missing information, or a plan change. Do not silently move to another Task.
- **`DONE`**: The Task is closed for the current cycle. Usually this means completed with verification. If the user explicitly skips or cancels it, it may still be marked `DONE`, but the reason must be recorded clearly.

### Transition Rules

- `**PENDING** -> **ACTIVE**`: Allowed when dependencies are satisfied, the user has approved execution, and no other Task is `ACTIVE`.
- `**PENDING** -> **DONE**`: Allowed only when the user explicitly cancels or skips the Task.
- `**ACTIVE** -> **DONE**`: Allowed after acceptance is met and verification is recorded.
- `**ACTIVE** -> **BLOCKED**`: Allowed when blocked conditions are met.
- `**ACTIVE** -> **PENDING**`: Allowed only when the user explicitly changes the plan and defers the current Task.
- `**BLOCKED** -> **ACTIVE**`: Allowed when the user resolves the block and execution resumes on the same Task.
- `**BLOCKED** -> **PENDING**`: Allowed when the user decides to defer the blocked Task instead of resolving it now.
- `**BLOCKED** -> **DONE**`: Allowed only when the user explicitly skips or cancels the Task.
- `**DONE** -> **PENDING**` or `**DONE** -> **ACTIVE**`: Avoid by default. Reopen only if the earlier `DONE` judgment was wrong. If scope expands, create a new Task instead.

### Dependency and Active Task Rules

- `Depends on` controls readiness, not automatic status changes.
- If Task N is `BLOCKED`, downstream Tasks that depend on it stay `**PENDING**`. Do not automatically mark them `**BLOCKED**`.
- `**Active Task**` in `COMPASS.md` must name the current `Task N` when one Task is `ACTIVE`.
- Set `**Active Task**` to `none` whenever no Task is currently executable, including blocked waiting states and final review before archive.

---

## Continuity Check

Before doing any work, inspect `.spec/` and determine which state you are in.

- **`COMPASS.md` exists**: Read it first. You are resuming the current cycle. If there is one `**ACTIVE**` Task, continue there. If the cycle is `**BLOCKED**` or `**Active Task**` is `none`, resolve the current waiting state before implementation resumes.
- **`COMPASS.md` is missing but `progress/` contains files**: Treat this as an ambiguous state. Inspect the progress files, summarize what you found, and ask the user whether to resume, rebuild `COMPASS.md`, or archive the stale cycle before proceeding.
- **Only `analysis/` exists**: Treat this as a fresh cycle on an already-known project. Reuse the analysis after a quick freshness check.
- **Nothing under `.spec/` exists yet**: Fresh start. Ensure `.spec/` is gitignored, then begin with Project Analysis.

Do not overwrite an unfinished cycle silently.

---

## Capability 1: Project Analysis

**Goal**: Build and maintain reusable project-level facts in `.spec/analysis/`.

### When to Run

- The project is new to this workflow
- `.spec/analysis/` is missing
- The repo changed enough that the analysis may be stale
- The current Goal touches an area that is not covered well enough in the existing analysis

### Output

- `.spec/analysis/architecture.md`
- `.spec/analysis/module-map.md`

### How to Work

1. Read the repository guidance that exists (`README.md`, `CLAUDE.md`, `AGENTS.md`, and similar files).
2. Scan the project structure and stack signals.
3. If analysis files already exist, read them before re-scanning the codebase.
4. Refresh only the sections that are stale or missing. Do not rewrite long-lived project facts just because a new cycle started.
5. Keep this capability factual. Do not mix in cycle-specific plans, risk logs, or execution status.

### File Requirements

- **`architecture.md`** must capture the tech stack, entry points, common commands, external integrations, and a concise architecture summary.
- **`module-map.md`** must capture the significant modules or architectural areas that matter to future planning, including responsibilities and dependency shape.
- Skip truly trivial files. This is a planning aid, not a full inventory dump.

### Freshness Check

Before reusing old analysis, quickly confirm that the tech stack, entry points, and major modules still match reality. If they do not, update the analysis before planning.

---

## Capability 2: Goal & Task Planning

**Goal**: Turn the user's request into an approved Task set for the current cycle.

### Inputs

- The user's request
- `.spec/analysis/`
- Relevant archived cycles, if they help clarify prior decisions

### How to Work

1. Build shared context through normal conversation. Confirm the Goal, scope, hard constraints, and priorities.
2. When tradeoffs matter, present 2–3 implementation options. Always include one conservative option. State your recommendation directly.
3. Get explicit user approval on the chosen direction before implementation begins.
4. Create or replace `.spec/COMPASS.md` from the template.
5. Write the Task overview directly into `COMPASS.md`. Each Task entry must include:
   - status: `**PENDING**`, `**ACTIVE**`, `**BLOCKED**`, or `**DONE**`
   - a short Task name
   - dependency information (`Depends on`)
   - a short acceptance summary
   - a link to its progress file
6. Create **all** progress files in `.spec/progress/` immediately after the Task list is approved. Planning and setup are done here, not during execution.
7. Add a short **Risk Watchlist** to `COMPASS.md`. Keep it to the few risks that matter right now. New risks found during execution may be added later.
8. Set exactly one Task to `**ACTIVE**` when implementation is ready to begin. Leave the rest as `**PENDING**`. Mirror those same Task-level states in each progress file summary.

### Planning Boundaries

- `COMPASS.md` is a summary document. Do not place subtask detail there.
- Progress files are created during planning, but they become the only place for subtask-level execution detail.
- If the user changes direction before implementation starts, update `COMPASS.md` and the relevant progress files before writing code.

---

## Capability 3: Task Execution

**Goal**: Execute one Task at a time, with detailed state recorded only in that Task's progress file.

### Start of Every Task

1. Read `.spec/COMPASS.md`.
2. Identify the single `**ACTIVE**` Task. If `**Active Task**` is `none`, inspect `Current Status` before doing any implementation. You may be waiting on blocked resolution, final review, or an explicit plan update.
3. Open that Task's progress file in `.spec/progress/`.
4. Re-read the Goal, Assumptions & Constraints, dependency notes, and Task acceptance summary before changing code.

### During Execution

- Work subtask by subtask inside the current progress file.
- Record real implementation detail in the progress file: decisions, surprises, verification, and blockers.
- Keep the progress file `**Status**` aligned with the parent Task state in `COMPASS.md`.
- Keep `COMPASS.md` at summary level. Do not mirror subtask detail there.
- If execution reveals a change that affects the overall cycle, update `COMPASS.md` after you have written the local detail in the progress file.

### Risk Recording and Escalation

When execution reveals a new risk, record it in the current progress file `## Notes` first.

Then decide whether it stays task-local, becomes cross-task tracking, or escalates to `**BLOCKED**`:

- Keep it in `Notes` only when it affects only the current Task's execution and can still be handled within the current Task.
- Add or refresh an item in `COMPASS.md > Risk Watchlist` when it may affect other Tasks, later verification, or later planning decisions across the current cycle.
- Escalate to `**BLOCKED**` when it affects the overall reliability of the current `COMPASS` plan, or when it is uncertain enough that user intervention is required before the current `**ACTIVE**` Task can continue.

`Risk Watchlist` is for cross-task visibility, not for local implementation noise.
Keep it short, summary-level, and limited to unresolved risks that still matter to the current cycle.

### Blocked Handling

See [references/blocked-protocol.md](references/blocked-protocol.md) for the full protocol.

Use the Blocked Protocol when:

- a subtask has already failed twice
- an implementation decision conflicts with Assumptions & Constraints and needs user input
- a required dependency is missing or unavailable and the current `**ACTIVE**` Task cannot continue without it
- a newly discovered risk affects the overall `COMPASS` plan or requires user intervention before the current `**ACTIVE**` Task can continue

When a subtask is blocked:

1. Mark that subtask as `- [ ] N.x **BLOCKED**: <description>` in the current progress file and write the exact reason in `Notes`.
2. Change the current progress file `**Status**` to `**BLOCKED**`.
3. Mark the parent Task `**BLOCKED**` in `COMPASS.md`.
4. Set `**Active Task**` to `none`.
5. Leave downstream dependent Tasks as `**PENDING**`. Do not mark them `**BLOCKED**` automatically.
6. Update `Current Status`, `Next Step`, and the `Risk Watchlist` if needed.
7. Stop and ask the user to intervene.

Do **not** move to another Task unless the user explicitly changes the plan.

### Task Completion

When the current Task is complete:

1. Verify the Task against its acceptance summary and the progress file evidence.
2. Mark the current progress file `**Status**` as `**DONE**`.
3. Mark the Task `**DONE**` in `COMPASS.md`.
4. Update `Current Status` and `Active Task`.
5. If another `**PENDING**` Task is now unblocked and ready, mark that Task `**ACTIVE**` and update `Next Step`.
6. If the Goal is complete, run the Final Review Checkpoint before Archive.

### Final Review Checkpoint

When the last Task becomes `**DONE**`:

1. Set `**Active Task**` to `none`.
2. Ask the user whether `.spec/analysis/` should be refreshed before archive.
3. If the user wants an analysis refresh, update `.spec/analysis/` first and summarize what changed.
4. Ask the user to review the completed cycle and confirm whether a final commit hash should be recorded.
5. Only proceed to archive after the user explicitly confirms the cycle is ready.

### Archive

When the user has confirmed the cycle is ready:

1. If the project is a git repository and the user wants to record a final commit hash, write the confirmed hash in `COMPASS.md`. Otherwise write `none (user skipped)`.
2. Create `.spec/archived/YYYY-MM-DD-NN/`.
3. Move the current `COMPASS.md` and the current `progress/` folder into that archive directory.
4. Leave `.spec/analysis/` and `.spec/archived/` in place for future cycles.
5. Confirm to the user what was archived and where.

After archive, a new cycle starts by creating a new `COMPASS.md` and a new `progress/` folder while reusing `analysis/`.
