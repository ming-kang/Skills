# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Claude Code plugin marketplace — distributing the user's commonly used plugins and skills. This repository serves as a personal marketplace for plugin distribution.

## Directory Structure

```
Skills/ (marketplace root)
├── .claude-plugin/
│   └── marketplace.json    # Marketplace catalog
│
└── plugins/
    └── biu/                # Biu plugin — spec-driven workflow
        ├── .claude-plugin/
        │   └── plugin.json # Plugin manifest (single source of truth for version)
        ├── agents/
        │   ├── analyzer.md             # Codebase analysis subagent (Phase 1)
        │   └── architect.md            # Task decomposition subagent (Phase 3)
        ├── hooks/                      # Pure bash, zero runtime deps
        │   ├── hooks.json              # Hook event registrations
        │   ├── verify-analyzer.sh      # SubagentStop gate: analyzer artifacts
        │   ├── verify-architect.sh     # SubagentStop gate: architect artifacts
        │   └── notify-task-complete.sh # PostToolUse reminder when a Task flips to COMPLETE
        └── skills/
            └── spec-coding/
                ├── SKILL.md            # Entry point + phase skeleton
                └── references/
                    ├── implementation.md   # Phase 4 per-Task loop (lazy-loaded)
                    ├── blocked-protocol.md # BLOCKED state protocol (lazy-loaded)
                    ├── archive.md          # Phase 5 archive procedure (lazy-loaded)
                    └── templates/          # COMPASS / task / analysis templates
```

## Plugin: biu

The `biu` plugin provides spec-driven workflow capabilities for complex development tasks. It includes:

- **spec-coding skill**: Structured workflow with analysis and task decomposition phases. Slash-only invocation (`disable-model-invocation: true`); Claude will not auto-trigger it on phrases.
- **Subagents**: `analyzer` (codebase analysis; writes `.spec/analysis/*.md` directly) and `architect` (task decomposition; writes `.spec/tasks/*.md` and updates COMPASS.md), defined in `agents/` at the plugin root.
- **Lifecycle hooks** (pure bash, zero runtime deps):
  - `SubagentStop` on analyzer/architect — verifies artifacts exist, are non-empty, and have the required structure; exit 2 + stderr feeds the missing-artifact list back to the subagent so it can self-correct.
  - `PostToolUse` on Edit/Write — when a `task-N-*.md` file is left with `Status: COMPLETE`, injects a soft reminder telling the model to STOP and not auto-advance to the next Task.
- **Templates**: `templates/compass.md` (canonical COMPASS structure), `templates/task.md`, and `templates/analysis.md` — all referenced from SKILL.md and the subagents, never restated inline.

Continuity between sessions is handled by reading `.spec/COMPASS.md` directly — there is no predigested session-state cache. COMPASS is the single source of truth for cycle state.

### Installation

Users can install the biu plugin from this marketplace:

```bash
# Add the marketplace
/plugin marketplace add ming-kang/Skills

# Install the biu plugin
/plugin install biu@ming-kang-skills
```

### Usage

After installation, use the spec-coding skill:

```bash
/biu:spec-coding
```

## Git Workflow

### Commit

When asked to commit, show the proposed commit message first for approval before executing `git commit -m ""`.

### Push

When asked to push:
1. Check `git status` for uncommitted changes
2. If there are uncommitted changes: do NOT push. Enter the commit message drafting phase — show a proposed message for approval, then commit, then push.
3. If all changes are committed: push to the remote GitHub repository.

### Docs sync

After any commit or push that changes the plugin's code, structure, or observable behavior, check whether `.claude/CLAUDE.md` and `README.md` still accurately describe the current state. If the change invalidates anything in those files — directory tree, hook list, plugin features, runtime requirements, installation or usage instructions — update them in the same session. Stale docs are a worse bug than missing docs.

Scope in: directory structure, hook event/purpose list, plugin feature list, runtime requirements, install/usage commands.
Scope out: commit-message-level internals, minor refactors with no user-visible surface change.

### Release / Versioning

The `version` field lives in **one place only**: `plugins/biu/.claude-plugin/plugin.json`. The marketplace entry in `.claude-plugin/marketplace.json` intentionally omits `version` — per the plugins reference, when both are set `plugin.json` wins, so we keep it single-source to avoid drift. A `git push` to `main` publishes whatever version `plugin.json` currently advertises — installed users pick up the new version on `/plugin marketplace update`.

When starting work on a new version, bump `plugin.json` locally first. Multiple commits may land on `main` locally under the same in-progress version before we push. Do not push on every commit — wait for an explicit "push" from the user, which signals "release the current version to users." Before pushing, verify that `plugin.json` reflects the intended published version.

## References

> **Documentation Index**
> Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

- Agent Skills specification: <https://agentskills.io/specification>
- Anthropic Claude Code Skills docs: <https://code.claude.com/docs/en/skills>
- Claude Code Plugins Reference: <https://code.claude.com/docs/en/plugins-reference>
- Claude Code Hooks Reference: <https://code.claude.com/docs/en/hooks>
- Claude Code Skills: <https://code.claude.com/docs/en/skills>
- Claude Code Sub-agents: <https://code.claude.com/docs/en/sub-agents>
