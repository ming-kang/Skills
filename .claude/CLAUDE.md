# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Claude Code plugin marketplace for distributing the user's commonly used plugins and skills. This repository serves as a personal marketplace for plugin distribution.

## Plugin: biu

biu ships three user-invocable skills: `/biu:interview`, `/biu:decompose`, and `/biu:archive`.

## Plugin Structure Rule

Claude Code skill supporting files belong inside the corresponding `skills/<skill-name>/` directory, alongside that skill's `SKILL.md` or in a subdirectory below it. biu uses `skills/<skill-name>/references/` for templates. Do not add a plugin-root `references/` directory for skill templates. For plugin skills, `${CLAUDE_SKILL_DIR}` points to the specific skill directory, not the plugin root.

## Git Workflow

- **`main` = published history.** Each push to `main` publishes the version currently in `plugins/biu/.claude-plugin/plugin.json`.
- **Development happens on temporary branches** named simply, e.g. `feat/<short>` or `fix/<short>`. The user decides the target version number, and `plugin.json` is bumped early on the branch. Commits during the cycle can be loose — they get squashed when the cycle ships.
- **Before any `git commit`**, draft the message and show it to the user for approval. Messages should explain what changed and why — detailed but not bloated.
- **Release flow** (triggered when the user says "push" or "release" on a feature branch):
  1. Confirm `plugin.json` version is correct and that `CLAUDE.md` / `README.md` are in sync with current behavior.
  2. `git checkout main && git merge --squash <branch>`.
  3. Draft the squash commit message in this form, get user approval, then commit:
     ```text
     biu vX.Y.Z: <one-line headline>

     - <change>
     - <change>
     ```
     For chore-only cycles that don't bump the version, drop `vX.Y.Z` and use a `chore: ...` headline instead.
  4. `git push` — this is the publication moment.
  5. `git branch -D <branch>` (capital `-D`: squash-merge isn't recorded as a merge).
- **Never push on every commit.** "push" from the user means "release the current cycle."

## References

> **Documentation Index**
> Fetch the complete documentation index at: https://code.claude.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

- Agent Skills specification: <https://agentskills.io/specification>
- Claude Code Plugins Reference: <https://code.claude.com/docs/en/plugins-reference>
- Claude Code Skills: <https://code.claude.com/docs/en/skills>
