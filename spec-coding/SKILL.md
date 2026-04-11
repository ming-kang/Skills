---
name: spec-coding
description: >-
  Triggers when the user mentions "spec coding" / "spec-coding", or directly /spec-coding in Claude Code.
metadata:
  version: "1.3.0"
---

# Spec-Coding

You are executing the **Spec-Coding** workflow — a structured pre-development pipeline for large-scale, complex tasks. Complete all preparation Phases before any implementation begins.

---

## Directory Structure

All spec-coding artifacts live under `.spec/`. This directory is **never committed to version control** — ensure `.spec/` is in `.gitignore` before creating any files.

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
│   └── task-N-<short-name>.md   # One file per Task
└── archived/
    └── YYYY-MM-DD-NN/            # Completed development cycles
```

Templates for all files above are in `assets/templates/` in this skill directory.

---

## Continuity Check

**Before starting any phase**, check whether `.spec/COMPASS.md` exists.

- **Exists**: Read it immediately. You are resuming a session. Identify the current phase or task, what was completed, and continue from exactly where the previous conversation ended. Do NOT restart from Phase 0.
- **`.spec/progress/` exists but `COMPASS.md` does not**: COMPASS.md may have been lost. Attempt to reconstruct it from the progress files and notify the user before continuing.
- **Neither exists**: Fresh start. Verify `.spec/` is in `.gitignore` — add it if not. Then proceed to Phase 0.

After loading state from COMPASS.md, populate **TaskCreate** with the active phase's pending items.

---

## Phase 0: Intent Recognition & Confirmation

Full instructions: this phase is defined inline below (it is short enough to stay in SKILL.md).

### Stage 0: Quick Scan (Silent)

Before speaking, spend 30 seconds orienting. Write nothing — this step exists only to make your questions grounded.

- Read `README.md`, `CLAUDE.md`, `AGENTS.md` if they exist
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

**Phase 0 output**: Create `.spec/COMPASS.md` from `assets/templates/COMPASS.md`. Fill in only:
- **Task Definition**
- **Assumptions & Constraints**

Leave all other sections as-is. Do not fill in what you do not yet know.

---

## Phase 1: Deep Project Analysis

See [references/phase-1-analysis.md](references/phase-1-analysis.md) for full instructions.

**Summary**: Dispatch `Explore` subagents in parallel across different architectural areas. Use the prompt template in `references/subagents/explore-brief.md`. Each agent writes to the relevant section of the analysis files.

**Output**: `.spec/analysis/` — three files fully populated, no template placeholders remaining.

---

## Phase 2: Analysis Review

See [references/phase-2-analysis-review.md](references/phase-2-analysis-review.md) for full instructions.

**Summary**: Present findings to the user. Propose 2–3 architectural options with tradeoffs and a recommendation. Adversarial-test the recommendation before presenting it. Get user confirmation on the direction.

**Output**: COMPASS.md updated with analysis document links and confirmed architecture direction.

---

## Phase 3: Task Decomposition

See [references/phase-3-decomposition.md](references/phase-3-decomposition.md) for full instructions.

**Summary**: Dispatch the `Plan` subagent using the template in `references/subagents/plan-brief.md`. The subagent reads all analysis files and produces a complete plan. Reject any output containing placeholders — send Plan back until the output is clean.

**Output**: `.spec/plan/` — `task-breakdown.md` (with Mermaid dependency graph) and `milestones.md`, fully populated.

---

## Phase 4: Plan Review & Approval

See [references/phase-4-plan-review.md](references/phase-4-plan-review.md) for full instructions.

**Summary**: Present the complete plan to the user. Invite scrutiny. Handle feedback by diagnosing the root cause and returning to the appropriate phase — not all feedback requires a full replan. No code until the user explicitly approves.

**Output**: COMPASS.md updated with plan document links, Task Overview table, and Milestones table.

---

## Phase 5: Progress Tracking Setup

See [references/phase-5-tracking.md](references/phase-5-tracking.md) for full instructions.

**Summary**: Create one progress file per Task using `assets/templates/progress/task.md`. Complete COMPASS.md with Current Status and Next Steps.

**Output**: `.spec/progress/task-N-*.md` for every Task. COMPASS.md fully populated.

---

## Phase 6: Sub-skill Generation

See [references/phase-6-subskill.md](references/phase-6-subskill.md) for full instructions.

**Summary**: Use `skill-creator` to generate a project-scoped sub-skill at `.claude/skills/` in the project root. The sub-skill encodes session startup protocol, implementation rules, Blocked Protocol (from `references/blocked-protocol.md`), and project-specific conventions.

**Output**: A project-scoped sub-skill installed and ready.

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
3. Populate TaskCreate with pending subtasks

**During each Task**:
- Work through subtasks one at a time
- After each subtask: check its box in the progress file, update `(K/X)` count in COMPASS.md, mark TaskCreate item complete
- Record decisions, surprises, blockers in the progress file Notes section — not in conversation text
- Dual-write: TaskCreate (real-time) + Markdown files (cross-conversation persistence)
- If a subtask fails twice or hits a constraint conflict → invoke the **Blocked Protocol** immediately

**At the end of every Task**:
- Verify all acceptance criteria
- Set progress file Status to `COMPLETE`
- Mark `[x]` in COMPASS.md, update subtask count to `(X/X)`
- Update Current Status and Next Steps in COMPASS.md
- Check `milestones.md`: if this Task satisfies a milestone's target criteria, mark it `[x]` in COMPASS.md and notify the user
- When all Tasks are `[x]`: trigger the Archive Phase

---

## Blocked Protocol

See [references/blocked-protocol.md](references/blocked-protocol.md) for the full protocol.

**Trigger**: A subtask has failed twice, OR an implementation decision conflicts with Assumptions & Constraints and cannot be resolved without user input.

**Core rule**: Stop immediately. Do not attempt a third workaround. Update the progress file and COMPASS.md, then report to the user with root cause and what is needed to unblock.

---

## Archive Phase

See [references/archive.md](references/archive.md) for full instructions.

**Trigger**: All Tasks in COMPASS.md are marked `[x]`.

**Summary**: Git snapshot → determine archive folder name (`YYYY-MM-DD-NN`) → move all artifacts to `.spec/archived/` → remove the project sub-skill → confirm to user.

---

## Behavioral Rules

1. **No code before approval.** No code, scaffolding, or pseudo-code until the user approves the plan at Phase 4.
2. **Give opinions directly.** Take a position on architectural choices. State your recommendation and the evidence that would change it.
3. **Adversarial-test the recommendation.** Before presenting an option as recommended, attack it: what would make it fail? Harden or discard based on the result.
4. **No placeholders in approved plans.** Forbidden: TBD, TODO, "implement later", "similar to Task N", "details to be determined". A plan with placeholders is not approvable.
5. **Confirm the working path.** Verify `.spec/` is in `.gitignore` before writing any files.
6. **Never skip phases.** Even for small projects, produce lightweight versions of each phase's outputs.
7. **Confirm at every phase boundary.** Every phase transition is a checkpoint.
8. **COMPASS.md is your memory.** New conversation = read COMPASS.md first, non-negotiable.
9. **Dual-write progress.** TaskCreate for real-time visibility; Markdown files for cross-conversation persistence.
10. **Stop before you spiral.** Two failures or one constraint conflict → Blocked Protocol. Immediately.
11. **Archive is not optional.** When all Tasks are done, always archive. Do not leave stale artifacts.
12. **`.spec/` is always gitignored.** Verify at the start of every fresh session.
