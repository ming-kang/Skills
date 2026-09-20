#!/usr/bin/env node
/**
 * Reapply and verify the offline patches on the vendored neo-ppt mirror.
 *
 * The mirror under `pptd/assets/editor/neo-ppt/` is an upstream build artifact.
 * Making it offline needs a handful of edits to minified files, and those edits
 * are invisible to every functional test: drop a fresh upstream mirror in and
 * the editor still works perfectly — it just starts phoning home again. This
 * script is the single place those edits are declared, so a mirror refresh is
 * `--apply` instead of an archaeology session.
 *
 * Every rule carries an expected hit count. That is not decoration: the string
 * `neo-ppt` alone appears 13 times in the bundle, and two of them (an APM
 * project id `pid:'/neo-ppt'` and a share URL in ShareDialog) must NOT be
 * touched. A rule that suddenly matches a different number of times means
 * upstream moved and the rule needs a human, not a silent best-effort edit.
 *
 * Usage:
 *   node tools/pptd/patch-mirror.mjs --check   # verify only, no writes (CI)
 *   node tools/pptd/patch-mirror.mjs --apply   # patch a freshly dropped mirror
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { resolve, join } from "node:path";

const EDITOR_ROOT = resolve(import.meta.dirname, "..", "..", "pptd", "assets", "editor");
const BUNDLE_DIR = join(EDITOR_ROOT, "neo-ppt", "assets");
const FONT_DIR = join(EDITOR_ROOT, "neo-ppt", "fonts", "web");

const MAIN_CHUNK = "index-jtNAhQeK.js";
const MAIN_CSS = "index-Bn1xM_xZ.css";

/** An empty program: the <script> still loads, but nothing runs. */
const INERT_SCRIPT = "data:text/javascript,";

/**
 * Remote fonts, as `[upstream url, local replacement]`. Non-ASCII family names
 * get a transliterated slug so the repo stays portable; the `font-family` name
 * in the CSS is untouched, so decks referencing 得意黑 keep working.
 */
const FONTS = [
  ["//statics.moonshot.cn/neo-design/fonts/css/MiSans.woff2", "MiSans"],
  ["//statics.moonshot.cn/neo-design/fonts/css/Liter.woff2", "Liter"],
  ["//statics.moonshot.cn/neo-design/fonts/css/Oranienbaum.woff2", "Oranienbaum"],
  ["//statics.moonshot.cn/neo-design/fonts/css/HedvigLettersSans.woff2", "HedvigLettersSans"],
  ["//statics.moonshot.cn/neo-design/fonts/css/QuattrocentoSans.woff2", "QuattrocentoSans"],
  ["//statics.moonshot.cn/neo-design/fonts/css/SortsMillGoudy.woff2", "SortsMillGoudy"],
  ["//statics.moonshot.cn/neo-design/fonts/css/Unna.woff2", "Unna"],
  ["//statics.moonshot.cn/neo-design/fonts/css/LuckiestGuy.woff2", "LuckiestGuy"],
  ["//statics.moonshot.cn/neo-design/fonts/css/Coda.woff2", "Coda"],
  ["//statics.moonshot.cn/neo-design/fonts/css/Jersey15.woff2", "Jersey15"],
  ["//statics.moonshot.cn/neo-design/fonts/css/PressStart2P.woff2", "PressStart2P"],
  ["//statics.moonshot.cn/neo-design/fonts/css/Jersey20Charted.woff2", "Jersey20Charted"],
  ["//statics.moonshot.cn/neo-design/fonts/css/Noto%20Sans%20SC.woff2", "NotoSansSC"],
  ["//statics.moonshot.cn/neo-design/fonts/css/%E6%80%9D%E6%BA%90%E5%AE%8B%E4%BD%93.woff2", "SourceHanSerifSC"],
  ["//statics.moonshot.cn/neo-design/fonts/css/%E9%98%BF%E9%87%8C%E5%A6%88%E5%A6%88%E5%88%80%E9%9A%B6%E4%BD%93.woff2", "AlimamaDaoLiTi"],
  ["//statics.moonshot.cn/neo-design/fonts/css/%E7%AB%99%E9%85%B7%E6%96%87%E8%89%BA%E4%BD%93.woff2", "ZCOOLWenYiTi"],
  ["//statics.moonshot.cn/neo-design/fonts/css/ZCOOLQingKeHuangYou-Regular.woff2", "ZCOOLQingKeHuangYou"],
  ["//statics.moonshot.cn/neo-design/fonts/css/%E9%A3%9E%E6%B3%A2%E6%AD%A3%E7%82%B9%E4%BD%93.woff2", "FeiBoZhengDianTi"],
  ["//statics.moonshot.cn/neo-design/fonts/css/%E7%A8%8B%E8%8D%A3%E5%85%89%E5%88%BB%E6%A5%B7.woff2", "ChengRongGuangKeKai"],
  ["//statics.moonshot.cn/neo-design/fonts/css/%E5%BE%97%E6%84%8F%E9%BB%91.woff2", "DeYiHei"],
  ["//statics.moonshot.cn/neo-design/fonts/css/%E7%B2%BE%E5%93%81%E7%82%B9%E9%98%B5%E4%BD%939%C3%979%201.6.woff2", "JingPinDianZhenTi"],
  ["//statics.moonshot.cn/neo-design/fonts/css/Long%20Cang.woff2", "LongCang"],
  ["//statics.moonshot.cn/neo-design/fonts/css/LXGW%20Bright.woff2", "LXGWBright"],
  ["//statics.moonshot.cn/neo-design/fonts/css/ZCOOL%20KuaiLe.woff2", "ZCOOLKuaiLe"],
  ["//statics.moonshot.cn/neo-design/fonts/css/%E9%9C%9E%E9%B9%9C%E6%96%B0%E8%87%B4%E5%AE%8B.woff2", "XiaWuXinZhiSong"],
];

/**
 * Hosts we actively removed. Unlike the bundle's many dead string constants
 * (www.kimi.com, api.iconify.design, …) which sit behind `location.origin`
 * checks that are false locally, these three were live request paths.
 */
const FORBIDDEN_HOSTS = ["statics.moonshot.cn", "lf3-data.volccdn.com", "apm.volccdn.com"];

/** Each rule: replace `from` with `to` in `file`, exactly `expect` times. */
const RULES = [
  {
    id: "R1-telemetry",
    file: MAIN_CHUNK,
    from: "https://lf3-data.volccdn.com/obj/data-static/log-sdk/collect/5.0/collect-rangers-v5.1.12.js",
    to: INERT_SCRIPT,
    expect: 1,
    note: "ByteDance collect-rangers SDK, injected via <script> on every open",
  },
  {
    id: "R2-apm-screenshot",
    file: MAIN_CHUNK,
    from: "https://apm.volccdn.com/mars-web/apmplus/web/html2canvas.min.js",
    to: INERT_SCRIPT,
    expect: 1,
    note: "APM screenshot helper, loaded on error reporting",
  },
  ...FONTS.map(([url, slug]) => ({
    id: `R3-font-${slug}`,
    file: MAIN_CSS,
    from: `url(${url})`,
    to: `url(../fonts/web/${slug}.woff2)`,
    expect: 1,
    note: "remote @font-face",
  })),
];

/**
 * Assertions about the patched result. Rules only prove the upstream string is
 * gone; these prove the replacement is actually in place and complete.
 */
const POSTCONDITIONS = [
  { id: "P1-fonts-local", file: MAIN_CSS, needle: "url(../fonts/web/", count: FONTS.length },
  // Anchored on the minified binding so the two neutered SDKs are asserted
  // separately. If upstream renames them these fail — which is the point: a
  // refreshed mirror should stop and ask for a human, not pass silently.
  { id: "P2-telemetry-inert", file: MAIN_CHUNK, needle: `Jo=\`${INERT_SCRIPT}\``, count: 1 },
  { id: "P3-apm-inert", file: MAIN_CHUNK, needle: `ssUrl:\`${INERT_SCRIPT}\``, count: 1 },
  // Not ours — upstream's own `import.meta.resolve` probe. It is the reason the
  // CSP must allow `data:` in script-src; assert it so the coupling is visible
  // if upstream ever drops it.
  { id: "P4-resolve-probe", file: MAIN_CHUNK, needle: `import'${INERT_SCRIPT}`, count: 1 },
];

function bundlePath(file) {
  return join(BUNDLE_DIR, file);
}

function countOccurrences(haystack, needle) {
  return haystack.split(needle).length - 1;
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
  for (const host of FORBIDDEN_HOSTS) {
    if (policy.includes(host)) failures.push(`CSP was widened to allow ${host}`);
  }
}

/** No patched-out host may reappear in any file a rule touches. */
function checkForbiddenHosts(failures) {
  const files = new Set(RULES.map((rule) => rule.file));
  for (const file of files) {
    const content = readFileSync(bundlePath(file), "utf-8");
    for (const host of FORBIDDEN_HOSTS) {
      const hits = countOccurrences(content, host);
      if (hits) failures.push(`${file}: ${hits}x ${host} (should be 0)`);
    }
  }
}

/** Every localized font must exist on disk and actually be a woff2. */
function checkFontFiles(failures) {
  for (const [, slug] of FONTS) {
    const path = join(FONT_DIR, `${slug}.woff2`);
    if (!existsSync(path)) {
      failures.push(`missing font file fonts/web/${slug}.woff2 (run --apply to fetch it)`);
      continue;
    }
    const magic = readFileSync(path).subarray(0, 4).toString("latin1");
    if (magic !== "wOF2") failures.push(`fonts/web/${slug}.woff2 is not a woff2 (magic ${JSON.stringify(magic)})`);
  }
}

/** Fetch a font we do not have yet; only reached on a fresh mirror. */
async function downloadFont(url, slug) {
  const response = await fetch(`https:${url}`);
  if (!response.ok) throw new Error(`${slug}: HTTP ${response.status}`);
  const buffer = Buffer.from(await response.arrayBuffer());
  const magic = buffer.subarray(0, 4).toString("latin1");
  if (magic !== "wOF2") throw new Error(`${slug}: not a woff2 (magic ${JSON.stringify(magic)})`);
  mkdirSync(FONT_DIR, { recursive: true });
  writeFileSync(join(FONT_DIR, `${slug}.woff2`), buffer);
  return buffer.length;
}

function check() {
  const failures = [];
  let applied = 0;
  for (const rule of RULES) {
    const content = readFileSync(bundlePath(rule.file), "utf-8");
    const remaining = countOccurrences(content, rule.from);
    if (remaining === 0) applied += 1;
    else failures.push(`${rule.id} not applied: ${rule.file} still has ${remaining}x upstream value (${rule.note})`);
  }
  for (const post of POSTCONDITIONS) {
    const content = readFileSync(bundlePath(post.file), "utf-8");
    const hits = countOccurrences(content, post.needle);
    if (hits !== post.count) failures.push(`${post.id}: expected ${post.count}x "${post.needle}", found ${hits}`);
  }
  checkForbiddenHosts(failures);
  checkContentSecurityPolicy(failures);
  checkFontFiles(failures);

  if (failures.length) {
    console.error(`FAIL  mirror patches (${applied}/${RULES.length} rules applied)`);
    for (const line of failures) console.error(`  - ${line}`);
    console.error("\nRun `node tools/pptd/patch-mirror.mjs --apply` to reapply.");
    process.exitCode = 1;
    return;
  }
  console.log(`OK  mirror is patched (${RULES.length} rules, ${POSTCONDITIONS.length} postconditions, ${FONTS.length} fonts)`);
}

async function apply() {
  const edits = new Map();
  const skipped = [];
  const failures = [];

  for (const rule of RULES) {
    const path = bundlePath(rule.file);
    const content = edits.get(path) ?? readFileSync(path, "utf-8");
    const hits = countOccurrences(content, rule.from);
    if (hits === 0) {
      skipped.push(rule.id); // already applied — this script is idempotent
      continue;
    }
    if (hits !== rule.expect) {
      failures.push(`${rule.id}: expected ${rule.expect} match(es) in ${rule.file}, found ${hits} — upstream moved, review by hand`);
      continue;
    }
    edits.set(path, content.split(rule.from).join(rule.to));
  }

  // A rule whose hit count drifted means the mirror is not what we think it is;
  // writing the other rules anyway would leave a half-patched bundle behind.
  if (failures.length) {
    console.error("FAIL  refusing to write a partially patched mirror");
    for (const line of failures) console.error(`  - ${line}`);
    process.exitCode = 1;
    return;
  }

  for (const [path, content] of edits) writeFileSync(path, content);
  console.log(`applied ${RULES.length - skipped.length} rule(s), ${skipped.length} already in place`);

  const missing = FONTS.filter(([, slug]) => !existsSync(join(FONT_DIR, `${slug}.woff2`)));
  if (missing.length) {
    console.log(`fetching ${missing.length} missing font(s)…`);
    for (const [url, slug] of missing) {
      const size = await downloadFont(url, slug);
      console.log(`  ok  ${slug}.woff2 (${(size / 1024).toFixed(0)} KB)`);
    }
  }

  check();
}

const mode = process.argv[2];
if (mode === "--apply") await apply();
else if (mode === "--check" || mode === undefined) check();
else {
  console.error(`unknown argument: ${mode}\nUsage: patch-mirror.mjs [--check|--apply]`);
  process.exitCode = 2;
}
