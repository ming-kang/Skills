#!/usr/bin/env node
// Vendor the third-party JavaScript the skill runs. The installed skill never sees
// node_modules: every runtime dependency is one self-contained file in assets/vendor/.
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { build, version as esbuildVersion } from 'esbuild';

const require = createRequire(import.meta.url);
const repository = path.resolve(import.meta.dirname, '..', '..');
const output = path.join(repository, 'pptd/assets/vendor');

function packageRoot(name) {
  let current = path.dirname(require.resolve(name));
  while (!fs.existsSync(path.join(current, 'package.json')) ||
         JSON.parse(fs.readFileSync(path.join(current, 'package.json'), 'utf8')).name !== name) {
    if (current === path.dirname(current)) throw new Error(`Cannot locate package root: ${name}`);
    current = path.dirname(current);
  }
  return current;
}
const entry = (name, file) => JSON.stringify(path.join(packageRoot(name), file));

// One licenses/<bundle>/ directory per vendored file; stale notices are removed.
function noticeWriter(bundle) {
  const directory = path.join(output, 'licenses', bundle);
  fs.rmSync(directory, { recursive: true, force: true });
  fs.mkdirSync(directory, { recursive: true });
  return (name, bytes) => fs.writeFileSync(path.join(directory, name), bytes);
}

// ---- Only the four non-native charts, their SVG renderer, axes, title and colorbar. ----
async function vendorEcharts() {
  const write = noticeWriter('echarts');
  const result = await bundle('echarts.mjs', `
    import { use } from 'echarts/core';
    import { HeatmapChart, TreemapChart, SunburstChart, SankeyChart } from 'echarts/charts';
    import { GridComponent, TitleComponent, VisualMapContinuousComponent } from 'echarts/components';
    import { SVGRenderer } from 'echarts/renderers';
    use([HeatmapChart, TreemapChart, SunburstChart, SankeyChart, GridComponent, TitleComponent, VisualMapContinuousComponent, SVGRenderer]);
    export { init, color } from 'echarts/core';
  `);
  fs.writeFileSync(path.join(output, result.file), result.contents);
  for (const [pkg, source, name] of [
    ['echarts', 'LICENSE', 'LICENSE'],
    ['echarts', 'NOTICE', 'NOTICE'],
    ['echarts', 'licenses/LICENSE-d3', 'LICENSE-d3'],
    ['zrender', 'LICENSE', 'LICENSE-zrender'],
    ['tslib', 'LICENSE.txt', 'LICENSE-tslib'],
    ['tslib', 'CopyrightNotice.txt', 'CopyrightNotice-tslib.txt'],
  ]) write(name, fs.readFileSync(path.join(packageRoot(pkg), source), 'utf8').replaceAll('\r\n', '\n'));
  return result;
}

// ---- esbuild bundles: Node 26+ ESM with no external imports. ----
async function bundle(file, source, options = {}) {
  const result = await build({
    stdin: { contents: source, resolveDir: repository, sourcefile: `${file}-entry.mjs` },
    absWorkingDir: repository,
    bundle: true, minify: true, metafile: true, write: false,
    legalComments: 'inline', platform: 'node', format: 'esm', target: 'node26',
    define: { 'process.env.NODE_ENV': '"production"' },
    ...options,
  });
  for (const generated of Object.values(result.metafile.outputs)) {
    if (generated.imports.length) throw new Error(`${file} must have no external imports`);
  }
  const inputs = Object.keys(result.metafile.inputs).filter((input) => input.includes('node_modules')).sort();
  // Nested {"type": "module"} marker files are not package roots.
  const manifest = (directory) => {
    const file = path.join(directory, 'package.json');
    const data = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : {};
    return data.name && data.version ? data : undefined;
  };
  const roots = new Set();
  for (const input of inputs) {
    let current = path.dirname(path.resolve(repository, input));
    while (!manifest(current)) current = path.dirname(current);
    roots.add(current);
  }
  const packages = [...roots].sort().map((root) => ({ root, ...manifest(root) }));
  return { file, contents: result.outputFiles[0].contents, inputs, packages };
}

// Copy every LICENSE/COPYING/NOTICE shipped by the bundled packages.
function copyPackageNotices({ packages }, write) {
  const copied = new Map();
  for (const pkg of packages) {
    const id = pkg.name.replace(/^@/, '').replace(/[^\w.-]+/g, '-');
    const names = fs.readdirSync(pkg.root)
      .filter((name) => /^(license|copying|notice)/i.test(name) && fs.statSync(path.join(pkg.root, name)).isFile()).sort();
    copied.set(pkg, names.map((name) => {
      write(`${id}-${name}`, fs.readFileSync(path.join(pkg.root, name), 'utf8').replaceAll('\r\n', '\n'));
      return `${id}-${name}`;
    }));
  }
  return copied;
}

async function vendorBundle(file, source) {
  const result = await bundle(file, source);
  const name = path.basename(file, '.mjs');
  const copied = copyPackageNotices(result, noticeWriter(name));
  for (const [pkg, files] of copied) {
    if (!files.length) throw new Error(`${pkg.name} ships no license file; add a verified source before vendoring it`);
  }
  fs.writeFileSync(path.join(output, file), result.contents);
  return result;
}

// ---- fontkit: several bundled packages omit their license; restore verified originals. ----
// Some npm releases omit LICENSE. Verified original files stay in the distributed assets so
// a normal rebuild is offline; fetch only to restore a missing notice, and never guess a
// copyright holder/year or synthesize license text.
const FONTKIT_UPSTREAM = [
  ['LICENSE-fontkit', 'https://raw.githubusercontent.com/foliojs/fontkit/811d374105e6e818fc411cd7604f81661f582b1b/LICENSE',
    'cf22b8198f0886a8d4626121579114f23141070e1fceab02ab3c1c361e163440'],
  ['LICENSE-base64-arraybuffer', 'https://raw.githubusercontent.com/niklasvh/base64-arraybuffer/5339d8f0abed59c893e87116a785bf52acdc17aa/LICENSE',
    'f3eca6ff762533fa5a77caf954a143e48afa204668cf97dce758c45a9e006be3'],
  ['LICENSE-Unicode', 'https://www.unicode.org/license.txt',
    'e7a93b009565cfce55919a381437ac4db883e9da2126fa28b91d12732bc53d96'],
];
// These releases have no LICENSE even at their release commits. Their package.json and
// README declare MIT; reproduce those declarations instead of fabricating an MIT grant.
const FONTKIT_DECLARED = new Map([
  ['dfa@1.2.0', { readme: 'README.md', repo: 'devongovett/dfa', commit: '3f5e603e5082caedabefefdf53e8a6ca3111e966' }],
]);

async function vendorFontkit() {
  if (require(path.join(packageRoot('fontkit'), 'package.json')).version !== '2.0.4') {
    throw new Error('Review the fontkit bundle/licensing before changing the pinned 2.0.4 parser');
  }
  // The runtime accepts SFNT/TTC/EOT, never WOFF/WOFF2/DFont. Register just those
  // containers, keeping the complete glyph/layout engine instead of forking it.
  const result = await bundle('fontkit.mjs', `
    import { registerFormat, create } from ${entry('fontkit', 'src/base.js')};
    import TTFFont from ${entry('fontkit', 'src/TTFFont.js')};
    import TrueTypeCollection from ${entry('fontkit', 'src/TrueTypeCollection.js')};
    registerFormat(TTFFont);
    registerFormat(TrueTypeCollection);
    export { create };
  `, {
    tsconfigRaw: { compilerOptions: { experimentalDecorators: true } },
    plugins: [{
      name: 'fontkit-source-assets',
      setup(build) {
        build.onLoad({ filter: /[\\/]node_modules[\\/]fontkit[\\/]src[\\/].*\.js$/ }, ({ path: file }) => ({
          // Parcel inlined these three Unicode tries in the published browser build.
          contents: fs.readFileSync(file, 'utf8').replace(
            /require\(['"]fs['"]\)\.readFileSync\(__dirname\s*\+\s*(['"][^'"]+['"]),\s*['"]base64['"]\)/g,
            (_, relative) => JSON.stringify(fs.readFileSync(path.join(path.dirname(file), relative.slice(1, -1)), 'base64')),
          ),
          // fontkit's @cache uses legacy three-argument decorators, not TC39 Stage 3.
          loader: 'ts',
        }));
      },
    }],
  });
  const directory = path.join(output, 'licenses/fontkit');
  const kept = new Map(FONTKIT_UPSTREAM.map(([name]) => [name, path.join(directory, name)])
    .filter(([, file]) => fs.existsSync(file)).map(([name, file]) => [name, fs.readFileSync(file)]));
  const write = noticeWriter('fontkit');

  const supplemental = [];
  for (const [name, url, sha256] of FONTKIT_UPSTREAM) {
    let bytes = kept.get(name);
    if (!bytes) {
      const response = await fetch(url, { signal: AbortSignal.timeout(30000) });
      if (!response.ok) throw new Error(`Cannot fetch authoritative license: ${response.status} ${url}`);
      bytes = Buffer.from(await response.arrayBuffer());
    }
    if (createHash('sha256').update(bytes).digest('hex') !== sha256) throw new Error(`Upstream license hash changed: ${url}`);
    write(name, bytes);
    supplemental.push(`${name}: ${url}\nSHA-256: ${sha256}`);
  }

  const packageNotices = [];
  for (const [pkg, files] of copyPackageNotices(result, write)) {
    if (!files.length && pkg.name === 'fontkit') files.push('LICENSE-fontkit');
    if (!files.length) {
      const record = FONTKIT_DECLARED.get(`${pkg.name}@${pkg.version}`);
      if (!record || pkg.license !== 'MIT') throw new Error(`No verified license source for bundled ${pkg.name}@${pkg.version}`);
      // Windows's filesystem is case-insensitive; use the spelling actually shipped.
      const readme = fs.readdirSync(pkg.root).find((name) => name.toLowerCase() === record.readme.toLowerCase());
      if (!readme) throw new Error(`Missing upstream licensing README for ${pkg.name}`);
      const section = /^## License\s*\r?\n[\s\S]*?(?=^## |$(?![\s\S]))/m.exec(fs.readFileSync(path.join(pkg.root, readme), 'utf8'))?.[0];
      if (!section || section.replace(/^## License\s*/, '').trim() !== 'MIT') throw new Error(`Unexpected README license declaration for ${pkg.name}`);
      const declared = { name: pkg.name, version: pkg.version, author: pkg.author, license: pkg.license, repository: pkg.repository };
      write(`NOTICE-${pkg.name}`, `${pkg.name} ${pkg.version}\nSource: https://github.com/${record.repo}/tree/${record.commit}\n\nOriginal package.json licensing/author/repository fields:\n${JSON.stringify(declared, null, 2)}\n\nOriginal ${readme} license section:\n${section}\n`);
      files.push(`NOTICE-${pkg.name}`);
    }
    const repo = typeof pkg.repository === 'string' ? pkg.repository : pkg.repository?.url ?? pkg.homepage ?? '';
    packageNotices.push(`${pkg.name} ${pkg.version} (${pkg.license})\n${repo}\nNotices: ${files.join(', ')}`);
  }

  // Preserve original source attributions in addition to the full package licenses.
  const sourceHeaders = [];
  for (const input of result.inputs) {
    const headers = [...fs.readFileSync(path.resolve(repository, input), 'utf8').matchAll(/\/\*[\s\S]*?\*\/|^\s*\/\/[^\r\n]*/gm)]
      .map((match) => match[0].trim()).filter((text) => /copyright|\blicen[cs]e\b|permission is hereby/i.test(text));
    if (headers.length) sourceHeaders.push(`${input.replaceAll('\\', '/')}\n${headers.join('\n\n')}`);
  }
  write('NOTICE-source-headers', sourceHeaders.join('\n\n--------------------\n\n') + '\n');
  write('NOTICE', `Browser-free SVG glyph outline parser/shaper

fontkit 2.0.4 SFNT and TrueTypeCollection source entries, bundled with esbuild ${esbuildVersion} for Node 26+.
The complete glyph parser, shaper and Unicode tries are included. Legacy @cache
decorators are compiled and Parcel's static trie reads are inlined at build time.
WOFF/WOFF2/DFont, Brotli and SWC helpers are not included. There are no external
imports, browser engine, adjacent node_modules or additional WASM.

BUNDLED NPM INPUTS

${packageNotices.join('\n\n')}

ADDITIONAL UPSTREAM LICENSE SOURCES

${supplemental.join('\n\n')}

fontkit's omitted MIT license is copied from the pinned upstream source above.
NOTICE-dfa reproduces its shipped metadata/README MIT declaration, without an
invented copyright grant. NOTICE-source-headers retains the original legal
headers; the base64-arraybuffer attribution and authoritative Unicode license
accompany the derived decoder and Unicode-generated data.

Selected fonts are supplied separately by the caller and retain their own licenses.
`);
  // Write the runtime bundle only after licensing and the no-external-import check succeed.
  fs.writeFileSync(path.join(output, 'fontkit.mjs'), result.contents);
  return result;
}

fs.mkdirSync(output, { recursive: true });
const bundles = [
  await vendorEcharts(),
  await vendorBundle('katex.mjs', "export { default as katex } from 'katex';"),
  // The parser's own HTML entity table lets rich text keep an unknown `&name;` literal.
  await vendorBundle('xmldom.mjs', `
    export { DOMImplementation, DOMParser, XMLSerializer } from '@xmldom/xmldom';
    export { HTML_ENTITIES } from ${entry('@xmldom/xmldom', 'lib/entities.js')};
  `),
  // The browser build is plain ESM without Node built-ins.
  await vendorBundle('yaml.mjs', `export { parseDocument, visit } from ${entry('yaml', 'browser/index.js')};`),
  await vendorFontkit(),
];
for (const { file, contents, packages } of bundles) {
  console.log(`Vendored ${file}: ${contents.length} bytes from ${packages.map((pkg) => `${pkg.name}@${pkg.version}`).join(', ')}`);
}
