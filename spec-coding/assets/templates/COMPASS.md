# COMPASS

**Goal**: <!-- One paragraph. What is being built or changed, and why. -->

**Assumptions & Constraints**:
<!-- Non-negotiable boundaries. Every implementation decision is checked against this list. -->

- 

---

## Analysis

| Document | Path |
|:--------:|:----:|
| Architecture | [architecture.md](./analysis/architecture.md) |
| Module Map | [module-map.md](./analysis/module-map.md) |

## Task Overview

<!-- Summary only. Keep subtask detail inside the progress files.
     Use uppercase bold Task states. Keep at most one **ACTIVE** Task.
     Zero **ACTIVE** Tasks is valid when planning is complete, between Tasks while
     waiting for user instruction, during blocked waiting states, or during final review.
     If one Task is the current interruption point, mark only that Task **BLOCKED**.
     Downstream Tasks that depend on it stay **PENDING**. -->

- **PENDING** Task N: <name> — Depends on: <none or Task IDs> — Acceptance: <one-line summary> — [details](./progress/task-N-<name>.md)
- **ACTIVE** Task N: <name> — Depends on: <none or Task IDs> — Acceptance: <one-line summary> — [details](./progress/task-N-<name>.md)
- **BLOCKED** Task N: <name> — Depends on: <none or Task IDs> — Acceptance: <one-line summary> — [details](./progress/task-N-<name>.md)
- **DONE** Task N: <name> — Depends on: <none or Task IDs> — Acceptance: <one-line summary> — [details](./progress/task-N-<name>.md)

## Risk Watchlist

<!-- Keep this short. This list is for unresolved risks that may affect other Tasks
     or cross-task planning in the current cycle. Do not put task-local implementation
     issues here if they can be handled inside one Task. One line each:
     risk name, affected Task(s), signal, where to look next.
     This is a working list. It should be empty before archive. If the user accepts
     a residual risk, move the summary into Final Review and clear it from here. -->

- 

---

## Status

**Current Status**:
<!-- Describe the current phase and stopping point in one or two sentences.
     Examples:
     - Planning complete; implementation has not started.
     - Task 1 in progress; 1.1 and 1.2 are done, 1.3 remains.
     - Task 1 done; waiting for user instruction to start Task 2.
     - Task 2 blocked; waiting for a user decision about API choice. -->

**Active Task**: <!-- Task N or "none". Use "none" before implementation starts, between Tasks while waiting for user instruction, during blocked waiting states, and during final review before archive. -->

---

## Final Review

**Analysis refresh before archive**: <!-- Leave blank until final review. Final value: Refreshed or Skipped. -->

**Residual risk disposition**: <!-- Leave blank until final review. Final value: None or Accepted by user: <summary>. -->

**Final commit**: <!-- Leave blank until final review. Final value: <hash> or Skipped. -->

**Ready to archive**: <!-- Leave blank until the user explicitly confirms. Final value: Confirmed. -->
