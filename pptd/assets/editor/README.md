# PPT Design — local offline editor

Single-page, fully offline mirror of the **Kimi neo-ppt editor** (the public Kimi
Slides web frontend), saved from the live site and patched to run without any
cloud service. Served by `pptd/scripts/serve.mjs`.

- No iframe, no cloud sync / share / drive / AI endpoints — every legacy cloud
  request is intercepted in `index.html` and answered with an offline stub
- Open a local PPTD folder, edit in the official UI, save back automatically
- In-editor export uses the local patched WASM
  (`neo-ppt/assets/pptd_wasm_bg-DPPWdROu.wasm`, the single canonical copy)

## Start

From the `pptd/` skill folder:

```bash
node scripts/serve.mjs            # default 127.0.0.1:55173
node scripts/serve.mjs --open     # also open the browser
```

Open the root URL in the browser (not `file://`).

## Use

1. **Open a PPTD project folder** — Chromium-based browsers get read-write
   access; other browsers fall back to read-only folder upload
2. Edit in the official editor UI
3. Top-bar **Export** → PPTX / images (no sharing, no Google Drive)

## Structure

```text
index.html          # the only entry: official UI + local topbar shell
favicon.ico         # neutral brand mark
lib.js              # deck path / title helpers shared by the shell
local-bridge.js     # local bridge that replaces the Penpal parent page
local-shell.css     # topbar shell styles + offline chrome cleanup
neo-ppt/            # upstream mirror (bundled assets + editor fonts)
```

## Provenance and local patches

Source: the public Kimi neo-ppt editor frontend. Kimi / Moonshot is the upstream
origin only — nothing in this folder talks to Kimi services at runtime.

Local patches applied on top of the mirror:

- **Offline enforcement** — `index.html` carries a `'self'`-only
  `Content-Security-Policy`; it is what actually keeps this folder offline,
  regardless of what initiates a request. The older `fetch`/`XHR` interception
  in the same file (cloud endpoints answered with offline stubs) is kept as a
  second layer, but it cannot see a `<script>`, an `@font-face` or a
  `sendBeacon`, so it is not the enforcement point.
- **Remote assets vendored / SDKs neutered** — 25 `@font-face` URLs repointed
  from `statics.moonshot.cn` to `fonts/web/`, and the collect-rangers and APM
  screenshot `<script>` URLs replaced with an inert `data:text/javascript,`.
  These are declared as rules in `tools/pptd/patch-mirror.mjs`; reapply with
  `npm run pptd:patch-apply` after refreshing the mirror.
- **Branding removed** — page title is `PPT Design`; favicon, comment
  placeholders, feedback tips, font sample text, default deck names, document
  title suffixes, version-history labels, and PPTX author/company metadata are
  all neutral
- **Functional identifiers intentionally unchanged** — the `KimiBridge` window
  API, `KIMI_LOCALE` / `kimi-ppt-LOCALE` storage keys, `kimi-*` CSS classes,
  `kimi-*.js` chunk filenames (they are import specifiers), icon registry keys,
  and UA-sniffing regexes. Renaming any of these would break the bundle.
- **Deleted** — the unused upstream entry `neo-ppt/index.html` (the served
  entry is `index.html`); its meta tags still carried upstream branding.

Development notes, test suites, and invariants: `../../../tools/pptd/README.md`
(relative to this file, from the repository root).
