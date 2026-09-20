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
  smoke_editor.mjs # manual browser check of the --project preview mode
```

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

- **Single canonical patched WASM.** `pptd/assets/editor/neo-ppt/assets/pptd_wasm_bg-DPPWdROu.wasm`
  is the only copy. Every exporter resolves it relative to the skill root;
  never duplicate it into scripts/ or tools/, and never copy-on-install.
  (`--wasm` exists only as a user override.)
- **Optional environment variables.** `PPTD_EDITOR_DIR` overrides the
  editor mirror directory (the legacy alias `OPEN_KIMI_PPT_EDITOR` is still
  honored); `AGENT_BROWSER_CDP`, `PPTD_DEBUG_CHROME_PORT` and
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
- **Mirror patches live in `patch-mirror.mjs`, never in someone's memory.**
  The upstream mirror shipped 25 `@font-face` rules pointing at
  `statics.moonshot.cn` and loaded a ByteDance telemetry SDK
  (`lf3-data.volccdn.com`, collect-rangers) plus an APM screenshot helper
  (`apm.volccdn.com`) from `<script>` tags. Those edits are now declared as
  rules: `npm run pptd:patch-apply` reapplies them (and fetches any missing
  font) after a mirror refresh, `npm run pptd:patch-check` runs on every
  `npm test`. Every rule carries an expected hit count, because the string
  `neo-ppt` alone appears 13 times in the bundle and **two of them must not be
  touched** — an APM `pid:'/neo-ppt'` and a share URL in `ShareDialog`. A rule
  that matches a different number of times fails loudly instead of quietly
  mangling the bundle. Fonts live in `neo-ppt/fonts/web/` (25 woff2, ~50 MB,
  ASCII slug filenames; `font-family` names are unchanged so decks are
  unaffected). Remaining remote hostnames in the bundle (`www.kimi.com`,
  `gator.volces.com`, `api.iconify.design`, …) are dead string constants behind
  `location.origin` checks that are false locally; they never fired in an audit
  and the policy covers them if they ever do.
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
- **Vendored editor mirror**: `pptd/assets/editor/neo-ppt/` is a locally
  patched vendored copy of Kimi's public neo-ppt frontend (single-page offline
  mirror, no iframe, no cloud APIs). The patched WASM above is the export
  "source of truth" it hosts. When refreshing the mirror, record the upstream
  origin, version/commit, and the applied patch list here.
  - **Refreshing the mirror**: drop the new upstream build in, then run
    `npm run pptd:patch-apply` (reapplies every rule, fetches missing fonts,
    and verifies the result) followed by `npm test` and `node
    tools/pptd/smoke_editor.mjs`. The rules themselves are declared in
    `patch-mirror.mjs` — that file, not this list, is the source of truth.
  - **Legacy bundle removed.** The upstream `*-legacy-*` chunks (ES5 fallback,
    64 files / ~5 MB) were deleted: the served `index.html` has no `nomodule`
    tag and nothing in the module graph references them, and the skill requires
    a Chromium-based browser anyway. Verified by serving the mirror and
    fetching every entry asset plus the main chunk's imports (all 200). Redo
    that check after any mirror refresh before deleting them again.
- **Docs**: user-facing changes go to `docs/README.pptd.md` and the root
  `README.md` entry; the root `AGENTS.md` stays a repository-wide guideline and
  is not the place for skill-specific constraints.
