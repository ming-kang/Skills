# pptd — repository development notes

Repo-only tooling for the pptd skill. The distributable artifact is the `pptd/`
folder at the repository root (SKILL.md + references/ + scripts/ + assets/);
nothing in this directory ships with the skill.

## Layout

```text
tools/pptd/
  tests/           # python unittest suite for the exporters
    fixtures/      # minimal PPTD project used by the tests
  tests-node/      # node --test suite for scripts/serve.mjs and assets/editor/lib.js
```

## Running tests

```bash
npm test                 # every skill in this repository
npm run test:pptd        # this skill only
node --test "tools/pptd/tests-node/*.test.js"
python -B -m unittest discover -s tools/pptd/tests -p "test_*.py"
```

Note: the python suite upgrades the global `agent-browser` to >= 0.33.2 when
an older version is present. That is expected behavior of the runtime path,
not a test side effect to guard against.

## Invariants

- **Single canonical patched WASM.** `pptd/assets/editor/neo-ppt/assets/pptd_wasm_bg-DPPWdROu.wasm`
  is the only copy. Every exporter resolves it relative to the skill root;
  never duplicate it into scripts/ or tools/, and never copy-on-install.
  (`--wasm` exists only as a user override.)
- **One optional environment variable.** `PPTD_EDITOR_DIR` overrides the
  editor mirror directory (the legacy alias `OPEN_KIMI_PPT_EDITOR` is still
  honored); `AGENT_BROWSER_CDP` is internal. Do not add env vars or network
  paths — PPTX export, image export, and editing must stay offline. A deck may
  still fetch remote images/fonts it references.
- **SKILL.md paths are folder-relative only.** No absolute install paths, no
  `npx` commands. The skill is a plain directory copy.
- **Skill self-containment.** Anything the skill needs at runtime lives inside
  `pptd/`. Repo-only sources, tests, and browser tooling live here.

## Working on the skill

- **Design presets**: `pptd/references/design_system/README.md` is the index of
  all 44 presets (30 primary + 14 extra). Adding/removing a preset means
  updating that index in the same change.
- **Vendored editor mirror**: `pptd/assets/editor/neo-ppt/` is a locally
  patched vendored copy of Kimi's public neo-ppt frontend (single-page offline
  mirror, no iframe, no cloud APIs). The patched WASM above is the export
  "source of truth" it hosts. When refreshing the mirror, record the upstream
  origin, version/commit, and the applied patch list here.
- **Docs**: user-facing changes go to `docs/README.pptd.md` and the root
  `README.md` entry; the root `AGENTS.md` stays a repository-wide guideline and
  is not the place for skill-specific constraints.
