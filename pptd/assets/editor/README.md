# PPT Design — local offline editor

The single-page, fully offline editor for PPTD projects. It is a locally owned
build: the bundle under `app/`, the fonts under `fonts/`, and the shell files
next to them are maintained in this repository and are not refreshed from any
upstream. Served by `pptd/scripts/serve.mjs`.

- No iframe, no cloud sync / share / drive / AI endpoints — every legacy cloud
  request the bundle still knows about is answered locally in `index.html`
- Open a local PPTD folder, edit in the editor UI, save back automatically
- In-editor export uses the local patched WASM
  (`app/pptd_wasm_bg-DPPWdROu.wasm`, the single canonical copy)

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
2. Edit in the editor UI
3. Top-bar **Export** → PPTX / images (no sharing, no Google Drive)

## Structure

```text
index.html          # the only entry: editor bundle + local topbar shell
favicon.ico         # neutral brand mark
lib.js              # deck path / title helpers shared by the shell
local-bridge.js     # local bridge that replaces the Penpal parent page
local-shell.css     # topbar shell styles + offline chrome cleanup
app/                # the editor bundle: JS/CSS chunks, KaTeX fonts, both WASM files
fonts/web/          # @font-face sources for the 25 editor fonts (woff2)
fonts/fnt/          # length-prefixed font containers for the browser export path
```

Every path in the bundle is relative to this directory: the dependency maps
resolve `app/...` against the page, the WASM loaders resolve against
`import.meta.url`, and the `@font-face` rules point at `../fonts/web/`. The
editor therefore works from any host that serves this directory as its root.

## Offline guarantees

- **Offline enforcement** — `index.html` carries a `'self'`-only
  `Content-Security-Policy`; it is what actually keeps this folder offline,
  regardless of what initiates a request. The older `fetch`/`XHR` interception
  in the same file (cloud endpoints answered with offline stubs) is kept as a
  second layer, but it cannot see a `<script>`, an `@font-face` or a
  `sendBeacon`, so it is not the enforcement point.
- **No remote assets** — all fonts are served from `fonts/web/`, the telemetry
  and APM screenshot `<script>` URLs are an inert `data:text/javascript,`, and
  the icon CDN base is `./` (a request for it 404s locally instead of leaving
  the machine). `tools/pptd/check-editor.mjs` asserts all of this on every
  `npm test`.
- **Neutral branding** — page title is `PPT Design`; favicon, comment
  placeholders, feedback tips, font sample text, default deck names, document
  title suffixes, version-history labels, and PPTX author/company metadata are
  all neutral.
- **Functional identifiers left as built** — the `KimiBridge` window API,
  `KIMI_LOCALE` / `kimi-ppt-LOCALE` storage keys, `kimi-*` CSS classes,
  `kimi-*.js` chunk filenames (they are import specifiers), icon registry keys,
  and UA-sniffing regexes are part of the bundle's internal wiring. Renaming
  any of them means rebuilding the bundle, not editing it.

Development notes, test suites, and invariants: `../../../tools/pptd/README.md`
(relative to this file, from the repository root).
