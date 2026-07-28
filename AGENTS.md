# Repo Guideline

## Repository Purpose

This repository is a personal source repository for agent Skills.

## Structure Rules

- Each usable skill is a top-level directory containing `SKILL.md`. Skill directories are flat — no nested grouping folders.
- Keep each skill's supporting files inside that skill directory.
- Put templates and long reference material under `<skill>/references/`.
- Put helper scripts under `<skill>/scripts/`.
- Put reusable assets under `<skill>/assets/`.
- Put user-facing documentation under `docs/` as `README.<name>.md` (e.g. `docs/README.biu.md`, `docs/README.visualize.md`). The root `README.md` is a short index that links to these files.

## Change Checklist

When changing skill behavior:

- Update the relevant `SKILL.md`.
- Update that skill's `references/*.md` template if generated artifacts change.
- Check whether `README.md` needs user-facing documentation updates.
- Confirm skill instructions and templates agree on filenames, statuses, frontmatter fields, and archive layout.

## Validation

There is no build or test suite for this repository. Validate changes by inspection:

```bash
git status --short
git diff --check
```

Before proposing a commit, review every changed file. Do not commit or push unless the user asks.
