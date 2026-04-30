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
                    └── templates/          # COMPASS / plan / task / analysis templates
```

## Plugin: biu

The `biu` plugin provides spec-driven workflow capabilities for complex development tasks. It includes:

- **spec-coding skill**: Structured workflow with analysis and task decomposition phases. Slash-only invocation (`disable-model-invocation: true`); Claude will not auto-trigger it on phrases.
- **Subagents**: `analyzer` (codebase analysis; writes `.biu/analysis/*.md` directly) and `architect` (task decomposition; writes `.biu/tasks/*.md` and updates COMPASS.md), defined in `agents/` at the plugin root.
- **Lifecycle hooks** (pure bash, zero runtime deps):
  - `SubagentStop` on analyzer/architect — verifies artifacts exist, are non-empty, and have the required structure; exit 2 + stderr feeds the missing-artifact list back to the subagent so it can self-correct.
  - `PostToolUse` on Edit/Write — when a `task-N-*.md` file is left with `Status: COMPLETE`, injects a soft reminder telling the model to STOP and not auto-advance to the next Task.
- **Templates**: `templates/compass.md` (canonical COMPASS state structure), `templates/plan.md` (canonical plan.md structure), `templates/task.md`, and `templates/analysis.md` — all referenced from SKILL.md and the subagents, never restated inline.

Continuity between sessions is handled by reading `.biu/COMPASS.md` for state and `.biu/plan.md` for the confirmed spec — neither is a predigested session-state cache. COMPASS is the single source of truth for cycle state; plan.md for the spec.

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

### Branching

Feature work happens on dedicated branches off `main`, never directly on `main`. This keeps `main` semantically equal to "published history" — one commit per release, linear, in user-visible order.

**Naming**: `<type>/<short-name>` in lowercase kebab-case, 1–4 words.

- `feat/<short-name>` — new functionality, behavior change, or substantive improvement (e.g., `feat/continuity-orphan-detect`)
- `fix/<short-name>` — bug fix observable to users (e.g., `fix/posttooluse-windows-glob`)
- `chore/<short-name>` — docs, refactors, dependency bumps with no user-visible behavior change (e.g., `chore/readme-sync`)

Name by content, not by target version. The version lives in `plugin.json` and may shift mid-development; the branch name should still make sense if the version does.

**Lifecycle**: branch off `main` → commit freely (wip/fixup/polish commits are fine, they get squashed) → squash-merge back to `main` as one clean release commit → delete the branch. Feature branches normally stay local; push to remote only if backup or hand-off is desired.

### Commit

When asked to commit, show the proposed commit message first for approval before executing `git commit -m ""`.

On a feature branch, in-progress commit messages can be loose (`wip: try X`, `fix typo`) since they will be squashed away. The release commit on `main` (produced by squash-merge) is the user-facing one and gets the careful `biu vX.Y.Z: ...` treatment with a structured body.

### Push

When asked to push:
1. Check `git status` for uncommitted changes.
2. If there are uncommitted changes: do NOT push. Enter the commit message drafting phase — show a proposed message for approval, then commit, then evaluate step 3.
3. Branch the behavior on the current branch:
   - **On a feature branch**: "push" is ambiguous. Default-interpret it as "ready to release" — propose the squash-merge-and-release flow (see *Release / Versioning* below) and ask for confirmation before merging. Only push the feature branch to remote if the user explicitly asks for "branch backup" or similar.
   - **On `main`**: push to the remote GitHub repository. This publishes the version currently in `plugin.json` to installed users.

### Docs sync

After any commit or push that changes the plugin's code, structure, or observable behavior, check whether `.claude/CLAUDE.md` and `README.md` still accurately describe the current state. If the change invalidates anything in those files — directory tree, hook list, plugin features, runtime requirements, installation or usage instructions — update them in the same session (typically as part of the same feature branch, before squash-merge). Stale docs are a worse bug than missing docs.

Scope in: directory structure, hook event/purpose list, plugin feature list, runtime requirements, install/usage commands.
Scope out: commit-message-level internals, minor refactors with no user-visible surface change.

### Release / Versioning

The `version` field lives in **one place only**: `plugins/biu/.claude-plugin/plugin.json`. The marketplace entry in `.claude-plugin/marketplace.json` intentionally omits `version` — per the plugins reference, when both are set `plugin.json` wins, so we keep it single-source to avoid drift. A `git push` to `main` publishes whatever version `plugin.json` currently advertises — installed users pick up the new version on `/plugin marketplace update`.

**Release flow**:

1. From up-to-date `main`, branch off: `git checkout main && git pull && git checkout -b <type>/<short-name>`.
2. Bump `plugin.json` version on the branch (typically as one of the early commits, so subsequent commits implicitly belong to that version).
3. Develop with as many local commits as needed — they are squash material, not history material.
4. When the user signals readiness to release:
   - Verify `plugin.json` reflects the intended published version.
   - Verify CLAUDE.md and README.md are in sync (per *Docs sync* above).
   - On `main`: `git merge --squash <type>/<short-name>`, then commit with a release-grade message (`biu vX.Y.Z: ...` headline + bulleted body summarizing user-visible changes).
   - Push `main` to remote.
   - Delete the merged branch: `git branch -D <type>/<short-name>`.

Do not push on every commit. "push" from the user signals "release the current version to users."

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
