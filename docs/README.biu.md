# Biu

Biu is a lightweight development-document workflow. It helps turn an unclear development goal into a SPEC, decompose that SPEC into implementation tasks, and archive the completed cycle.

## Skills

| Skill | Role |
|:-----:|:----:|
| `biu-interview` | Interview the user to clarify intention & goal, producing `.biu/SPEC.md` |
| `biu-decompose` | Decompose `.biu/SPEC.md` into `.biu/tasks/TASK-*.md` implementation handoffs |
| `biu-archive` | Summarize outcomes and archive the completed cycle |

## Typical Workflow

```text
biu-interview -> biu-decompose -> implement -> biu-archive
```

This is not a requirement. The user can skip or reorder skills as needed.

## Directory Layout

`.biu/` should be git-ignored.

```text
.biu/
├── SPEC.md                         # Development Specification
├── tasks/                          # Implementation Tasks
│   └── TASK-<short-name>.md
└── archived/                       # Completed Cycles
    └── YYYY-MM-DD-NN/
        ├── SPEC.md
        ├── Summary.md
        └── tasks/
            └── TASK-<short-name>.md
```

## License

MIT
