# Skills Marketplace

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ming-kang/Skills)

Personal Claude Code plugin marketplace for distributing commonly used plugins and skills.

## Overview

This repository serves as a plugin marketplace for Claude Code, providing curated plugins for enhanced development workflows.

## Available Plugins

### biu (v1.0.0)

Spec-driven workflow for complex development tasks with structured analysis and task decomposition.

**Features:**
- Structured workflow phases for complex tasks
- Codebase analysis with custom agents
- Task decomposition and planning
- COMPASS methodology templates
- Cross-session continuity via `.spec/` artifacts
- Formal blocker protocol

**Installation:**

```bash
# Add this marketplace
/plugin marketplace add ming-kang/Skills

# Install the biu plugin
/plugin install biu@ming-kang-skills
```

**Usage:**

```bash
/biu:spec-coding
```

## For Users

### Adding the Marketplace

```bash
/plugin marketplace add ming-kang/Skills
```

### Installing Plugins

```bash
/plugin install biu@ming-kang-skills
```

### Updating Plugins

```bash
/plugin marketplace update ming-kang-skills
```

## For Developers

This marketplace follows the [Claude Code plugin marketplace specification](https://code.claude.com/docs/en/plugin-marketplaces).

### Testing Locally

```bash
# Add local marketplace
/plugin marketplace add ./path/to/Skills

# Install plugin for testing
/plugin install biu@ming-kang-skills
```

## License

MIT License
