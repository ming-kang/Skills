# Skills Marketplace

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ming-kang/Skills)

Personal Claude Code plugin marketplace for distributing commonly used plugins and skills.

## Quick Start

```bash
# 1. Add marketplace (lowercase repo name required)
/plugin marketplace add ming-kang/skills

# 2. Install plugin
/plugin install biu@ming-kang-skills

# 3. Use it
/biu:spec-coding
```

> To update: `/plugin marketplace update ming-kang-skills`

## Available Plugins

### biu

Spec-driven workflow for complex development tasks.

| Feature | Description |
|---------|-------------|
| Structured workflow | Phased analysis, planning, decomposition, implementation, archive |
| Custom agents | Codebase analysis (analyzer) and task decomposition (architect) subagents |
| COMPASS-based continuity | Single-file `.spec/COMPASS.md` as cross-session memory; no hidden state cache |
| Templates | Canonical structures for COMPASS, tasks, and analysis documents |
| Blocker protocol | Formal handling for blocked tasks with resume/skip workflow |
| Verification gates | `SubagentStop` hooks verify analyzer/architect produced well-formed artifacts |
| Task-complete reminder | `PostToolUse` hook injects a STOP reminder when a Task is marked COMPLETE |

**Requirements**: biu's hooks are pure bash scripts — no Python or other runtime dependencies. On Windows, install [Git for Windows](https://git-scm.com/download/win) so `bash` is available on PATH. macOS and Linux have bash out of the box.

## For Developers

This marketplace follows the [Claude Code plugin marketplace specification](https://code.claude.com/docs/en/plugin-marketplaces).

### Testing Locally

```bash
# Add local repository as marketplace
/plugin marketplace add ./path/to/Skills

# Install plugin
/plugin install biu@ming-kang-skills
```

## License

MIT License
