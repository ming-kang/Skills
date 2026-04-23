---
name: spec-coding
description: >-
  Structured multi-phase workflow (Analyze → Plan → Decompose → Hand-off → Implement → Archive) for complex tasks. Invoke explicitly with /biu:spec-coding.
disable-model-invocation: true
---

# Spec-Coding

A skill for **Spec-Coding** workflow: standardized development pipeline for complex tasks.

---

## Directory Structure

All spec-coding artifacts live under `.biu/`. This directory is **never committed to version control** — ensure `.biu/` is present in `.gitignore` before creating any files.

```
.biu/
├── COMPASS.md                    # State router: Task Overview, Decision Log, Skipped Tasks + pointer to plan.md
├── plan.md                       # Confirmed spec: Task Definition, Assumptions & Constraints, Analysis links
├── analysis/
│   ├── project-overview.md
│   ├── module-inventory.md
│   └── risk-assessment.md
├── tasks/
│   └── task-N-<short-name>.md    # One file per Task
└── archived/
    └── YYYY-MM-DD-NN/            # Completed development cycles
        ├── COMPASS.md
        ├── plan.md
        ├── analysis/
        └── tasks/
```

---

## Behavioral Rules

*Each rule carries a stable slug in backticks (e.g., `R-no-auto-advance`). External references — in hooks, templates, `references/`, and `agents/` — use the form `` Behavioral Rule `R-xxx` ("Rule Title") ``, not the ordinal `Rule #N`, so rule reorderings or renames do not invalidate references. When adding a new rule, assign a slug; when adding an external reference, use the slug.*

1. **Never skip User's Confirmation.** `R-confirm-phase-boundary` Confirm with the user at each phase boundary. This includes archiving — never archive without explicit user approval.
2. **One Task at a time. Never auto-advance.** `R-no-auto-advance` When a Task is marked COMPLETE, STOP. Do NOT begin the next Task in the same turn. Always wait for the user to explicitly instruct "continue with Task N+1" (or equivalent) before starting any work on the next Task. **Corollary invariant**: COMPASS may contain at most one `[~]` at any time — before starting a new Task, transition the currently-active Task to `[x]`, `[!]`, or `[-]` first.
3. **Document decisions.** `R-document-decisions` Record important technical decisions and plan changes in COMPASS.md's Decision Log. Record implementation details in the relevant Task file's Notes section.
4. **Progress updates are mandatory.** `R-progress-updates` After completing any subtask: check its box in the Task file, immediately update the (X/N) count in COMPASS.md.
5. **New conversation = read COMPASS.md first.** `R-compass-first` Non-negotiable. It is your memory.
6. **Archive when done.** `R-archive-when-done` When all Tasks are complete, suggest archiving and wait for confirmation. Don't leave stale artifacts in the working area indefinitely.
7. **`.biu/` is always gitignored.** `R-gitignore` Verify this at the start of every fresh session before writing any files.
8. **Stop before you spiral.** `R-stop-before-spiral` If a subtask fails twice or hits a constraint conflict, load `references/blocked-protocol.md` and follow it.
9. **Respect verification gates.** `R-verification-gates` A `SubagentStop` hook that exits with code 2 feeds its stderr back to the subagent so it can self-correct within the same invocation — usually no main-agent action is needed. However, if the subagent returns to the main agent without producing complete artifacts (its final message reports failure, or the missing artifacts are still missing on disk), re-invoke the same subagent with the specific missing-artifact list as the next prompt. Do not advance to the next phase until the gate passes.
10. **Authority on disagreement.** `R-authority` When a COMPASS Task Overview symbol and a task file's `**Status**:` value disagree, the task file is authoritative — reconcile COMPASS to match. When a COMPASS `(X/N)` count disagrees with the `[x]` checkbox tally in the task file, the checkboxes are authoritative. Never silently adopt COMPASS's value over the task file's.

---

## Continuity Check

**CRITICAL**: Before starting any phase, check whether `.biu/COMPASS.md` exists.

- **If it exists**: Read it immediately. You are resuming an in-progress session. Then verify `.biu/` is in `.gitignore` (add if missing). Identify the current phase or Task from the Task Overview (the unique `[~]` line) and the per-task files in `.biu/tasks/`. Then **reconcile state**: scan `.biu/tasks/*.md`. If any task file's `**Status**:` value disagrees with the Task Overview symbol in COMPASS for the same task, trust the task file and update COMPASS to match (per Behavioral Rule `R-authority`). If a COMPASS `(X/N)` count disagrees with the count of `[x]` checkboxes in the task file, trust the checkboxes and update COMPASS. Continue from exactly where the previous conversation ended. Do NOT restart from Phase 1.
- **If it does not exist**: This is a fresh start. Verify `.biu/` is in `.gitignore` (add if missing). Then proceed to *Begin: Intent Recognition*.

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
1. Use the Agent tool to spawn the `analyzer` subagent with the user's intent and codebase context. **IMPORTANT**: Pass the absolute path to the target codebase in the prompt (e.g., `C:\Users\...\project` or `/home/user/project`). The analyzer writes `.biu/analysis/{project-overview,module-inventory,risk-assessment}.md` directly and returns a short summary.
2. A `SubagentStop` hook verifies that all three files exist, are non-empty, and contain at least one section heading. If verification fails, re-invoke the analyzer with the missing-artifact list.

Example invocation:
```
Agent({
  description: "Analyze codebase for spec-coding Phase 1",
  subagent_type: "biu:analyzer",
  prompt: "Analyze the codebase at [absolute-path] for [user's intent]. Focus on: structure, modules, architecture, and transformation risks."
})
```

**Output**: Complete `.biu/analysis/` directory with three documents. Present a brief summary of findings to the user and confirm before proceeding to Phase 2.

---

## Phase 2: Plan Refinement

**Goal**: Refine the task definition using analysis findings, then lock in a confirmed plan.

**Action**: Interview the user iteratively — one `AskUserQuestion` at a time. Ask about technical approach, UI/UX, tradeoffs, risks, scope, constraints, or anything else that affects the plan. Each question must be non-obvious and build on previous answers.

Continue until the plan is fully fleshed out. After each answer, decide: ask another question, or lock in the plan. Do not batch multiple questions in a single turn.

**Only when the plan is complete**, create two files:

1. `.biu/plan.md` — read `references/templates/plan.md` first, then populate all three sections:
   - `## Task Definition` — the confirmed description
   - `## Assumptions & Constraints` — boundaries locked in during refinement
   - `## Analysis` — links to the three analysis documents in `.biu/analysis/`

2. `.biu/COMPASS.md` — following the structure defined in `references/templates/compass.md`. Scaffold it with:
   - The `**Plan**: [plan.md](./plan.md)` pointer line
   - `## Task Overview` left with the `<Populated by Phase 3>` placeholder
   - `## Skipped Tasks` and `## Decision Log` empty (their entries are appended later during Implementation)

**Output**: `.biu/plan.md` with the confirmed spec AND `.biu/COMPASS.md` scaffolded for Phase 3.

---

## Phase 3: Task Decomposition

**Goal**: Break the transformation into concrete, trackable Tasks organized into logical groups.

**Action**: Use the Agent tool to spawn the `architect` subagent. The architect reads both `.biu/plan.md` and the analysis documents, then produces the Task files and updates COMPASS.

Example invocation:
```
Agent({
  description: "Decompose confirmed plan into tasks for spec-coding Phase 3",
  subagent_type: "biu:architect",
  prompt: "Read .biu/plan.md (confirmed spec) and all analysis documents. Break down the plan into concrete tasks with dependencies and acceptance criteria. Write task files to .biu/tasks/ and update .biu/COMPASS.md with the task overview."
})
```

**Output**: Complete `.biu/tasks/` directory with one file per Task, and COMPASS.md updated with the Task Overview.

**Hand-off**: After decomposition, before advancing to Phase 4, run the hand-off ritual:

1. Present a structured summary:
   - Confirmed task definition
   - Key findings from analysis
   - Task overview with Task names and subtask counts

2. List all generated artifacts:
   ```
   .biu/
   ├── COMPASS.md
   ├── plan.md
   ├── analysis/
   │   ├── project-overview.md
   │   ├── module-inventory.md
   │   └── risk-assessment.md
   └── tasks/
       └── task-N-*.md  (one per Task)
   ```

3. Ask the user: **"Preparation complete. Ready to start Implementation Phase?"**

Only after explicit user confirmation, advance to Phase 4. Hand-off is a transient event, not a persistent state — it is not a numbered phase because nothing about it is recoverable from disk.

---

## Phase 4: Implementation

Load `references/implementation.md` when you enter this phase. It covers the per-Task start/during/end loop, COMPASS update contract, and analysis-update protocol.

If a subtask fails twice in a row, or you hit an unresolvable constraint conflict, load `references/blocked-protocol.md` and follow it.

---

## Phase 5: Archive

When all Tasks are complete and the user has confirmed readiness to archive, load `references/archive.md`. It covers archive folder naming (`YYYY-MM-DD-NN`), artifact relocation, and final reporting.

---

## Reference Files

The plugin's `agents/` directory contains specialized subagents that are automatically available when the biu plugin is enabled:

- `analyzer` — Codebase analysis subagent (invoked via Agent tool in Phase 1)
- `architect` — Task decomposition subagent (invoked via Agent tool in Phase 3)

The `references/` directory contains lazy-loaded procedure files:

- `references/implementation.md` — Implementation Phase loop (load at Phase 4)
- `references/blocked-protocol.md` — BLOCKED state entry/exit/skip procedure
- `references/archive.md` — Archive Phase procedure (load at Phase 5)
- `references/templates/analysis.md` — Templates for the three analysis documents
- `references/templates/plan.md` — Template for the plan.md artifact (Phase 2 output)
- `references/templates/task.md` — Template for task files in `.biu/tasks/`
