import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import test from 'node:test';
import { pathToFileURL } from 'node:url';

import {
  checkNodeVersion,
  exportPptx,
} from '../../../pptd/scripts/export.mjs';
import { normalizeElement } from '../../../pptd/scripts/lib/deck/contract.mjs';
import { readContent } from '../../../pptd/scripts/lib/deck/content.mjs';
import { buildWasmProject, readProject } from '../../../pptd/scripts/lib/deck/project.mjs';
import { readZip } from '../../../pptd/scripts/lib/pptx/zip.mjs';
import { loadWasmExporter } from '../../../pptd/scripts/lib/pptx/writer.mjs';
import { resolveImages } from '../../../pptd/scripts/lib/prepare/assets.mjs';
import { prepareFonts } from '../../../pptd/scripts/lib/prepare/fonts.mjs';
import { latexToOmml } from '../../../pptd/scripts/lib/prepare/formulas.mjs';

const REPO_ROOT = path.resolve(import.meta.dirname, '..', '..', '..');
const SKILL_ROOT = path.join(REPO_ROOT, 'pptd');
const WASM = path.join(SKILL_ROOT, 'assets', 'wasm', 'pptd_wasm_bg.wasm');
const MINIMAL = path.join(REPO_ROOT, 'tools', 'pptd', 'tests', 'fixtures', 'minimal');

test('custom shapes accept bare and viewBox-prefixed paths', () => {
  const bare = normalizeElement({
    elementType: 'shape',
    shapeName: 'custom',
    bounds: [0, 0, 120, 80],
    path: 'M0 0L120 80',
  });
  assert.deepEqual(bare.viewBox, [120, 80]);
  const prefixed = normalizeElement({
    elementType: 'shape',
    shapeName: 'custom',
    bounds: [0, 0, 120, 80],
    path: '200,100;M0 0L200 100',
  });
  assert.deepEqual(prefixed.viewBox, [200, 100]);
  assert.equal(prefixed.path, 'M0 0L200 100');
});

test('project becomes the page-object shape expected by WASM', () => {
  const project = buildWasmProject({
    manifestPath: path.resolve('fixture', 'deck.pptd'),
    version: 'v2', title: 'Fixture', warnings: [], media: [],
    pages: [{ pagePath: 'pages/01.page', elements: [] }],
  });
  assert.equal(project.version, 'v2');
  assert.equal(project.title, 'Fixture');
  for (const key of ['manifest', 'manifestPath', 'warnings', 'media']) assert.equal(key in project, false);
  assert.equal(project.pptdFileName, 'deck.pptd');
  assert.equal(project.pages[0].pagePath, 'pages/01.page');
  assert.deepEqual(project.pages[0].elements, []);
});

test('local media resolves to bytes and all matching sources are remapped', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-media-'));
  try {
    fs.mkdirSync(path.join(root, 'media'));
    const bytes = fs.readFileSync(new URL('../tests/fixtures/qa-deck/media/pixel.png', import.meta.url));
    fs.writeFileSync(path.join(root, 'media', 'pixel.png'), bytes);
    const project = {
      pages: [
        {
          background: { type: 'image', src: 'media/pixel.png' },
          elements: [
            { elementType: 'image', src: 'media/pixel.png' },
            { elementType: 'shape', fill: { type: 'image', src: 'media/pixel.png' } },
          ],
        },
      ],
    };
    const images = await resolveImages(project, root);
    assert.deepEqual(Buffer.from(images['wasm-assets/img-0.png']), bytes);
    assert.equal(project.pages[0].background.src, 'wasm-assets/img-0.png');
    assert.equal(project.pages[0].elements[0].src, 'wasm-assets/img-0.png');
    assert.equal(project.pages[0].elements[1].fill.src, 'wasm-assets/img-0.png');
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('media paths cannot escape the project', async () => {
  const project = {
    pages: [{ elements: [{ elementType: 'image', src: '../outside.png' }] }],
  };
  await assert.rejects(resolveImages(project, os.tmpdir()), /escapes the PPTD directory/);
});

test('bad image bytes are rejected and actual SVG bytes override a misleading URL suffix', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-media-identity-'));
  const originalFetch = globalThis.fetch;
  try {
    fs.writeFileSync(path.join(root, 'fake.png'), '<html>not an image</html>');
    await assert.rejects(resolveImages({ pages: [{ elements: [{ elementType: 'image', src: 'fake.png' }] }] }, root), /not a supported/);
    const svg = Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>');
    globalThis.fetch = async () => new Response(svg);
    const project = { pages: [{ elements: [{ elementType: 'image', src: 'https://example.invalid/picture.png' }] }] };
    const images = await resolveImages(project, root);
    assert.equal(project.pages[0].elements[0].src, 'wasm-assets/img-0.svg');
    assert.deepEqual(Buffer.from(images['wasm-assets/img-0.svg']), svg);
  } finally {
    globalThis.fetch = originalFetch;
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('math spacing and display style are preserved, while ruled arrays fail explicitly', () => {
  const slash = String.fromCharCode(92);
  assert.notEqual(latexToOmml('a' + slash + 'quad b'), latexToOmml('a' + slash + 'qquad b'));
  assert.notEqual(latexToOmml(slash + 'tfrac{x}{y}'), latexToOmml(slash + 'dfrac{x}{y}'));
  assert.match(latexToOmml('x+1', { bold: true, opacity: 0.5 }), /b="1"/);
  assert.match(latexToOmml('x+1', { bold: true, opacity: 0.5 }), /a:alpha val="50000"/);
  assert.equal(latexToOmml('x+1', { opacity: null }), latexToOmml('x+1'));
  assert.throws(() => latexToOmml(slash + 'begin{array}{c|c}1&2' + slash.repeat(2) + '3&4' + slash + 'end{array}'), /ruled formula arrays/);
});

test('the bundled writer is unique and matches the version-locked adapter', async () => {
  const found = [];
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name.endsWith('.wasm')) found.push(full);
    }
  };
  walk(SKILL_ROOT);
  assert.deepEqual(found, [WASM]);

  const exporter = await loadWasmExporter(WASM);
  assert.equal(typeof exporter.exportPPTDToPPTXBytes, 'function');
});

test('old Node versions are rejected and existing output is preserved without force', async () => {
  assert.throws(() => checkNodeVersion('v24.11.0'), /Node\.js 26\+/);
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-no-overwrite-'));
  try {
    const output = path.join(dir, 'deck.pptx');
    fs.writeFileSync(output, 'keep');
    await assert.rejects(exportPptx(MINIMAL, { output, quiet: true }), /already exists/);
    assert.equal(fs.readFileSync(output, 'utf8'), 'keep');
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('vendored bundles resolve without node_modules', () => {
  const vendorDir = path.join(SKILL_ROOT, 'assets', 'vendor');
  for (const name of fs.readdirSync(vendorDir).sort()) {
    if (!name.endsWith('.mjs')) continue;
    const text = fs.readFileSync(path.join(vendorDir, name), 'utf8');
    assert.doesNotMatch(text, /node_modules/, `${name} references node_modules`);
  }
  const vendorUrl = pathToFileURL(vendorDir).href;
  const probe = [
    `import { create } from '${vendorUrl}/fontkit.mjs';`,
    `import { katex } from '${vendorUrl}/katex.mjs';`,
    `import { DOMParser } from '${vendorUrl}/xmldom.mjs';`,
    `import { parseDocument } from '${vendorUrl}/yaml.mjs';`,
    'console.log(typeof create, typeof katex.renderToString, typeof DOMParser, typeof parseDocument);',
  ].join('\n');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-vendor-probe-'));
  try {
    const probePath = path.join(dir, 'probe.mjs');
    fs.writeFileSync(probePath, probe, 'utf8');
    const stdout = execFileSync(process.execPath, [probePath], { encoding: 'utf8' });
    assert.match(stdout, /^function function function function/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('English decks omitting fontFamily fall back to Liter instead of 11MB Noto Sans SC', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-english-fallback-'));
  try {
    fs.mkdirSync(path.join(dir, 'pages'));
    fs.writeFileSync(path.join(dir, 'deck.pptd'), 'version: v2\nsize: [960, 540]\npages: [pages/01.page]\n');
    fs.writeFileSync(path.join(dir, 'pages/01.page'), JSON.stringify({
      elements: [
        { elementId: 'en', elementType: 'text', bounds: [40, 40, 400, 60], content: { text: '<p><!-- 中文注释 -->Hello World</p>' } },
      ],
    }));
    const output = path.join(dir, 'en.pptx');
    const summary = await exportPptx(dir, { output, offline: true, quiet: true });
    assert.deepEqual(summary.fontFamilies, ['Liter']);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('resolveImages deduplicates identical payloads and formulas support cases/asymmetric fences/mpadded', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-dedup-'));
  try {
    fs.mkdirSync(path.join(dir, 'media'));
    const bytes = fs.readFileSync(new URL('../tests/fixtures/qa-deck/media/pixel.png', import.meta.url));
    fs.writeFileSync(path.join(dir, 'media', 'a.png'), bytes);
    fs.writeFileSync(path.join(dir, 'media', 'b.png'), bytes);
    const project = {
      pages: [{
        elements: [
          { elementType: 'image', src: 'media/a.png' },
          { elementType: 'image', src: 'media/b.png' },
        ],
      }],
    };
    const images = await resolveImages(project, dir);
    assert.equal(Object.keys(images).length, 1);
    assert.equal(project.pages[0].elements[0].src, project.pages[0].elements[1].src);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }

  const slash = String.fromCharCode(92);
  const casesOmml = latexToOmml(slash + 'begin{cases}1&x>0' + slash.repeat(2) + '0&x' + slash + 'le 0' + slash + 'end{cases}');
  assert.match(casesOmml, /<m:d>/);
  assert.match(casesOmml, /m:begChr m:val="{"/);
  assert.match(latexToOmml(slash + 'left. ' + slash + 'frac{df}{dx} ' + slash + 'right|'), /<m:d>/);
  assert.match(latexToOmml(slash + 'left[ 0, 1 ' + slash + 'right)'), /<m:d>/);
  assert.match(latexToOmml(slash + 'xrightarrow{f}'), /<m:limUpp>/);
});

test('every compressed bundled font keeps its family/style metadata', async () => {
  const { readFontBytes, readFontFaces, readFontFacesFromFile } = await import('../../../pptd/scripts/lib/prepare/font_data.mjs');
  const catalog = JSON.parse(fs.readFileSync(path.join(SKILL_ROOT, 'assets/fonts/catalog.json'), 'utf8'));
  for (const entry of catalog.faces) {
    assert.ok(entry.src.endsWith('.ttf.gz'), entry.src);
    const file = path.join(SKILL_ROOT, 'assets/fonts', entry.src);
    const bytes = readFontBytes(file);
    const faces = readFontFaces(bytes);
    assert.deepEqual(readFontFacesFromFile(file), faces);
    assert.equal(faces[0].family, entry.family);
    assert.equal(faces[0].slot, entry.slot);
  }
});

test('manifest metadata and Cell.textStyle reach the writer instead of being dropped', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-metadata-'));
  try {
    fs.mkdirSync(path.join(dir, 'pages'));
    fs.writeFileSync(path.join(dir, 'deck.pptd'), [
      'version: v2',
      'title: Annual Review',
      'metadata: {author: "Strategy Team", company: Acme, subject: Q3, copyright: "© 2026"}',
      'size: [960, 540]',
      'theme:',
      '  textStyles:',
      '    body: {fontSize: 22, color: "#FF0000"}',
      'pages: [pages/01.page]',
      '',
    ].join('\n'));
    fs.writeFileSync(path.join(dir, 'pages/01.page'), [
      'elements:',
      '  - elementId: tb',
      '    elementType: table',
      '    bounds: [40, 40, 400, 200]',
      '    columnWidths: [1]',
      '    rowHeights: [1]',
      '    rows:',
      '      - - {text: A, textStyle: "$body"}',
      '',
    ].join('\n'));
    const output = path.join(dir, 'meta.pptx');
    await exportPptx(dir, { output, offline: true, quiet: true });
    const core = readZip(fs.readFileSync(output)).read('docProps/core.xml').toString('utf8');
    assert.match(core, /<dc:title>Annual Review<\/dc:title>/);
    assert.match(core, /<dc:creator>Strategy Team<\/dc:creator>/);
    assert.match(core, /<dc:subject>Q3<\/dc:subject>/);
    const slide = readZip(fs.readFileSync(output)).read('ppt/slides/slide1.xml').toString('utf8');
    // Cell.textStyle is ignored by the writer, so the content pass must materialize it.
    assert.match(slide, /sz="2200"/);
    assert.match(slide, /<a:srgbClr val="FF0000"\/>/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('unsupported manifest metadata keys and non-string values are rejected', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-metadata-bad-'));
  try {
    fs.mkdirSync(path.join(dir, 'pages'));
    fs.writeFileSync(path.join(dir, 'pages/01.page'), 'elements: []\n');
    for (const [line, pattern] of [
      ['metadata: {keywords: seo}', /manifest.metadata.keywords is not a supported document property/],
      ['metadata: {title: 2026}', /manifest.metadata.title must be a non-empty string/],
      ['metadata: nope', /manifest.metadata must be a mapping/],
    ]) {
      fs.writeFileSync(path.join(dir, 'deck.pptd'), `version: v2\ntitle: T\n${line}\nsize: [960, 540]\npages: [pages/01.page]\n`);
      assert.throws(() => readProject(dir), pattern, line);
    }
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('rich-text emphasis selects the same font slot the writer marks bold or italic', async () => {
  // The writer treats >= 600 and `bolder` as bold and `oblique` as italic; the font
  // pass must agree, or a bold run would carry a regular embedded face.
  const slots = async (style) => {
    const project = { pages: [{ pagePath: 'pages/01.page', elements: [{
      elementId: 'text', elementType: 'text', bounds: [0, 0, 800, 80],
      content: { text: `<p><span style="${style}">AV</span></p>`, fontFamily: 'Quattrocento Sans' },
    }] }] };
    const fonts = await prepareFonts(project, readContent(project), { projectRoot: os.tmpdir(), offline: true, embed: true });
    assert.deepEqual(fonts.warnings, []);
    return fonts.bindings.map((face) => face.slot).sort();
  };
  assert.deepEqual(await slots('font-weight:600'), ['bold', 'regular']);
  assert.deepEqual(await slots('font-weight:500'), ['regular']);
  assert.deepEqual(await slots('font-weight:bolder'), ['bold', 'regular']);
  assert.deepEqual(await slots('font-style:oblique'), ['italic', 'regular']);
  assert.deepEqual(await slots('font-style:normal'), ['regular']);
});
