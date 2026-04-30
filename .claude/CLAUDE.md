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

This repo uses a **release-cycle branch + squash-merge** workflow. Each release maps to one dedicated branch (opened from `main`) and lands on `main` as exactly one squash-merged commit when published. `main` therefore equals "published history" — one commit per release, in chronological order; the active branch represents "the next release, in progress."

### Branching

Open one branch per release cycle. The branch may bundle multiple logical changes (feat + fix + chore mixed) — it represents the cycle, not a single atomic change.

**Naming**: `<type>/<short-name>` in lowercase kebab-case, 1–4 words. Pick the prefix and short-name from the **dominant theme** of the cycle:

- `feat/<short-name>` — cycle is primarily a new feature or substantive improvement (e.g., `feat/continuity-orphan-detect`)
- `fix/<short-name>` — cycle is primarily a bug fix (e.g., `fix/posttooluse-windows-glob`)
- `chore/<short-name>` — cycle is purely docs, refactors, or maintenance with no user-visible behavior change (e.g., `chore/readme-sync`)

A `fix`-themed cycle may still include small unrelated doc tweaks; that's fine — the dominant theme governs the name. Do not open separate branches per change within one release.

Name by content, not by target version. The version lives in `plugin.json` and may shift mid-cycle; the branch name should still make sense if it does.

**Lifecycle**:

1. Branch off up-to-date `main`: `git checkout main && git pull && git checkout -b <type>/<short-name>`.
2. Bump `plugin.json` to the target version early on the branch, so subsequent commits implicitly belong to it. Skip this step for chore-only cycles that don't ship a new plugin version.
3. Develop. Commits within the cycle can be loose (`wip: try X`, `fix typo`, `polish`) — they get squashed away on release.
4. When the user signals readiness to release, run the squash-merge release flow (see *Release / Versioning*).

Branches normally stay local; push to remote only if backup or hand-off is desired.

### Commit

When asked to commit, show the proposed commit message first for approval before executing `git commit -m ""`.

Two kinds of commits exist in this workflow, with different message standards:

- **In-progress commits on the active branch** — loose, working-style messages are fine (`wip: ...`, `fix typo`, `try alternate approach`). They get squashed away; nobody else sees them.
- **The release commit on `main`** — produced by `git merge --squash` followed by a fresh `git commit`. This is the single user-facing entry that survives in published history. Use the structured form:

  ```
  biu vX.Y.Z: <one-line headline summarizing the cycle>

  - <bullet for each change in the cycle, regardless of type>
  - <bullet>
  - <bullet>

  <optional notes, e.g., "no plugin code touched" for chore-only releases>
  ```

  For chore-only cycles that don't bump `plugin.json`, drop the `vX.Y.Z` and use a `chore: ...` headline instead (e.g., `chore: switch repo to feature-branch + squash-merge workflow`).

### Push

When asked to push:

1. Check `git status` for uncommitted changes.
2. If there are uncommitted changes: do NOT push. Enter the commit message drafting phase — show a proposed message for approval, then commit, then re-evaluate step 3.
3. Behavior depends on the current branch:
   - **On the active release branch**: "push" defaults to "ready to release" — propose the squash-merge release flow (see *Release / Versioning*) and ask for confirmation before merging. Only push the branch to remote if the user explicitly requests "branch backup" or similar.
   - **On `main`**: push to the remote GitHub repository. This publishes whatever version `plugin.json` currently advertises to installed users.

### Docs sync

After any commit that changes the plugin's code, structure, or observable behavior, check whether `.claude/CLAUDE.md` and `README.md` still accurately describe the current state. If the change invalidates anything in those files — directory tree, hook list, plugin features, runtime requirements, installation or usage instructions — update them in the same session, on the same branch, **before the squash-merge to `main`**. The release commit should land with docs already aligned.

Scope in: directory structure, hook event/purpose list, plugin feature list, runtime requirements, install/usage commands.
Scope out: commit-message-level internals, minor refactors with no user-visible surface change.

### Release / Versioning

The `version` field lives in **one place only**: `plugins/biu/.claude-plugin/plugin.json`. The marketplace entry in `.claude-plugin/marketplace.json` intentionally omits `version` — per the plugins reference, when both are set `plugin.json` wins, so we keep it single-source to avoid drift. A `git push` to `main` publishes whatever version `plugin.json` currently advertises — installed users pick up the new version on `/plugin marketplace update`.

**Release flow**:

1. Verify `plugin.json` reflects the intended published version. (Should already be set; bumping it is part of the cycle's early commits, not a last-minute fix.)
2. Verify CLAUDE.md and README.md are in sync (per *Docs sync* above).
3. Switch to `main`: `git checkout main`.
4. Squash-merge the active branch: `git merge --squash <type>/<short-name>`. All changes from the entire cycle land on `main`'s index as one diff; no commit yet.
5. Commit on `main` with a release-grade message (see *Commit* for the structured form).
6. Push: `git push`. This is the publication moment.
7. Delete the merged branch: `git branch -D <type>/<short-name>`. Use `-D` (capital), not `-d` — squash-merge does not preserve a merge link, so git considers the branch "unmerged" even though its content is now on `main`.

Do not push on every commit. "push" from the user signals "release the current cycle to users."

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
