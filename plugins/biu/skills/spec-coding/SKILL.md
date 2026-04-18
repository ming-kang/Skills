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
7. **Stop before you spiral.** If a subtask fails twice or hits a constraint conflict, load `references/blocked-protocol.md` and follow it.
8. **Respect verification gates.** If a `SubagentStop` hook blocks the analyzer or architect subagent with a missing-artifact list, re-invoke the same subagent with that list as its next task — do not advance to the next phase until the gate passes.

---

## Continuity Check

**CRITICAL**: Before starting any phase, check the session state.

- **If a `<biu-session-state>` block was injected at the start of this session by the Biu `SessionStart` hook, trust it.** It already tells you whether a cycle is active, what phase you're in, task counts, and the current status. Skip the COMPASS existence probe and proceed based on that block.
- **If no `<biu-session-state>` block is present** (hook not available, or fresh install), fall back to checking whether `.spec/COMPASS.md` exists:
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
1. Use the Agent tool to spawn the `analyzer` subagent with the user's intent and codebase context. The analyzer writes `.spec/analysis/{project-overview,module-inventory,risk-assessment}.md` directly and returns a short summary.
2. For large codebases, you may spawn multiple analyzer subagents in parallel — but each one must be scoped to a **non-overlapping file** to avoid write races.
3. A `SubagentStop` hook verifies that all three files exist, are non-empty, and contain the required headings. If verification fails, re-invoke the analyzer with the missing-artifact list.

Example invocation:
```
Agent({
  description: "Analyze codebase for spec-coding Phase 1",
  subagent_type: "analyzer",
  prompt: "Analyze the codebase at [path] for [user's intent]. Focus on: structure, modules, architecture, and transformation risks."
})
```

**Output**: Complete `.spec/analysis/` directory with three documents. Present a brief summary of findings to the user and confirm before proceeding to Phase 2.

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

**Output**: Complete `.spec/tasks/` directory with one file per Task, and COMPASS.md updated with the Task Overview. Present the full task breakdown to the user and confirm before proceeding.

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

## Phase 5: Implementation

Load `references/implementation.md` when you enter this phase. It covers the per-Task start/during/end loop, COMPASS update contract, and analysis-update protocol.

If a subtask fails twice in a row, or you hit an unresolvable constraint conflict, load `references/blocked-protocol.md` and follow it.

---

## Phase 6: Archive

When all Tasks are complete and the user has confirmed readiness to archive, load `references/archive.md`. It covers archive folder naming (`YYYY-MM-DD-NN`), artifact relocation, and final reporting.

---

## Reference Files

The plugin's `agents/` directory contains specialized subagents that are automatically available when the biu plugin is enabled:

- `analyzer` — Codebase analysis subagent (invoked via Agent tool in Phase 1)
- `architect` — Task decomposition subagent (invoked via Agent tool in Phase 3)

The `references/` directory contains lazy-loaded procedure files:

- `references/implementation.md` — Implementation Phase loop (load at Phase 5)
- `references/blocked-protocol.md` — BLOCKED state entry/exit/skip procedure
- `references/archive.md` — Archive Phase procedure (load at Phase 6)
- `references/templates/analysis.md` — Templates for the three analysis documents
- `references/templates/task.md` — Template for task files in `.spec/tasks/`
