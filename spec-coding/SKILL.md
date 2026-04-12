---
name: spec-coding
description: >-
  Triggers only when the user wants to do spec coding.
disable-model-invocation: true
metadata:
  version: "2.4.0"
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
5. **Only one `ACTIVE` Task at a time.** Do not run multiple Tasks in parallel inside this workflow. Zero `ACTIVE` Tasks is valid when the cycle is waiting for user instruction.
6. **Blocked means stop.** Do not silently move to the next Task; update state and ask the user to resolve it.
7. **Verify before claiming done.** If something was not verified, say so explicitly in the progress file and to the user.
8. **Keep project facts separate from cycle decisions.** `.spec/analysis/` is long-lived; cycle-specific decisions belong in `COMPASS.md` and progress files.
9. **Execution must be document-driven.** A Task may enter execution only when an agent can carry it out by reading `.spec/analysis/`, `.spec/COMPASS.md`, and the current `task-N-<name>.md`, without relying on unstated chat context.
10. **Use behavior, not tool names, as the source of truth.** If the environment changes, preserve the workflow intent rather than a specific command or UI.
11. **Archive only cycle docs.** `analysis/` stays in place across cycles; archive `COMPASS.md` and `progress/` when the cycle is finished.
12. **Keep `.spec/` out of version control.** In a fresh project, ensure `.spec/` is gitignored before writing cycle files.
13. **`Risk Watchlist` is a working list, not an archive log.** Before archive it should be empty. If the user explicitly accepts a residual risk, move the summary into `## Final Review` and then clear it from `Risk Watchlist`.

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

- **`PENDING`**: The Task belongs to the current cycle but is not currently in progress. This may mean not started yet, waiting on dependencies, waiting on user instruction, or deliberately deferred. Use `Depends on`, `Current Status`, and notes to explain which case applies.
- **`ACTIVE`**: The single Task currently in progress. Only one Task may be `ACTIVE` at a time.
- **`BLOCKED`**: The current interruption point. This Task cannot continue without user input, missing information, or a plan change. Do not silently move to another Task.
- **`DONE`**: The Task is closed for the current cycle. Usually this means completed with verification. If the user explicitly skips or cancels it, it may still be marked `DONE`, but the reason must be recorded clearly.

### Transition Rules

- `**PENDING** -> **ACTIVE**`: Allowed when dependencies are satisfied, the user has explicitly approved starting or resuming execution, the progress file is execution-ready, and no other Task is `ACTIVE`.
- `**PENDING** -> **DONE**`: Allowed only when the user explicitly cancels or skips the Task.
- `**ACTIVE** -> **DONE**`: Allowed after acceptance is met and verification is recorded.
- `**ACTIVE** -> **BLOCKED**`: Allowed when blocked conditions are met.
- `**ACTIVE** -> **PENDING**`: Allowed only when the user explicitly changes the plan and defers the current Task.
- `**BLOCKED** -> **ACTIVE**`: Allowed when the user resolves the block and explicitly resumes the same Task.
- `**BLOCKED** -> **PENDING**`: Allowed when the user decides to defer the blocked Task instead of resolving it now.
- `**BLOCKED** -> **DONE**`: Allowed only when the user explicitly skips or cancels the Task.
- `**DONE** -> **PENDING**` or `**DONE** -> **ACTIVE**`: Avoid by default. Reopen only if the earlier `DONE` judgment was wrong. If scope expands, create a new Task instead.

### Dependency and Active Task Rules

- `Depends on` controls readiness, not automatic status changes.
- If Task N is `BLOCKED`, downstream Tasks that depend on it stay `**PENDING**`. Do not automatically mark them `**BLOCKED**`.
- `**Active Task**` in `COMPASS.md` must name the current `Task N` when one Task is `ACTIVE`.
- Set `**Active Task**` to `none` whenever no Task is currently in progress, including after planning is complete but implementation has not started, between Tasks while waiting for user instruction, blocked waiting states, and final review before archive.

---

## Continuity Check

Before doing any work, inspect `.spec/` and determine which cycle state you are in.

- **Valid waiting state**: `COMPASS.md` exists, the Task list and progress files are consistent, and `**Active Task**` is `none`. Common cases: planning is complete but implementation has not started; a Task just finished and the next Task has not been started; the cycle is blocked and waiting on user input; final review is waiting for archive. Summarize the current status to the user and wait for instruction. Do not auto-start a Task.
- **Valid execution state**: `COMPASS.md` exists, exactly one Task is `**ACTIVE**`, `**Active Task**` points to it, and the matching progress file exists with aligned status. Continue that Task.
- **Invalid state**: The cycle control files are inconsistent or incomplete. Examples: `COMPASS.md` is missing while `progress/` exists, more than one Task is `**ACTIVE**`, `**Active Task**` disagrees with the Task list, a Task is missing its progress file, Task and progress-file statuses conflict, or a dependency points to a missing Task. Stop, summarize the inconsistency, and ask the user how to proceed. Do not reconstruct missing control files automatically.
- **Only `analysis/` exists**: Treat this as a fresh cycle on an already-known project. Reuse the analysis after a quick freshness check.
- **Nothing under `.spec/` exists yet**: Fresh start. Ensure `.spec/` is gitignored, then begin with Project Analysis.

Do not overwrite an unfinished cycle silently. Do not reconstruct missing cycle control files without explicit user instruction.

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

- **Every analysis file must include `## Baseline Reference`.** Record:
  - `Checked against`: the git commit that the file was checked against, or `none (non-git repo)`
  - `Working tree`: `clean` or `dirty`
  - `Checked on`: `YYYY-MM-DD`
  - `Review type`: `full refresh` or `targeted revalidation`
- **`architecture.md`** must capture the tech stack, entry points, common commands, external integrations, and a concise architecture summary.
- **`module-map.md`** must capture the significant modules or architectural areas that matter to future planning, including responsibilities and dependency shape.
- Skip truly trivial files. This is a planning aid, not a full inventory dump.

### Freshness Check

Before reusing old analysis, check the `## Baseline Reference` in each analysis file and then confirm that the documented facts still match reality.

Use this process:

1. If `## Baseline Reference` is missing, treat the file as needing review and add the section when you finish.
2. If the project is a git repository, compare the current repo state with the recorded baseline commit and working-tree state.
3. If the recorded baseline says `dirty`, do not rely on commit-only comparison. Re-scan the relevant project areas directly.
4. If only the covered area needs confirmation and the facts still hold, do a `targeted revalidation`.
5. If the structure, stack, entry points, commands, integrations, or module boundaries changed materially, do a `full refresh`.
6. After any review that confirms or updates an analysis file, update its `## Baseline Reference` to reflect the current state.

Treat `architecture.md` and `module-map.md` independently. One may need a refresh while the other only needs revalidation.

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
7. Fill each progress file during planning until it is ready for execution. The progress file, not the chat transcript, is the task-level handoff.
8. Add a short **Risk Watchlist** to `COMPASS.md`. Keep it to the few risks that matter right now. New risks found during execution may be added later.
9. When planning is complete, keep all not-yet-started Tasks as `**PENDING**` unless the user explicitly instructs you to start one immediately. Mirror those same Task-level states in each progress file summary.
10. If planning is complete and implementation has not started, set `**Current Status**` to say that planning is finished and execution is waiting for user instruction. Set `**Active Task**` to `none`.

### Planning Boundaries

- `COMPASS.md` is a summary document. Do not place subtask detail there.
- Progress files are created during planning, and they must already contain the task-level detail needed for execution.
- Task-level implementation instructions belong in the progress file, not in unstated chat context.
- If the user changes direction before implementation starts, update `COMPASS.md` and the relevant progress files before writing code.

### Definition of Ready for Execution

A Task may enter execution only when its progress file includes all of the following:

- `## Summary` with aligned status, dependency notes, and acceptance summary
- `## Task Context` explaining why this Task exists and how it serves the current Goal
- `## Scope` with both `In scope` and `Out of scope`
- `## Touchpoints` listing the main files, modules, interfaces, configs, or tests expected to matter
- `## Subtasks` broken into concrete execution units; each subtask must say what changes, what it touches, and what "Done when" means
- `## Verification Plan` with planned commands or checks and the expected signals
- `## Open Questions` set to `none`, or every remaining gap is explicitly covered by an assumption in `COMPASS.md`
- `## Execution Notes` with order, compatibility requirements, or "do not change" constraints that matter during implementation

Do not mark a Task `**ACTIVE**` until this bar is met.

---

## Capability 3: Task Execution

**Goal**: Execute one approved Task at a time, using the current cycle docs as the source of truth.

### Entering or Resuming Execution

1. Read `.spec/COMPASS.md` and classify the current cycle state.
2. If you are in a valid execution state, continue the current `**ACTIVE**` Task.
3. If you are in a valid waiting state, do not start implementation automatically. Summarize the current status to the user and wait for instruction. Start a `**PENDING**` Task only after the user explicitly says to begin it.
4. Before implementing a newly started Task, change that Task to `**ACTIVE**` in both `COMPASS.md` and its progress file.
5. Open the current Task's progress file in `.spec/progress/`.
6. Re-read the Goal, Assumptions & Constraints, dependency notes, acceptance summary, Scope, Verification Plan, and Execution Notes before changing code.

### During Execution

- Work subtask by subtask inside the current progress file.
- Record real implementation detail in the progress file: decisions, surprises, verification evidence, and blockers.
- Keep the progress file `**Status**` aligned with the parent Task state in `COMPASS.md`.
- Keep `COMPASS.md` at summary level. Do not mirror subtask detail there.
- Keep `**Current Status**` in `COMPASS.md` up to date when the current stopping point changes materially.
- If execution reveals a change that affects the overall cycle, update `COMPASS.md` after you have written the local detail in the progress file.

### Risk Recording and Escalation

When execution reveals a new risk, record it in the current progress file `## Notes` first.

Then decide whether it stays task-local, becomes cross-task tracking, or escalates to `**BLOCKED**`:

- Keep it in `Notes` only when it affects only the current Task's execution and can still be handled within the current Task.
- Add or refresh an item in `COMPASS.md > Risk Watchlist` when it may affect other Tasks, later verification, or later planning decisions across the current cycle.
- Escalate to `**BLOCKED**` when it affects the overall reliability of the current `COMPASS` plan, or when it is uncertain enough that user intervention is required before the current `**ACTIVE**` Task can continue.

`Risk Watchlist` is for cross-task visibility, not for local implementation noise.
Keep it short, summary-level, and limited to unresolved risks that still matter to the current cycle.
By the time the cycle is archived, `Risk Watchlist` should be empty.

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
6. Update `Current Status` so it names the blocked Task and what user decision or missing input is required. Update the `Risk Watchlist` if needed.
7. Stop and ask the user to intervene.

Do **not** move to another Task unless the user explicitly changes the plan.

### Task Completion

When the current Task is complete:

1. Verify the Task against its acceptance summary and the progress file evidence.
2. Mark the current progress file `**Status**` as `**DONE**`.
3. Mark the Task `**DONE**` in `COMPASS.md`.
4. Update `Current Status` to say what finished and whether the cycle is now waiting for user instruction or ready for final review.
5. Set `**Active Task**` to `none`.
6. If the Goal is complete, run the Final Review Checkpoint before Archive.
7. Otherwise stop and ask the user whether to start another Task or change the plan.

### Final Review Checkpoint

When the last Task becomes `**DONE**`:

1. Set `**Active Task**` to `none`.
2. Review `Risk Watchlist`.
3. If `Risk Watchlist` is not empty, do not archive yet. Resolve the remaining risks, or ask the user whether to explicitly accept the residual risk.
4. If the user explicitly accepts a residual risk, write the summary in `## Final Review > **Residual risk disposition**`, then clear that item from `Risk Watchlist`.
5. If no residual risk remains, write `None` in `## Final Review > **Residual risk disposition**`.
6. Scan the repo and existing `.spec/analysis/` to assess whether an analysis refresh is needed before archive. Summarize the recommendation for the user before asking for a decision.
7. If the user chooses to refresh analysis, update `.spec/analysis/`, including baseline metadata. This may be a full content update or a targeted revalidation that keeps the prose but refreshes the baseline reference. Summarize what changed and write `Refreshed` in `## Final Review > **Analysis refresh before archive**`.
8. If the user chooses not to refresh analysis, write `Skipped` in `## Final Review > **Analysis refresh before archive**`.
9. Ask the user whether to record a final commit hash.
10. If the user wants to record one, write the confirmed hash in `## Final Review > **Final commit**`. Otherwise write `Skipped`.
11. Ask the user whether the cycle is ready to archive.
12. Only when the user explicitly confirms, write `Confirmed` in `## Final Review > **Ready to archive**`.

### Archive

When the user has confirmed the cycle is ready:

1. Confirm these preconditions in `COMPASS.md`:
   - `Risk Watchlist` is empty
   - `## Final Review > **Residual risk disposition**` is filled
   - `## Final Review > **Analysis refresh before archive**` is `Refreshed` or `Skipped`
   - `## Final Review > **Final commit**` is a hash or `Skipped`
   - `## Final Review > **Ready to archive**` is `Confirmed`
2. Create `.spec/archived/YYYY-MM-DD-NN/`.
3. Move the current `COMPASS.md` and the current `progress/` folder into that archive directory.
4. Leave `.spec/analysis/` and `.spec/archived/` in place for future cycles.
5. Confirm to the user what was archived and where.

After archive, a new cycle starts by creating a new `COMPASS.md` and a new `progress/` folder while reusing `analysis/`.
