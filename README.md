# Skills Marketplace

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ming-kang/Skills)

Personal Claude Code plugin marketplace. Currently ships one plugin: **biu**.

## Install

```bash
/plugin marketplace add ming-kang/skills
/plugin install biu@ming-kang-skills
```

To update later, refresh the marketplace and then update the installed plugin:

```bash
/plugin marketplace update ming-kang-skills
/plugin update biu@ming-kang-skills
```

## Biu — lightweight dev-doc protocol

Biu turns vague development goals into specs, specs into executable task handoffs, and finished cycles into archives. All artifacts are plain Markdown under a project-local `.biu/` directory.

| Command | What it does |
|---|---|
| `/biu:interview` | Ask clarifying questions, write `.biu/SPEC.md` |
| `/biu:decompose` | Split the SPEC into `.biu/tasks/TASK-*.md` handoffs |
| `/biu:archive` | Close the cycle to `.biu/archived/YYYY-MM-DD-NN/` with a `Summary.md` |

A typical cycle:

```text
/biu:interview            # → .biu/SPEC.md
/biu:decompose            # → .biu/tasks/TASK-filter-state.md, TASK-wire-ui.md, ...
@.biu/tasks/TASK-filter-state.md   # tell Claude to execute a task
/biu:archive              # wrap up
```

Biu has no runtime dependencies — it's just skills and Markdown templates.

## For developers

This marketplace follows the [Claude Code plugin marketplace spec](https://code.claude.com/docs/en/plugin-marketplaces).

Test a local copy:

```bash
/plugin marketplace add ./path/to/Skills
/plugin install biu@ming-kang-skills
```

## License

MIT
