# CLAUDE.md

This file guides Claude Code when maintaining this repository.

## Repository Purpose

This repository is a personal Claude Code plugin marketplace for distributing the user's commonly used plugins and skills.

The published marketplace entry is `.claude-plugin/marketplace.json`. The only current plugin is `biu`, defined at `plugins/biu/.claude-plugin/plugin.json`.

## Plugin: biu

`biu` is a lightweight development-document protocol. It ships three user-invocable skills:

- `/biu:interview` - clarify a development goal and produce `.biu/SPEC.md`.
- `/biu:decompose` - turn `.biu/SPEC.md` into `.biu/tasks/TASK-*.md` handoffs.
- `/biu:archive` - summarize and archive the completed `.biu/` cycle.

## Structure Rules

- Keep each skill's supporting files inside that skill directory: `plugins/biu/skills/<skill-name>/`.
- Put templates under `plugins/biu/skills/<skill-name>/references/`.
- Do not add a plugin-root `references/` directory for skill templates.
- For plugin skills, `${CLAUDE_SKILL_DIR}` points to the specific skill directory, not the plugin root.
- Keep `.biu/` git-ignored. It is user/project-local working state, not marketplace content.

## Change Checklist

When changing skill behavior, check the whole published surface before finishing:

- Update the relevant `plugins/biu/skills/<skill-name>/SKILL.md`.
- Update that skill's `references/*.md` template if the generated artifact changes.
- Check whether `README.md` needs user-facing documentation updates.
- Check whether this file needs maintenance-workflow updates.
- Check whether `plugins/biu/.claude-plugin/plugin.json` needs a version bump or metadata change.
- Check whether `.claude-plugin/marketplace.json` still describes the plugin accurately.

Do not bump the plugin version for documentation-only maintenance unless the user asks for a release version or the documentation change describes newly published behavior.

## Validation

There is no build or test suite for this repository. Validate changes by inspection:

- Run `git status --short` and review every changed file.
- Run `git diff --check` before proposing a commit or release.
- Confirm skill instructions and templates agree on filenames, statuses, frontmatter fields, and archive layout.
- Confirm `README.md`, `CLAUDE.md`, `plugin.json`, and `marketplace.json` are in sync with current behavior.

## Git Workflow

Develop directly on `main`. No feature branches.

Before any commit, draft the message for user approval. Commits stay local — never push individually.

When the user says "push" or "release":

1. Confirm `plugin.json` version is correct and `CLAUDE.md` / `README.md` are in sync.
2. Squash all local commits since last publish:
   ```bash
   git reset --soft $(git merge-base main origin/main)
   ```
3. Draft the squash commit message, get user approval, then commit:
   ```text
   biu vX.Y.Z: <one-line headline>
   
   - <change>
   - <change>
   ```
   For chore-only cycles, drop `vX.Y.Z` and use `chore: ...`.
4. `git push`. This is the publication moment.

## References

> Documentation index: https://code.claude.com/docs/llms.txt
>
> Use this index to discover available Claude Code documentation before exploring further.

- Agent Skills specification: <https://agentskills.io/specification>
- Claude Code Plugins Reference: <https://code.claude.com/docs/en/plugins-reference>
- Claude Code Skills: <https://code.claude.com/docs/en/skills>
