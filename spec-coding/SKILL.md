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
5. **Only one active Task at a time.** Do not run multiple Tasks in parallel inside this workflow.
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

## Continuity Check

Before doing any work, inspect `.spec/` and determine which state you are in.

- **`COMPASS.md` exists**: Read it first. You are resuming the current cycle. Find the `active` or `blocked` Task and continue from there.
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
   - status: `pending`, `active`, `blocked`, or `done`
   - a short Task name
   - dependency information (`Depends on`)
   - a short acceptance summary
   - a link to its progress file
6. Create **all** progress files in `.spec/progress/` immediately after the Task list is approved. Planning and setup are done here, not during execution.
7. Add a short **Risk Watchlist** to `COMPASS.md`. Keep it to the few risks that matter right now. New risks found during execution may be added later.
8. Set exactly one Task to `active` when implementation is ready to begin. Leave the rest as `pending`.

### Planning Boundaries

- `COMPASS.md` is a summary document. Do not place subtask detail there.
- Progress files are created during planning, but they become the only place for subtask-level execution detail.
- If the user changes direction before implementation starts, update `COMPASS.md` and the relevant progress files before writing code.

---

## Capability 3: Task Execution

**Goal**: Execute one Task at a time, with detailed state recorded only in that Task's progress file.

### Start of Every Task

1. Read `.spec/COMPASS.md`.
2. Identify the single `active` Task.
3. Open that Task's progress file in `.spec/progress/`.
4. Re-read the Goal, Assumptions & Constraints, dependency notes, and Task acceptance summary before changing code.

### During Execution

- Work subtask by subtask inside the current progress file.
- Record real implementation detail in the progress file: decisions, surprises, verification, and blockers.
- Keep `COMPASS.md` at summary level. Do not mirror subtask detail there.
- If execution reveals a change that affects the overall cycle, update `COMPASS.md` after you have written the local detail in the progress file.

### Blocked Handling

See [references/blocked-protocol.md](references/blocked-protocol.md) for the full protocol.

Use the Blocked Protocol when:

- a subtask has already failed twice
- an implementation decision conflicts with Assumptions & Constraints and needs user input
- enough new risks appear that the current plan may no longer be trustworthy

When a subtask is blocked:

1. Mark that subtask `[blocked]` in the current progress file and write the exact reason there.
2. Mark the parent Task `blocked` in `COMPASS.md`.
3. Update `Current Status`, `Active Task`, `Next Step`, and the `Risk Watchlist` if needed.
4. Stop and ask the user to intervene.

Do **not** move to another Task unless the user explicitly changes the plan.

### Task Completion

When the current Task is complete:

1. Verify the Task against its acceptance summary and the progress file evidence.
2. Mark the Task `done` in `COMPASS.md`.
3. Update `Current Status` and `Active Task`.
4. If another pending Task is now unblocked and ready, mark that Task `active` and update `Next Step`.
5. If the Goal is complete, run the Archive step.

### Archive

When the cycle is complete:

1. If the project is a git repository, ask the user whether they want to record a final commit hash. Write the hash or `none (user skipped)` in `COMPASS.md`.
2. Create `.spec/archived/YYYY-MM-DD-NN/`.
3. Move the current `COMPASS.md` and the current `progress/` folder into that archive directory.
4. Leave `.spec/analysis/` and `.spec/archived/` in place for future cycles.
5. Confirm to the user what was archived and where.

After archive, a new cycle starts by creating a new `COMPASS.md` and a new `progress/` folder while reusing `analysis/`.
