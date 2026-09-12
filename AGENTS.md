# Repo Guideline

## Repository Purpose

This repository is a personal source repository for agent Skills.

## Structure Rules

- Each usable skill is a top-level directory containing `SKILL.md`. Skill directories are flat — no nested grouping folders.
- Keep each skill's supporting files inside that skill directory.
- The entire skill directory is distributed as one unit. Keep only runtime instructions, runtime helpers, and reusable assets inside it; repository-only build sources, tests, and browser tooling belong under `tools/<skill>/`.
- Keep development dependencies at the repository root and generated review artifacts under `.artifacts/`; neither belongs in a distributable skill folder.
- Put templates and long reference material under `<skill>/references/`.
- Put runtime helper scripts under `<skill>/scripts/`.
- Put reusable assets under `<skill>/assets/`.
- Put user-facing documentation under `docs/` as `README.<name>.md` (e.g. `docs/README.visualize.md`, `docs/README.code-quality-review.md`). The root `README.md` is a short index that links to these files.

## Change Checklist

When changing skill behavior:

- Update the relevant `SKILL.md`.
- Update that skill's `references/*.md` template if generated artifacts change.
- Check whether `README.md` needs user-facing documentation updates.
- Confirm skill instructions and templates agree on filenames, statuses, frontmatter fields, and archive layout.

## Validation

Validate changes by inspection:

```bash
git status --short
git diff --check
```

For Visualize asset or helper changes, also run the relevant build, browser review, and regression checks documented in `docs/README.visualize.md`.

Before proposing a commit, review every changed file. Do not commit or push unless the user asks.
