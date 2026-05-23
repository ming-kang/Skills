# Skills Marketplace

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ming-kang/Skills)

Personal Claude Code plugin marketplace. It currently publishes one plugin: **biu**.

## Biu

Biu is a lightweight development-document protocol for Claude Code. It turns vague development goals into a SPEC, turns that SPEC into executable task handoffs, and archives the finished cycle with a summary.

All artifacts are plain Markdown in a project-local `.biu/` directory:

```text
.biu/
├── SPEC.md
├── tasks/
│   └── TASK-<short-name>.md
└── archived/
    └── YYYY-MM-DD-NN/
        ├── SPEC.md
        ├── Summary.md
        └── tasks/
            └── TASK-<short-name>.md
```

Biu has no runtime dependencies. It is just Claude Code skills and Markdown templates.

## Install

```bash
/plugin marketplace add ming-kang/skills
/plugin install biu@ming-kang-skills
```

To update later:

```bash
/plugin marketplace update ming-kang-skills
/plugin update biu@ming-kang-skills
```

## Commands

| Command | Use it when | Output |
|---|---|---|
| `/biu:interview` | The goal is still ambiguous and needs clarification | `.biu/SPEC.md` |
| `/biu:decompose` | `.biu/SPEC.md` is ready and implementation work needs task handoffs | `.biu/tasks/TASK-*.md` |
| `/biu:archive` | The current development cycle is complete or ready to close | `.biu/archived/YYYY-MM-DD-NN/` |

## Typical Workflow

```text
/biu:interview
/biu:decompose
@.biu/tasks/TASK-filter-state.md
/biu:archive
```

The skills can also be skipped or reordered when the project context calls for it.

## For Developers

This marketplace follows the [Claude Code plugin marketplace spec](https://code.claude.com/docs/en/plugin-marketplaces).

Test a local copy:

```bash
/plugin marketplace add ./path/to/Skills
/plugin install biu@ming-kang-skills
```

## License

MIT
