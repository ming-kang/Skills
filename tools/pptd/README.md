# pptd — repository development notes

Repo-only tooling for the pptd skill. The distributable artifact is the `pptd/`
folder at the repository root (SKILL.md + references/ + scripts/ + assets/);
nothing in this directory ships with the skill.

## Layout

```text
tools/pptd/
  tests/           # python unittest suite for the exporters
    fixtures/      # minimal PPTD project + qa-deck (3 pages, local media)
  tests-node/      # node --test suite for scripts/serve.mjs and assets/editor/lib.js
  check-editor.mjs # offline / layout invariants of assets/editor (runs on every npm test)
  smoke_editor.mjs # manual browser check of the --project preview mode
```

## `pptd/scripts/` module map

The export scripts are flat sibling modules (no package: the skill ships as a
plain directory copy, and `python3 scripts/export_pptx.py` must work from any
cwd). Each module owns one layer:

| module | owns |
|---|---|
| `export_pptx.py` | CLI + the two export paths' orchestration (local WASM, browser) |
| `export_images.py` | the image-QA pipeline (dialog → ZIP → rename → stitch) |
| `clean_processes.py` | reclaiming the editor host and debug browser by hand |
| `pptd_common.py` | process running, temp dirs, `ensure_module()` (the one pip-install helper), `SKILL_DIR`, the canonical proxy env list |
| `pptd_deck.py` | manifest/pages reading + validation, payload.json, image maps |
| `pptd_browser.py` | agent-browser bootstrap, Windows debug-browser lifecycle, CDP, `EditorExportSession` (the shared drive flow) |
| `pptd_editor_host.py` | the local editor HTTP host + media mount (`EditorHost`) |
| `pptd_pptx.py` | slide-transition patching and output verification |
| `serve.mjs` | the interactive editor host (leases, idle watchdog, project mount) |
| `local-export/export-pptd.mjs` | the offline WASM writer |

Tests import these modules directly (they are the unit under test); the
orchestration tests load `export_pptx` via `importlib` and patch the module
that owns the function they exercise.

## Running tests

```bash
npm test                 # every skill in this repository
npm run test:pptd        # this skill only
node --test "tools/pptd/tests-node/*.test.js"
python -B -m unittest discover -s tools/pptd/tests -p "test_*.py"

# manual, needs Playwright's Chromium (devDependency at the repo root)
node tools/pptd/smoke_editor.mjs
```

Note: `agent-browser` upgrade and Node.js probing are fully mocked
(`unittest.mock.patch` in `tests/test_export_pptx.py`); the
`[pptd] agent-browser upgraded …` lines in the test output come from the mocked
code path, not a real global npm install.

Three suites are **environment-dependent** and skip themselves when the needed
binary is missing — they are the only tests that start a real browser:

- `DebugChromeLifecycleTests` — spawns a real Chrome/Chromium (system install
  or Playwright cache) and drives the spawn → register → reuse → reclaim cycle.
- `DownloadRedirectTests` — verifies that `Page.setDownloadBehavior` sends the
  editor's ZIP to our directory instead of the user's Downloads.
- `ExportImagesEndToEndTests` — runs the whole image-QA pipeline against
  `fixtures/qa-deck`; needs `agent-browser` on PATH plus a debug browser.

Each of them kills only the browser instance it started (pid from `netstat`,
tree kill, then waits for exit) and cleans up its temp directories. They leave
no Chrome or editor-host process behind.

## Invariants

- **Single canonical patched WASM.** `pptd/assets/editor/app/pptd_wasm_bg-DPPWdROu.wasm`
  is the only copy. Every exporter resolves it relative to the skill root;
  never duplicate it into scripts/ or tools/, and never copy-on-install.
  (`--wasm` exists only as a user override.)
- **Optional environment variables.** `PPTD_EDITOR_DIR` overrides the
  editor directory; `AGENT_BROWSER_CDP`, `PPTD_DEBUG_CHROME_PORT` and
  `PPTD_DEBUG_CHROME_IDLE_MINUTES` tune the Windows debug browser;
  `PPTD_SERVE_IDLE_MINUTES` tunes the editor host's idle timeout. None of them
  are required — the defaults keep export, image QA and editing offline and
  self-cleaning. Do not add env vars that change *what* is produced, and do not
  add network paths: PPTX export, image export, and editing must stay offline.
  A deck may still fetch remote images/fonts it references.
- **Background helpers clean up after themselves.** The editor host and the
  Windows debug browser register themselves (`%TEMP%/pptd-serve/*.json`,
  `%TEMP%/pptd-cdp.json`), exit on an idle timeout, and are reclaimable with
  `python pptd/scripts/clean_processes.py` (`npm run pptd:clean`). Reclaiming is
  gated by a signature: the entry must carry the skill's own profile directory
  and the pid must still be a browser launched with that profile. A pid that was
  recycled by another browser, or a command line that cannot be read, is left
  alone. Never add a cleanup path that can kill a browser the user owns.
- **Browser paths serve media, they do not embed it.** `open_local_editor()` is
  the single entry point for both browser paths: it builds the payload *and*
  starts the host, so the two halves cannot disagree. With the default
  `embed_media=False` the payload carries no base64 and the host serves the
  deck's media under `/__media__/` (media and font extensions only, project-
  relative paths, percent-decoded before the escape check). The editor fetches
  those files asynchronously, so a host must wait for
  `window.__NEODECK_PENDING_PROJECT_FETCHES__() === 0` before driving the UI —
  "deck ready" precedes the media, and clicking earlier loses images. The export
  summary reports `mediaDelivery` and `mediaRequests` so a silent placeholder
  render is visible.
- **The editor is offline by policy, not by blocklist.** `index.html` carries a
  `Content-Security-Policy` meta that allows `'self'` only; it is what actually
  holds the line. The older `blocked[]` shim patches `fetch`/`XHR` and therefore
  cannot see a `<script>`, a CSS `@font-face` or a `navigator.sendBeacon` — it is
  kept as a second layer that answers legacy cloud endpoints with a fake 200,
  not as the enforcement point. Two rules when touching the policy:
  - `script-src` **must** keep `data:`. The bundle's module loader probes
    `import.meta.resolve` through a `data:` script; without it the loader and
    the main chunk are both blocked and the page goes silently blank behind a
    bridge that still says "等待编辑器…". `'unsafe-eval'` is required to compile
    the WASM.
  - Never widen it to a remote origin. `tests-node/editor-browser.test.js`
    asserts zero CSP violations, zero off-host responses and a mounted `#app`
    on every `npm test`; `smoke_editor.mjs` repeats it with the export dialog
    and the heartbeat.
- **The bridge must be able to fail.** `local-bridge.js` publishes
  `document.documentElement.dataset.deckStatus` in *every* mode (`booting` →
  `loading` → `ready`, or `failed`/`error`), and an 8s handshake watchdog flips
  it to `failed` when the official bundle never calls `__NEODECK_CONNECT__`.
  The first page error is captured by an inline script in `index.html` — it has
  to be inline and first, because a CSP violation against the bundle fires
  before any module script runs — and is surfaced in the UI and in
  `window.__ND_ERRORS__`. Keep both: without them a blocked bundle is
  indistinguishable from a slow one, which is exactly how a blank editor once
  hid behind a green suite.
- **The editor tree is local and flat; `check-editor.mjs` guards it.**
  `pptd/assets/editor/` is the whole editor: `index.html` + shell files at the
  root, the bundle under `app/`, fonts under `fonts/`. There is no upstream to
  refresh from and no patch script to reapply — the bundle is edited in place
  when it has to change. `npm run pptd:check-editor` runs on every `npm test`
  and asserts the couplings that would otherwise live in someone's memory: the
  telemetry SDK and APM screenshot `<script>` URLs are an inert
  `data:text/javascript,`; every `@font-face` points at `../fonts/web/` and the
  file exists and is a woff2; Vite's dependency maps and the preload helper are
  rooted at `app/`; both WASM loaders resolve against `import.meta.url`; no
  `.js`/`.css` contains a forbidden host (`statics.moonshot.cn`,
  `lf3-data.volccdn.com`, `apm.volccdn.com`) or the historical `neo-ppt` base
  prefix. Fonts: 25 woff2 in `fonts/web/` (~50 MB, ASCII slug filenames;
  `font-family` names are unchanged so decks are unaffected) and the Latin
  `.fntdata` subset in `fonts/fnt/`. Remaining remote hostnames in the bundle
  (`www.kimi.com`, `gator.volces.com`, `api.iconify.design`, …) are dead string
  constants behind `location.origin` checks that are false locally; they never
  fired in an audit and the policy covers them if they ever do.
- **`fonts/fnt/*.fntdata` is not a web font, but the browser does fetch it.**
  It is a length-prefixed container the editor pulls from `${base}fonts/fnt/`
  (see `ThumbnailSlide-*.js`) to embed fonts on the browser export path, and
  the WASM exporter reads the same files. It cannot be used in `@font-face` —
  that is what `fonts/web/` is for — so keep the two directories distinct.
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
- **Editor bundle**: `pptd/assets/editor/app/` is the editor's compiled
  bundle (single-page offline editor, no iframe, no cloud APIs); it is owned by
  this repository and edited in place. The patched WASM above is the export
  "source of truth" it hosts. Changing a chunk means: edit the minified file,
  run `npm run pptd:check-editor`, then `npm test` and `node
  tools/pptd/smoke_editor.mjs` (the only checks that open the real page). Add
  an assertion to `check-editor.mjs` for every new coupling you introduce.
  - **Paths are root-relative to `assets/editor/`.** The bundle's dependency
    maps are `app/<chunk>`, the preload helper prefixes `./`, the WASM
    loaders use `import.meta.url`, `ThumbnailSlide` fetches
    `./fonts/fnt/<name>.fntdata`, and the CSS uses `../fonts/web/`. Keep it that
    way — the host serves this directory as `/`, and a mounted project lives
    under `/project/`, so nothing may assume another prefix.
  - **No ES5 fallback.** The bundle has no `*-legacy-*` chunks and
    `index.html` has no `nomodule` tag; the skill requires a Chromium-based
    browser.
- **Docs**: user-facing changes go to `docs/README.pptd.md` and the root
  `README.md` entry; the root `AGENTS.md` stays a repository-wide guideline and
  is not the place for skill-specific constraints.
