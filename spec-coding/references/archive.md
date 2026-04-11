# Archive Phase

**Trigger**: All Tasks in `.spec/COMPASS.md` are marked `[x]`.

**Goal**: Preserve this development cycle's artifacts and return `.spec/` to a clean state for the next cycle.

---

## Steps

### 1. Announce Completion

Tell the user all Tasks are complete and the Archive Phase is beginning.

### 2. Git Snapshot

Check whether the project is a git repository.

- **If yes**: Prompt the user to commit any pending code changes from this cycle. Once committed, record the commit hash in the `**Final commit**` field at the end of `.spec/COMPASS.md` as `<hash>`. If the user declines, record `none (user skipped)` in that same field and continue.
- **If no**: Skip this step.

### 3. Determine Archive Folder Name

Format: `YYYY-MM-DD-NN` where `NN` is a two-digit sequence starting at `01`.

Check `.spec/archived/` for existing folders with the current date. Example: if today's date is `YYYY-MM-DD` and `.spec/archived/YYYY-MM-DD-01/` exists, use `02`, and so on.

### 4. Move Artifacts

Move all current working artifacts into the archive folder, preserving internal structure:

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

### 5. Remove the Sub-skill

Delete the project-scoped sub-skill installed in Phase 6 from `.claude/skills/`. It was specific to this cycle and is no longer needed. If Phase 6 was skipped and no sub-skill was installed, skip this step.

### 6. Confirm to the User

Report:
- What was archived and its location (`.spec/archived/YYYY-MM-DD-NN/`)
- The final commit hash recorded (if applicable)
- That the sub-skill has been removed
- That `.spec/` is clean and ready for the next cycle
- A reminder to commit any production code changes from this cycle to version control, if not already done

---

## After Archive

`.spec/` now contains only the `archived/` directory. The next development cycle begins immediately with Phase 0.
