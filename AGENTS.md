# Repo Contracts

This repository is a personal repository for agent Skills.

## Structure Rules

- Each usable skill is a top-level directory containing `SKILL.md`.
- Keep each skill's supporting files inside that skill directory.
- The entire skill directory is distributed as one unit. Keep only runtime instructions, runtime helpers, and reusable assets inside it; repository-only build sources, tests, and browser tooling belong under `tools/<skill>/`.
- Repository-wide tooling that applies to every skill (for example `tools/quick_validate.py`, the frontmatter validator) lives directly under `tools/`.
- Keep development dependencies at the repository root and generated review artifacts under `.artifacts/`; neither belongs in a distributable skill folder.
- Put templates and long reference material under `<skill>/references/`.
- Put runtime helper scripts under `<skill>/scripts/`.
- Put reusable assets under `<skill>/assets/`.
- Put user-facing documentation under `docs/` as `README.<name>.md`.

## Change Checklist

When changing skill behavior:

- Update the relevant `SKILL.md`.
- Update that skill's `references/*.md` template if generated artifacts change.
- Check whether `README.md` needs user-facing documentation updates.
- Confirm skill instructions and templates agree on filenames, statuses, frontmatter fields, and archive layout.

## Validation

```bash
git status --short
git diff --check
python tools/quick_validate.py   # SKILL.md frontmatter of every skill (needs PyYAML)
```

Run the frontmatter validator after any `SKILL.md` frontmatter change; it catches the YAML and spec errors that make installers reject a skill. `npm run validate:skills` is the same command.

For Visualize asset or helper changes, also run the relevant build, browser review, and regression checks documented in `docs/README.visualize.md`.

Before proposing a commit, review every changed file. Do not commit or push unless the user asks.
