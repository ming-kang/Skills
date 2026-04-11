---
name: spec-coding
description: >-
  Triggers only when the user wants to do spec coding.
disable-model-invocation: true
metadata:
  version: "2.0.2"
---

# Spec-Coding

You are executing the **Spec-Coding** workflow — a structured pre-development pipeline for large-scale, complex tasks.

Complete all preparation Phases before any implementation begins.

If a specific tool mentioned here is unavailable, use the closest equivalent available in your environment.

---

## Behavioral Rules

1. **COMPASS.md is your memory.** New conversation = read COMPASS.md first, non-negotiable.
2. **Never skip phases.** Even for small projects, produce lightweight versions of each phase's outputs.
3. **Confirm at phase boundaries.** Every phase transition is a checkpoint.
4. **Stop before you spiral.** Two failures or one constraint conflict → Blocked Protocol. Immediately.
5. **Archive is not optional.** When all Tasks are done, always archive. Do not leave stale artifacts.
6. **`.spec/` is always gitignored.** Verify at the start of every fresh session.
7. **No code before approval.** No code, scaffolding, or pseudo-code until the user approves the plan at Phase 4.
8. **Give opinions directly.** Take a position on architectural choices. State your recommendation and the evidence that would change it.
9. **No placeholders in approved plans.** A plan with placeholders is not approvable.

---

## Directory Structure

All spec-coding artifacts live under `.spec/`. This directory is **never committed to version control**.

```
.spec/
├── COMPASS.md                    # Main control file — always read this first
├── analysis/
│   ├── architecture.md
│   ├── module-map.md
│   └── risk-register.md
├── plan/
│   ├── task-breakdown.md         # Includes Mermaid dependency graph
│   └── milestones.md
├── progress/
│   └── task-N-<short-name>.md  	  # One file per Task
└── archived/
    └── YYYY-MM-DD-NN/            # Completed development cycles
```

Templates for all files above are in the skill directory at `assets/templates/`.

---

## Continuity Check

**Before starting any phase**, check whether `.spec/COMPASS.md` exists.

- **Exists**: Read it immediately. You are resuming a session. Identify the current phase or task, what was completed, and continue from exactly where the previous conversation ended. Do NOT restart from Phase 0.
- **Does not exist**: Treat this as a fresh start. Verify `.spec/` is in `.gitignore` — add it if not. Then proceed to Phase 0.

After loading state from COMPASS.md, populate **TaskCreate** with the active phase's pending items.

---

## Phase 0: Intent Recognition & Confirmation

### Stage 0: Quick Scan

This exists to help you orient and make your questions grounded.

- Read `README.md`, `CLAUDE.md`, `AGENTS.md`, etc.
- Scan the top-level directory structure
- Identify technology stack signals: `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, etc.

If the directory is empty or unfamiliar, note that — it means Stage 1 questions must be more open-ended.

### Stage 1: Natural Conversation

Open with a short summary of what you already understand from Stage 0 and the user's initial message — project type, tech stack, your interpretation of the request. Then ask follow-up questions in **plain conversational text**.

Do **not** use `AskUserQuestion` here. Keep to 1–2 questions at a time. Build shared context through dialogue, not forms.

Continue until you have a working understanding of scope, target state, and hard constraints.

### Stage 2: Targeted Confirmation

Once natural conversation has established sufficient context, use `AskUserQuestion` to nail down remaining specific unknowns. One call per unresolved question — do not batch them.

Confirm at minimum: scope, hard constraints (backward compatibility, libraries, deployment targets), and priority (performance vs. maintainability vs. speed of delivery).

### Confirmation

Summarize your complete understanding and get explicit user confirmation before proceeding.

**Phase 0 output**: Create `.spec/COMPASS.md` from `assets/templates/`. Fill in only:

- **Task Definition**
- **Assumptions & Constraints**

Leave all other sections as-is. Do not fill in what you do not yet know.

---

## Phase 1: Deep Project Analysis

**Goal**: Build a comprehensive, factual understanding of the current codebase. No opinions, no suggestions — only what exists.

### Before You Begin

Create `architecture.md` `module-map.md` `risk-register.md` from `assets/templates/analysis`.

### Dispatch `Explore`

Read `references/subagents.md` — Explore section — for the prompt template. Adapt it for each subagent you dispatch.

**If the project is small** (roughly 20 files or fewer), a single Explore pass is sufficient. 

Otherwise, **split the work by architectural boundary**, not by file count. One agent per logical area is more effective than one agent per directory. Examples:

- Core domain logic + data models
- Infrastructure layer (DB, external APIs, file I/O)
- Entry points, routing, public API surface

Dispatch all agents in parallel. After `Explore` subagents report findings back to you, write `.spec/analysis/*` and consolidate all findings into the three output files.

### Output: `.spec/analysis/`

Each file must be fully filled in before Phase 2 begins. Incomplete sections must be explicitly marked as "not found" — do not leave template placeholders.

- **architecture.md**: tech stack, all entry points, build/run/test/lint commands, high-level architecture (2–5 paragraphs), patterns observed with file evidence, external integrations
- **module-map.md**: every significant module with responsibility, public API, internal deps, external deps, size, complexity rating
- **risk-register.md**: every risk that could affect the plan — complexity, coupling, missing tests, external constraints; hotspot summary (the 2–3 areas most likely to cause problems)

### Phase Boundary

Phase 1 is complete when all three files are filled and contain no template placeholders. Proceed to Phase 2 immediately.

---

## Phase 2: Analysis Review

**Goal**: Present findings, propose architectural options, test the recommendation, reach a confirmed direction.

### Step 1: Present the Analysis

Summarize for the user — do not dump the full documents. Cover:

1. **Project overview**: what this is, tech stack, approximate scale
2. **Key findings**: important modules, dependencies, patterns relevant to the task
3. **Risk highlights**: top 2–3 risks and why they matter

Keep to one focused message.

### Step 2: Propose Architectural Options

Propose **2–3 options**. Always include one minimal option.

For each option:

| Field | Content |
|:-----:|:-------:|
| **Summary** | One sentence: what this approach does |
| **Effort** | Small/Medium/High |
| **Risk** | What could go wrong |
| **Builds on** | Which existing code or patterns it leverages |

State your recommendation explicitly. Do not hedge — pick one and say why.

### Step 3: Adversarial Test the Recommendation

Before presenting, attack your own recommendation internally:

1. **What would make this fail?** Identify the single most likely failure mode.
2. **If the attack holds**: Deform the design to survive it. Present the deformed version, noting what changed and why.
3. **If the attack shatters the approach entirely**: Discard it, tell the user why, promote the second-best option and repeat.

Present the hardened recommendation — not your original unexamined first choice.

### Step 4: User Confirmation

Ask the user to confirm the direction. Do not proceed to Phase 3 until they do.

If the user pushes back: minor adjustments inline and confirm again; different option preferred — re-run adversarial test on that option; new option not yet proposed — explore, assess, test, present.

### Phase Boundary

Phase 2 is complete when the user confirms an architectural direction.

Update COMPASS.md: fill in **Architecture direction confirmed** (one sentence: which option and why) and add links to all three analysis documents.

Proceed to Phase 3.

---

## Phase 3: Task Decomposition

**Goal**: Break the confirmed approach into concrete, trackable Tasks with no placeholders and clear acceptance criteria.

### Before You Begin

Confirm `COMPASS.md` has a confirmed architecture direction — if not, Phase 2 was not completed.

Create `task-breakdown.md` `milestones.md` from `assets/templates/plan`.

### Dispatch `Plan`

Read `references/subagents.md` — Plan section — for the prompt template. Fill in:
- The task definition from `COMPASS.md`
- The confirmed architecture direction from `COMPASS.md`
- The full Assumptions & Constraints from `COMPASS.md`

Dispatch Plan after the template is filled.

### Placeholder Enforcement

When Plan returns, scan both output files for forbidden patterns before accepting the output:

**Forbidden**: TBD, TODO, "implement later", "similar to Task N", "details to be determined", "to be specified", blank acceptance criteria fields, blank effort fields.

If any found: send Plan back with a list of every occurrence and the instruction to resolve each one. Do not proceed to Phase 4 with an incomplete plan.

### Output: `.spec/plan/`

- **task-breakdown.md**: every Task with description, priority (P1/P2/P3), effort (Small/Medium/High), dependencies, subtasks, acceptance criteria; Mermaid dependency graph; Tasks ordered by dependency.
- **milestones.md**: 3–5 milestones, each an end-to-end working state or retired risk, with explicit demonstrable target criteria.

### Phase Boundary

Phase 3 is complete when both plan files are filled and contain no forbidden patterns. Proceed to Phase 4 immediately.

---

## Phase 4: Plan Review & Approval

**Goal**: Get explicit user approval before any implementation begins. No code, scaffolding, or pseudo-code until the user approves.

### Step 1: Present the Plan

Present a readable summary — do not paste the raw files. Cover:

1. **Task overview**: all Tasks with names, priorities, effort estimates, and dependencies (a table works well)
2. **Milestone overview**: all milestones and their target criteria
3. **Total scope**: rough overall effort, number of Tasks
4. **Key risks addressed**: tie back to the risk register — how does the plan handle the top risks?

### Step 2: Invite Scrutiny

Explicitly ask the user to check:
- Are all the right things included?
- Is anything scoped too broadly or too narrowly?
- Do the priorities look right?
- Are the acceptance criteria strong enough?

### Step 3: Handle Feedback

Diagnose the root cause before acting:

| Feedback type | Root cause | Action |
|:------------:|:---------:|:------:|
| Task description unclear, wrong granularity, missing functionality | Plan output incomplete | Return to Phase 3: re-dispatch Plan with corrected instructions |
| Analysis missed a module, factual gap | Phase 1 analysis wrong | Return to Phase 1: targeted Explore, update analysis file, re-run Phase 3 |
| Architecture direction wrong | Phase 2 decision wrong | Return to Phase 2: re-present options, new confirmation, re-run Phase 3 |
| Scope or constraints changed | Phase 0 assumptions outdated | Update COMPASS.md, return to Phase 2 or 3 as appropriate |
| Minor wording fix, small reprioritization | Surface fix only | Edit plan file directly, no phase return needed |

State the diagnosis to the user before acting. Confirm with the user before returning to a prior phase.

### Phase Boundary

Phase 4 is complete when the user explicitly approves the plan (e.g., "looks good", "approved", "proceed").

Update `COMPASS.md`: add links to both plan documents, fill in the Task Overview table (all Tasks, initial `[ ]`), fill in the Milestones table (all milestones, initial `[ ]`).

Proceed to Phase 5.

---

## Phase 5: Progress Tracking Setup

**Goal**: Create per-Task progress files and complete COMPASS.md so a fresh agent can orient in under 30 seconds.

### Step 1: Create Progress Files

For each Task in `task-breakdown.md`, create `task-N-<short-name>.md` from `assets/templates/progress/task.md`. 

For each file:

- Copy the subtasks and acceptance criteria from `task-breakdown.md`
- Set **Current** to the first subtask of that Task (e.g., `1.1`); leave other tasks' Current blank until active
- Leave the Notes section empty

Naming example: Task 3 "Refactor authentication layer" → `task-3-refactor-auth.md`

### Step 2: Complete COMPASS.md

Fill in the two remaining sections:

**Current Status**: "Phase 5 complete. Ready to begin Task 1: `<name>`."

**Next Steps**:

- Read `.spec/plan/task-breakdown.md` to understand the full scope
- Open `.spec/progress/task-1-<name>.md` and begin the first subtask
- Re-read Assumptions & Constraints before touching any code

### Phase Boundary

Phase 5 is complete when progress files exist and `COMPASS.md`'s Current Status and Next Steps are filled. Proceed to Phase 6.

---

## Phase 6: Sub-skill Generation

**Goal**: Generate a project-scoped sub-skill that encodes this project's implementation standards and continuity protocol.

Install at **project scope only**: `./.claude/skills/`.

Name it `spec-coding-<project-name>`. It is removed when the Archive Phase runs.

Delegate creation to `skill-creator`. Provide it the task context from `COMPASS.md`, the sub-skill name, and the content outline below.

**If `skill-creator` is not installed**: Tell the user it is required and instruct them to install it with `npx skills add anthropics/skills --skill skill-creator`. Do not install it on their behalf. Once installed, return to this phase.

### Required Sub-skill Content

The generated sub-skill must instruct the agent to do the following.

**Session Startup** (every conversation, non-negotiable):

1. Read `.spec/COMPASS.md` first — before any other file, before any action
2. Identify the active Task from the Task Overview table
3. Open that Task's progress file in `.spec/progress/`
4. Populate `TaskCreate` with all unchecked subtasks.
5. Re-read Assumptions & Constraints before touching any code

**During Implementation**:

- Before each implementation decision, check it against Assumptions & Constraints — if it conflicts, stop and invoke the Blocked Protocol.
- After completing a subtask: check its box `[x]` in the progress file, update **Current** to the next subtask, use `TaskUpdate` to mark the item as completed.
- Record decisions, surprises, and discovered context in the progress file Notes section — not in conversation text
- Dual-write: `TaskCreate` for real-time visibility; Markdown files for cross-conversation persistence

**Blocked Protocol**: Include the full content of `references/blocked-protocol.md`.

**Task Completion**:
- Verify all acceptance criteria before marking complete
- Mark `[x]` in `COMPASS.md` Task Overview
- Update Current Status and Next Steps in `COMPASS.md`
- Check `milestones.md`: if this Task satisfies a milestone's criteria, mark it `[x]` in `COMPASS.md` and notify the user
- When all Tasks are `[x]`, trigger the Archive Phase automatically

**Project-Specific Standards**: Fill in from Phase 0 and Phase 1 analysis — tech stack conventions, naming rules, file organization, testing requirements.

### Phase Boundary

Phase 6 is complete when the project-scope sub-skill is installed and visible. Proceed to Handoff.

---

## Handoff

Present a structured summary:
- Confirmed task definition
- Key findings from analysis (3–5 bullets, high-level)
- Task overview: group names, Task count, total effort estimate
- Milestone list
- Sub-skill name and install location

List all generated artifacts:
```
.spec/
├── COMPASS.md
├── analysis/
│   ├── architecture.md
│   ├── module-map.md
│   └── risk-register.md
├── plan/
│   ├── task-breakdown.md
│   └── milestones.md
└── progress/
    └── task-N-*.md  (one per Task)
.claude/skills/spec-coding-<project-name>  (sub-skill)
```

Ask the user: **"Preparation complete. Ready to start Task 1?"**

---

## Implementation: Tasks

Once Handoff is confirmed, development proceeds as a series of **Tasks**.

**At the start of every Task**:
1. Read `.spec/COMPASS.md` — confirm position, re-read Assumptions & Constraints
2. Open `.spec/progress/task-N-<name>.md`
3. Populate `TaskCreate` with subtasks

**During each Task**:
- Work through subtasks one at a time.
- After each subtask: check its box `[x]` in the progress file, update **Current** to the next subtask, use `TaskUpdate` to mark the item as completed.
- Record decisions, surprises, blockers in the progress file Notes section — not in conversation text.
- Dual-write: `TaskCreate` (real-time) + Markdown files (cross-conversation persistence).
- If a subtask fails twice or hits a constraint conflict → invoke the **Blocked Protocol** immediately.

**At the end of every Task**:

- Verify all acceptance criteria.
- Mark `[x]` in `COMPASS.md` Task Overview.
- Update Current Status and Next Steps in `COMPASS.md`.
- Check `milestones.md`: if this Task satisfies a milestone's criteria, mark it `[x]` in `COMPASS.md` and notify the user.
- When all Tasks are `[x]`: trigger the Archive Phase.

---

## Blocked Protocol

See [references/blocked-protocol.md](references/blocked-protocol.md) for the full protocol.

**Trigger**: A subtask has failed twice, OR an implementation decision conflicts with Assumptions & Constraints and cannot be resolved without user input.

**Core rule**: Stop immediately. Do not attempt a third workaround. Mark the subtask `[blocked]` in the progress file, mark the Task `[blocked]` in `COMPASS.md`, then report to the user with root cause and what is needed to unblock.

---

## Archive Phase

**Trigger**: All Tasks in `COMPASS.md` are marked `[x]`.

### Steps

1. **Announce** to the user that all Tasks are complete and the Archive Phase is beginning.

2. **Git Snapshot**: If the project is a git repository — prompt the user to commit any pending code changes. Once committed, record the commit hash in `Final commit` in `COMPASS.md`. If the user declines, record `none (user skipped)`. If not a git repo, skip.

3. **Determine archive folder name**: Format `YYYY-MM-DD-NN`. Check `.spec/archived/` for existing folders with today's date and increment `NN` accordingly (starting at `01`).

4. **Move artifacts** to the archive folder, preserving internal structure:
```
.spec/archived/YYYY-MM-DD-NN/
├── COMPASS.md
├── analysis/
│   ├── architecture.md
│   ├── module-map.md
│   └── risk-register.md
├── plan/
│   ├── task-breakdown.md
│   └── milestones.md
└── progress/
    └── task-N-*.md
```

5. **Remove the project-scope sub-skill** from `.claude/skills/`.

6. **Confirm to the user**: what was archived and its location, the final commit hash (if applicable), that `.spec/` is clean and ready for the next cycle.

After archive, `.spec/` contains only the `archived/` directory. The next development cycle begins with Phase 0.
