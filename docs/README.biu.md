# Biu

Biu is a lightweight development-document workflow. It helps turn an unclear development goal into a SPEC, decompose that SPEC into implementation tasks, verify the outcome, and archive the completed cycle — distilling knowledge that carries over to future cycles.

## Skills

| Skill | Role |
|:-----:|:----:|
| `biu-interview` | Interview the user to clarify intention & goal, producing the cycle's `SPEC.md` |
| `biu-decompose` | Decompose SPEC into `tasks/TASK-*.md` implementation handoffs |
| `biu-archive` | Verify outcomes, distill learnings, and archive the completed cycle |

## Typical Workflow

```text
biu-interview -> biu-decompose -> implement -> biu-archive
```

This is not a requirement. The user can skip or reorder skills as needed.

## Directory Layout

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

## Task Lifecycle

Tasks move through `ready → in_progress → completed`, claimed by setting `owner`. Two guard rails travel inside every task file so they survive hand-off to any agent:

- **Stop before you spiral** — the same step failing twice sets `status: blocked` with a `## Blocked` record (what was tried, what would unblock it) instead of endless retries.
- **One task at a time** — a completed task is a stopping point; the user decides what runs next, which is also what makes parallel dispatch of independent tasks safe.

## Collaboration

In a git repository, `.biu/` is tracked by default: cycles, archives, and learnings become shared team assets. Add `.biu/` to `.gitignore` if you prefer to keep it private — biu respects an existing ignore entry and never edits `.gitignore` itself.

There is no configuration file. Developer identity comes from `git config user.name` (it fills the SPEC's `owner` and claims TASKs), and concurrent cycles are isolated by their directories under `.biu/cycles/`.

Biu only reads from git; it never runs `add`, `commit`, or `push`.

## Portability

Skills follow the open [Agent Skills](https://agentskills.io) format (`SKILL.md`), supported by Claude Code, Codex CLI, Gemini CLI, OpenCode, and other agents. All biu state lives in plain Markdown files under `.biu/` — team members can run different agents against the same cycle documents.

## License

MIT
