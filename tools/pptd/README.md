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

Note: the suites have no system side effects. `agent-browser` upgrade and
Node.js probing are fully mocked (`unittest.mock.patch` in
`tests/test_export_pptx.py`); the `[pptd] agent-browser upgraded …` lines in the
test output come from the mocked code path, not a real global npm install.

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
- **No npm dependency next to the skill.** `export_pptx.py` parses the project
  with PyYAML and passes `export-pptd.mjs --json`; the mjs YAML chain (npm
  `yaml` → `js-yaml` → `PPTD_PYTHON`/`python3`/`python`/`py`) exists only for
  direct `node export-pptd.mjs` use. Never make the default export path depend
  on a node package — the skill ships as a plain directory with no
  `node_modules`.
- **Clean the tree before packaging.** Running the scripts leaves
  `pptd/scripts/__pycache__/` behind. It is gitignored but still on disk, and a
  directory-copy install would ship it; delete it before distributing.

## Working on the skill

- **Design presets**: `pptd/references/design_system/README.md` is the index of
  all 44 presets (30 primary + 14 extra). Adding/removing a preset means
  updating that index in the same change.
- **Vendored editor mirror**: `pptd/assets/editor/neo-ppt/` is a locally
  patched vendored copy of Kimi's public neo-ppt frontend (single-page offline
  mirror, no iframe, no cloud APIs). The patched WASM above is the export
  "source of truth" it hosts. When refreshing the mirror, record the upstream
  origin, version/commit, and the applied patch list here.
  - **Legacy bundle removed.** The upstream `*-legacy-*` chunks (ES5 fallback,
    64 files / ~5 MB) were deleted: the served `index.html` has no `nomodule`
    tag and nothing in the module graph references them, and the skill requires
    a Chromium-based browser anyway. Verified by serving the mirror and
    fetching every entry asset plus the main chunk's imports (all 200). Redo
    that check after any mirror refresh before deleting them again.
- **Docs**: user-facing changes go to `docs/README.pptd.md` and the root
  `README.md` entry; the root `AGENTS.md` stays a repository-wide guideline and
  is not the place for skill-specific constraints.
