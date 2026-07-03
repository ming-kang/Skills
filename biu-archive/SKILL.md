---
name: biu-archive
description: Verify, summarize, and archive a completed biu cycle, distilling learnings.
disable-model-invocation: true
---

# Biu Archive

Use this skill to close a biu cycle: verify acceptance criteria, summarize outcomes, distill cross-cycle learnings, then archive SPEC, TASKs, and Summary together into `.biu/archived/YYYY-MM-DD-<short-name>/`.

## Biu Workflow

<!-- Shared section: keep in sync across biu-interview / biu-decompose / biu-archive. -->

Biu provides three skills covering the full development cycle from idea to archive:

| Skill | Role |
|:-----:|:----:|
| `interview` | Clarify requirements through relentless interview, producing the cycle's `SPEC.md` |
| `decompose` | Decompose SPEC into `tasks/TASK-*.md` implementation handoffs |
| `archive` | Verify outcomes, distill learnings, and archive the completed cycle |

Typical usage: `biu-interview` -> `biu-decompose` -> Implement -> `biu-archive`

This is not a requirement. The user can skip or reorder them as needed.

### Directory Layout

```text
.biu/
├── LEARNINGS.md                    # Cross-cycle knowledge (append-only)
├── cycles/                         # Active cycles, one directory each
│   └── <short-name>/
│       ├── SPEC.md                 # Development Specification
│       └── tasks/                  # Implementation Tasks
│           └── TASK-<short-name>.md
└── archived/                       # Completed Cycles
    └── YYYY-MM-DD-<short-name>/
        ├── SPEC.md
        ├── Summary.md
        └── tasks/
            └── TASK-<short-name>.md
```

`LEARNINGS.md` carries knowledge across cycles: `interview` and `decompose` read it before starting, `archive` appends to it.

**Selecting the working cycle**: if the user named one, use it; if exactly one directory exists under `cycles/`, use it; if several exist, list them (with each SPEC's `owner`) and ask. Never maintain a "current cycle" pointer.

**Legacy layout**: if `.biu/SPEC.md` exists at the root (pre-cycles layout), migrate first — derive a short name from the SPEC title, create `.biu/cycles/<short-name>/`, move `SPEC.md` and `tasks/` into it, and tell the user. Leave `archived/` untouched.

### Version Control

Biu only reads from git (`rev-parse`, `diff`, `config`) and never writes to it — no `add`, `commit`, or `push`. It reminds the user to commit at natural points instead.

How `.biu/` relates to version control (never add or remove the `.gitignore` entry yourself):

- **Not a git repository** → plain local directory; omit git-derived fields (`owner`, `baseline_commit`).
- **Git repo, `.gitignore` does not mention `.biu/`** → `.biu/` is tracked (the default). Cycles, archives, and learnings are shared team assets.
- **Git repo, `.gitignore` ignores `.biu/`** → respect it; the user chose to keep biu private. Mention once that removing the line enables shared use.

## Process

### Assess

Select the working cycle (see Directory Layout). Inputs are its `SPEC.md` and `tasks/TASK-*.md`. Archive output lives under `.biu/archived/YYYY-MM-DD-<short-name>/`.

**Pre-flight checks:**
- Verify the cycle's `SPEC.md` exists
- Verify its `tasks/` contains TASK files
- Read all SPEC and TASK files

**Status evaluation:**
- **All completed** → proceed to verify
- **Any in_progress or ready** → list them and ask the user how to close:
  - Continue work
  - Mark selected tasks
  - Archive as-is

Do not proceed until the user decides.

**Baseline context:**
Read `baseline_commit` from SPEC frontmatter. If it resolves in the current repo, run `git diff --stat <baseline>..HEAD` as context for the Summary. Treat a missing or unresolvable baseline as "no diff available."

### Verify

Task-level verification already happened during execution (each TASK's `## Verify`). This pass is cycle-level: confirm the SPEC's Acceptance Criteria actually hold before the cycle is archived as done.

For each AC, verify against the real system — run the test suite, the build, or exercise the behavior directly. Prefer quick decisive probes over exhaustive re-testing: the goal is to catch ACs that fell through the cracks between tasks, not to repeat task-level verification.

Record a per-AC result (`pass` / `fail` / `not verified`, with a short note) for the Summary's Task Results table. A failed AC is a finding, not a blocker: present it to the user and let them decide — fix now, or archive as-is with the gap recorded in Gaps & Follow-Ups.

### Summarize

Analyze the cycle and draft `Summary.md` inside the cycle's directory. The primary source material is each TASK's `## Implementation Decisions` and `## Notes`, plus the Verify pass results.

- **Outcome** — what was actually achieved, and how it differs from the SPEC's goal
- **Decisions & Discoveries** — synthesize from each TASK's Implementation Decisions and Notes
  - During discussion, explicitly ask the user whether any significant decisions or new domain knowledge discovered during implementation are missing from the task files
  - Exclude decisions already recorded in SPEC
- **Deviations** — what changed mid-cycle from the original SPEC and what triggered it
- **Task Results** — group by AC, not TASK order
  - Use the task's own frontmatter status (`completed` / `in_progress` / `ready`)
  - Verified column: the per-AC result of the Verify pass (`pass` / `fail` / `not verified`)
  - Notes column: brief evaluation of key issues encountered for that AC and how they were resolved
- **Gaps & Follow-Ups** — what was not verified, and items the next cycle can pick up

Present the draft to the user. Discuss and adjust until confirmed.

### Distill

From the Summary's Decisions & Discoveries, extract entries that remain true beyond this cycle — pitfalls hit, conventions settled, domain facts learned — and append them to `.biu/LEARNINGS.md` (create it if missing):

```markdown
# Learnings

<!-- Append-only. One bullet per entry: date, source cycle, one sentence. -->

- YYYY-MM-DD [<cycle-name>] <the lesson>
```

Rules:
- Append at the end only — never rewrite or delete existing entries (keeps merges trivial).
- Admission bar: only what a future cycle would want to know. One-off implementation details stay in the Summary.
- Project-wide coding conventions don't belong here — propose adding those to the project's agent guidance file (`AGENTS.md` or `CLAUDE.md`, whichever the project uses) instead.
- When in doubt, leave it out — a short LEARNINGS.md that gets read beats a long one that gets skipped.

### Archive

Determine the archive directory: `.biu/archived/YYYY-MM-DD-<short-name>/`, using today's date and the cycle's directory name. If it already exists, append `-2`, `-3`, ... to disambiguate.

If the repository uses Git, run `git rev-parse HEAD` and record the result as `head_commit` in `Summary.md` frontmatter.

Create the archive directory. Move the cycle's `SPEC.md`, `tasks/`, `Summary.md`, and any other temporary cycle artifacts into it, then remove the now-empty cycle directory from `.biu/cycles/`.

Close out:
- If `## Gaps & Follow-Ups` in Summary is non-empty, remind the user they can pick up these items when starting the next cycle.
- If `.biu/` is tracked by git, remind the user to commit the archived cycle and the `LEARNINGS.md` update — biu never commits on its own.

## Reference

Template: `references/summary-template.md` relative to this skill directory.
