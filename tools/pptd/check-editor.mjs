#!/usr/bin/env node
/**
 * Verify the offline invariants of the pptd editor (`pptd/assets/editor/`).
 *
 * The editor is a locally owned build: the bundle under `app/`, the fonts under
 * `fonts/`, and the shell files next to them. This script proves that the tree
 * still holds the properties every functional test assumes:
 *
 *   - no CSS asset loads from a remote or host-absolute URL;
 *   - the patched WASM and its JS glue carry neutral export metadata;
 *   - the CSP in index.html still enforces `'self'` and still allows the
 *     `data:` probe the module loader needs;
 *   - every font the CSS and the bundle reference exists on disk.
 *
 * Usage:
 *   node tools/pptd/check-editor.mjs
 */

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";

const EDITOR_ROOT = resolve(import.meta.dirname, "..", "..", "pptd", "assets", "editor");
const APP_DIR = join(EDITOR_ROOT, "app");
const FONT_DIR = join(EDITOR_ROOT, "fonts");

const MAIN_CHUNK = "index-jtNAhQeK.js";
const MAIN_CSS = "index-Bn1xM_xZ.css";
const WASM = "pptd_wasm_bg-DPPWdROu.wasm";

/** An empty program: the <script> still loads, but nothing runs. */
const INERT_SCRIPT = "data:text/javascript,";

/** Metadata the patched WASM writes into every exported PPTX. */
const WASM_METADATA = [
  { needle: "urn:pptd:prov:provenance", count: 1 },
  { needle: "PPT Design (local)", count: 2 },
  { needle: "https://pptd.local/ns/2026/pptd/schema", count: 1 },
];

/**
 * Assertions about the bundle. Each one is a coupling that would otherwise
 * live in someone's memory; a failure means the editor tree was edited by hand
 * and needs a human, not a silent best-effort pass.
 */
const ASSERTIONS = [
  { id: "telemetry-inert", file: MAIN_CHUNK, needle: `Jo=\`${INERT_SCRIPT}\``, count: 1 },
  { id: "apm-inert", file: MAIN_CHUNK, needle: `ssUrl:\`${INERT_SCRIPT}\``, count: 1 },
  // The module loader's `import.meta.resolve` probe. It is the reason the CSP
  // must allow `data:` in script-src; assert it so the coupling stays visible.
  { id: "resolve-probe", file: MAIN_CHUNK, needle: `import'${INERT_SCRIPT}`, count: 1 },
  // Vite's dependency maps and the preload helper must point at app/, not at
  // a nested build directory.
  { id: "dep-map-base", file: MAIN_CHUNK, needle: `"app/${MAIN_CHUNK}"`, count: 1 },
  { id: "preload-base", file: "preload-helper-NECkhNH4.js", needle: "e.startsWith(`./`)?e:`./`+e", count: 1 },
  // The in-editor exporter loads the single canonical WASM next to itself.
  { id: "wasm-relative", file: "exportPPTXWasm-CNZG8r42.js", needle: `new URL(\`./${WASM}\`,import.meta.url)`, count: 1 },
  { id: "wasm-glue-relative", file: "pptd-wasm-glue-kDxO8uUJ.js", needle: `new URL(\`./${WASM}\`,\`\`+import.meta.url)`, count: 1 },
  // fntdata (browser export path) is fetched from `${base}fonts/fnt/`.
  { id: "fnt-base", file: "ThumbnailSlide-COLdjDXw.js", needle: "Y=`./`", count: 1 },
];

function countOccurrences(haystack, needle) {
  return haystack.split(needle).length - 1;
}

function readApp(file) {
  return readFileSync(join(APP_DIR, file), "utf-8");
}

function checkAssertions(failures) {
  for (const { id, file, needle, count } of ASSERTIONS) {
    const hits = countOccurrences(readApp(file), needle);
    if (hits !== count) failures.push(`${id}: expected ${count}x ${JSON.stringify(needle)} in ${file}, found ${hits}`);
  }
}

/** The CSS must not pull a remote or host-absolute URL. */
function checkBundleAssets(failures) {
  for (const file of readdirSync(APP_DIR)) {
    if (!file.endsWith(".css")) continue;
    const content = readApp(file);
    for (const match of content.matchAll(/url\(([^)]*)\)/g)) {
      const target = match[1].replace(/^["']|["']$/g, "");
      if (/^(https?:)?\/\//.test(target)) failures.push(`${file}: remote url(${target})`);
      else if (target.startsWith("/")) failures.push(`${file}: host-absolute url(${target})`);
    }
  }
}

/** The patched WASM and its JS glue must carry the neutral export metadata. */
function checkExportMetadata(failures) {
  const wasm = readFileSync(join(APP_DIR, WASM)).toString("latin1");
  for (const { needle, count } of WASM_METADATA) {
    const hits = countOccurrences(wasm, needle);
    if (hits !== count) failures.push(`${WASM}: expected ${count}x ${JSON.stringify(needle)}, found ${hits}`);
  }
  const appName = "PPT Design";
  if (countOccurrences(wasm, appName) < 3) {
    failures.push(`${WASM}: producer/statement/application metadata is not neutral`);
  }
  const glue = readApp("exportPPTXWasm-CNZG8r42.js");
  const namespace = "https://pptd.local/ns/2026/pptd/schema";
  if (countOccurrences(glue, namespace) !== 1) {
    failures.push(`exportPPTXWasm-CNZG8r42.js: expected one ${namespace}`);
  }
}

/** The CSP in index.html is the enforcement point; a missing `data:` blanks the app. */
function checkContentSecurityPolicy(failures) {
  const html = readFileSync(join(EDITOR_ROOT, "index.html"), "utf-8");
  const match = html.match(/http-equiv="Content-Security-Policy"\s*\n?\s*content="([^"]+)"/);
  if (!match) {
    failures.push("index.html has no Content-Security-Policy meta");
    return;
  }
  const policy = match[1];
  const scriptSrc = policy.match(/script-src ([^;]+)/)?.[1] ?? "";
  if (!/\bdata:/.test(scriptSrc)) {
    failures.push(
      "CSP script-src is missing `data:` — the bundle's module loader probes " +
        "import.meta.resolve through a data: script, and without it the editor " +
        "renders a blank page while the bridge still reports progress",
    );
  }
  if (!/default-src 'self'/.test(policy)) {
    failures.push("CSP has no `default-src 'self'` — the offline invariant is not enforced");
  }
  for (const [, href] of html.matchAll(/(?:src|href)="([^"]+)"/g)) {
    if (/^(https?:)?\/\//.test(href)) failures.push(`index.html loads a remote resource: ${href}`);
  }
}

/** Every font the CSS and the bundle reference must exist on disk. */
function checkFontFiles(failures) {
  const css = readApp(MAIN_CSS);
  const webFonts = [...css.matchAll(/url\(\.\.\/fonts\/web\/([^)]+)\)/g)].map((m) => m[1]);
  if (!webFonts.length) failures.push(`${MAIN_CSS}: no local @font-face rules found`);
  for (const name of webFonts) {
    const path = join(FONT_DIR, "web", name);
    if (!existsSync(path)) {
      failures.push(`missing font file fonts/web/${name}`);
      continue;
    }
    const magic = readFileSync(path).subarray(0, 4).toString("latin1");
    if (magic !== "wOF2") failures.push(`fonts/web/${name} is not a woff2 (magic ${JSON.stringify(magic)})`);
  }
  // fntdata files feed the browser export path. Only the Latin subset ships
  // (the CJK ones were never vendored), so require the directory, not the list.
  const fnt = existsSync(join(FONT_DIR, "fnt")) ? readdirSync(join(FONT_DIR, "fnt")) : [];
  if (!fnt.some((name) => name.endsWith(".fntdata"))) failures.push("fonts/fnt/ has no .fntdata files");
  if (!existsSync(join(APP_DIR, WASM))) failures.push(`missing app/${WASM} (the single canonical patched WASM)`);
}

const failures = [];
checkAssertions(failures);
checkBundleAssets(failures);
checkExportMetadata(failures);
checkContentSecurityPolicy(failures);
checkFontFiles(failures);

if (failures.length) {
  console.error(`FAIL  editor invariants (${failures.length} problem(s))`);
  for (const line of failures) console.error(`  - ${line}`);
  process.exitCode = 1;
} else {
  console.log(`OK  editor invariants hold (${ASSERTIONS.length} assertions, export metadata neutral, fonts present)`);
}
