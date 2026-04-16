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

### biu (v1.0.0)

Spec-driven workflow for complex development tasks.

| Feature | Description |
|---------|-------------|
| Structured workflow | Phased analysis and task decomposition |
| Custom agents | Codebase analysis and planning subagents |
| COMPASS templates | Consistent task and analysis documentation |
| Cross-session state | `.spec/` artifacts persist between sessions |
| Blocker protocol | Formal handling for blocked tasks |

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
