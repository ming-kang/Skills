import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

import { DOMParser } from '../../../pptd/assets/vendor/xmldom.mjs';
import { exportPptx } from '../../../pptd/scripts/export.mjs';
import { readFontFaces } from '../../../pptd/scripts/lib/prepare/font_data.mjs';
import { PptxPackage } from '../../../pptd/scripts/lib/pptx/package.mjs';
import { patchTransitions } from '../../../pptd/scripts/lib/pptx/patch.mjs';
import {
  PPTX_CONTENT_TYPE,
  slideTransitionFacts,
  validateTransitionOrder,
  verifyOutput,
} from '../../../pptd/scripts/lib/pptx/verify.mjs';
import { crc32, readZip, writeZip } from '../../../pptd/scripts/lib/pptx/zip.mjs';
import { makeDeck, replaceTransition, updateZip } from './helpers.mjs';

const REPO_ROOT = path.resolve(import.meta.dirname, '..', '..', '..');
const EXPORT_CLI = path.join(REPO_ROOT, 'pptd', 'scripts', 'export.mjs');
const FIXTURES = path.join(REPO_ROOT, 'tools', 'pptd', 'tests', 'fixtures');
const MINIMAL = path.join(FIXTURES, 'minimal');
const QA_DECK = path.join(FIXTURES, 'qa-deck');
const ADVANCED_CHARTS = path.join(FIXTURES, 'advanced-charts');

const P_NS = 'http://schemas.openxmlformats.org/presentationml/2006/main';
const A_NS = 'http://schemas.openxmlformats.org/drawingml/2006/main';
const M_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math';

function parseXml(buffer) {
  return new DOMParser().parseFromString(Buffer.from(buffer).toString('utf8'), 'application/xml');
}

test('zip roundtrip computes IEEE CRC-32 and detects tampered bytes', () => {
  const payload = Buffer.from('Hello PPTD ZIP!');
  assert.equal(crc32(Buffer.from('123456789')), 0xcbf43926);
  const zip = writeZip([
    { name: 'a.txt', data: payload },
    { name: 'b.txt', data: Buffer.from('unchanged'), method: 0 },
  ]);
  const archive = readZip(zip);
  archive.verifyAll();
  assert.deepEqual(archive.read('a.txt'), payload);
  assert.equal(archive.read('b.txt').toString(), 'unchanged');

  const updated = updateZip(zip, { 'c.txt': Buffer.from('added') });
  const archive2 = readZip(updated);
  archive2.verifyAll();
  assert.equal(archive2.read('c.txt').toString(), 'added');
});

test('fade transition is inserted before timing and replaces or clears existing transitions', () => {
  const source = Buffer.from(
    '<p:sld xmlns:p="urn:test"><p:cSld><p:spTree><p:extLst/>' +
      '</p:spTree></p:cSld><p:clrMapOvr/><p:timing/><p:extLst/></p:sld>',
  );
  const result = replaceTransition(source, 'fade');
  const text = result.toString('utf8');
  assert.ok(text.indexOf('<p:transition') > text.indexOf('<p:clrMapOvr'));
  assert.ok(text.indexOf('<p:transition') < text.indexOf('<p:timing'));
  validateTransitionOrder(slideTransitionFacts(parseXml(result)), 'fade');

  const existing = Buffer.from(
    '<p:sld xmlns:p="urn:test"><p:cSld/><p:transition><p:wipe/></p:transition><p:extLst/></p:sld>',
  );
  const faded = replaceTransition(existing, 'fade').toString('utf8');
  assert.ok(!faded.includes('p:wipe'));
  assert.equal(faded.match(/<p:transition\b/g)?.length, 1);
  const cleared = replaceTransition(existing, 'none').toString('utf8');
  assert.ok(!cleared.includes('p:transition'));
});

test('nested transition is relocated to slide root and patchTransitions preserves zip integrity', () => {
  const nested = Buffer.from(
    '<p:sld xmlns:p="urn:test"><p:cSld><p:spTree>' +
      '<p:transition><p:fade/></p:transition><p:extLst/>' +
      '</p:spTree></p:cSld><p:clrMapOvr/><p:extLst/></p:sld>',
  );
  const facts = slideTransitionFacts(parseXml(replaceTransition(nested, 'fade')));
  assert.deepEqual(facts.names, ['cSld', 'clrMapOvr', 'transition', 'extLst']);

  const zip = writeZip([
    {
      name: '[Content_Types].xml',
      data:
        `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">` +
        `<Default Extension="xml" ContentType="application/xml"/>` +
        `<Override PartName="/ppt/presentation.xml" ContentType="${PPTX_CONTENT_TYPE}"/></Types>`,
    },
    { name: 'ppt/presentation.xml', data: "<p:presentation xmlns:p='urn:test'/>" },
    { name: 'ppt/slides/slide1.xml', data: '<p:sld xmlns:p="urn:test"><p:cSld/></p:sld>' },
  ]);
  const pkg = PptxPackage.open(zip);
  const slideCount = patchTransitions(pkg, 'fade');
  assert.equal(slideCount, 1);
  const summary = verifyOutput(pkg.toBuffer(), 'fade');
  assert.equal(summary.slides, 1);
  assert.equal(summary.fadeTransitions, 1);
});

test('public CLI exports real WASM PPTX and defaults output path beside manifest', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-cli-export-'));
  try {
    fs.cpSync(MINIMAL, dir, { recursive: true });
    const res = spawnSync(process.execPath, [EXPORT_CLI, dir, '--offline'], { encoding: 'utf8' });
    assert.equal(res.status, 0, res.stderr);
    const summary = JSON.parse(res.stdout);
    const expectedOut = path.join(dir, 'minimal.pptx');
    assert.equal(summary.output, expectedOut);
    assert.equal(summary.exporter, 'wasm');
    assert.equal(summary.slides, summary.fadeTransitions);

    const archive = readZip(fs.readFileSync(expectedOut));
    archive.verifyAll();
    assert.match(archive.read('docProps/app.xml').toString('utf8'), /<Application>PPT Design<\/Application>/);
    assert.match(archive.read('customXml/provenance.xml').toString('utf8'), /urn:pptd:prov:provenance/);
    assert.match(archive.read('customXml/provenance.xml').toString('utf8'), /<producer>PPT Design \(local\)<\/producer>/);
    assert.match(archive.read('ppt/slides/slide1.xml').toString('utf8'), /xmlns:pptd="https:\/\/pptd\.local\/ns\/2026\/pptd\/schema"/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('exports local media and transition none cleanly', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-qa-export-'));
  try {
    const output = path.join(dir, 'qa.pptx');
    const summary = await exportPptx(QA_DECK, { output, transition: 'none', offline: true, quiet: true });
    assert.equal(summary.slides, 3);
    assert.equal(summary.fadeTransitions, 0);
    assert.ok(summary.fontParts > 0);
    const archive = readZip(fs.readFileSync(output));
    assert.ok(archive.names().some((name) => name.startsWith('ppt/media/')));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('advanced charts export as framed SVG pictures with outlined glyph paths', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-charts-export-'));
  try {
    const output = path.join(dir, 'charts.pptx');
    const summary = await exportPptx(ADVANCED_CHARTS, { output, offline: true, quiet: true });
    assert.equal(summary.slides, 5);
    const archive = readZip(fs.readFileSync(output));
    const chartSvgs = archive.names()
      .filter((name) => name.startsWith('ppt/media/') && name.endsWith('.svg'))
      .map((name) => archive.read(name).toString('utf8'))
      .filter((svg) => svg.includes('<metadata'));
    assert.equal(chartSvgs.length, 4);
    for (const image of chartSvgs) {
      assert.doesNotMatch(image, /dominant-baseline/);
      assert.doesNotMatch(image, /<text(?:\s|>)/);
      assert.match(image, /data-pptd-fonts=/);
      assert.match(image, /data-pptd-text=/);
      assert.match(image, /<metadata/);
    }
    for (let i = 1; i <= 4; i++) {
      const slide = archive.read(`ppt/slides/slide${i}.xml`).toString('utf8');
      const shapes = Object.fromEntries(
        [...slide.matchAll(/<p:cNvPr id="(\d+)" name="([^"]+)"/g)].map((m) => [m[1], m[2]]),
      );
      const chartId = `chart-${i}`;
      assert.ok(Object.values(shapes).includes(chartId));
      assert.ok(Object.values(shapes).includes(`${chartId}-frame`));
      const picture = /<p:pic>[\s\S]*?<\/p:pic>/.exec(slide)[0];
      assert.doesNotMatch(picture, /effectLst/);
      assert.ok(!Object.values(shapes).some((value) => value.endsWith('-border')));
      assert.doesNotMatch(slide, /<a:ln w="0">/);
      const timing = slide.slice(slide.indexOf('<p:timing'));
      const animated = new Set([...timing.matchAll(/spTgt spid="(\d+)"/g)].map((m) => m[1]));
      assert.deepEqual(animated, new Set(Object.keys(shapes)));
    }
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('editable icons, formulas, $textStyle, RIBBI fonts, table cell col>0 overrides, and table image fills', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-full-export-'));
  try {
    fs.mkdirSync(path.join(dir, 'media'));
    fs.copyFileSync(path.join(QA_DECK, 'media', 'pixel.png'), path.join(dir, 'media', 'pixel.png'));
    const manifest = {
      version: 'v2',
      size: [960, 540],
      pages: ['pages/01.page'],
      theme: {
        textStyles: {
          heading: { fontFamily: 'Unna', fontSize: 22, bold: true },
        },
        tableStyles: {
          imageHeader: {
            firstRowStyle: {
              fontFamily: 'Unna',
              color: '#008055',
              fill: { type: 'image', src: 'media/pixel.png' },
            },
          },
        },
      },
    };
    const shared = { text: 'Shared alias' };
    const page = {
      elements: [
        { elementId: 'home', elementType: 'icon', bounds: [40, 40, 48, 48], iconName: 'fas:house' },
        {
          elementId: 'math',
          elementType: 'text',
          bounds: [100, 40, 800, 140],
          content: { fontFamily: 'Unna', fontSize: 24, bold: true, text: '<p>Before \\(\\frac{x^2+1}{y_3}\\) <em>after</em></p>' },
        },
        {
          elementId: 'styled-ref',
          elementType: 'text',
          bounds: [100, 170, 300, 40],
          content: { style: '$heading', text: 'Ref heading' },
        },
        {
          elementId: 'table',
          elementType: 'table',
          bounds: [40, 220, 600, 100],
          columnWidths: [0.5, 0.5],
          rowHeights: [1],
          style: '$imageHeader',
          rows: [[
            { text: '\\( \\sqrt{x} \\)' },
            { text: '<p><span style="font-family:MissingCellFont">col1</span></p>' },
          ]],
        },
        {
          elementId: 'matrix',
          elementType: 'text',
          bounds: [680, 220, 240, 180],
          content: {
            fontFamily: 'Unna',
            fontSize: 24,
            text: 'Matrix: \\(\\begin{pmatrix}1&2\\\\3&4\\end{pmatrix}\\)',
          },
        },
        { elementId: 'weight', elementType: 'text', bounds: [40, 350, 400, 60], content: { fontFamily: 'Coda ExtraBold', text: 'ABC' } },
        { elementId: 'cjk-inline', elementType: 'text', bounds: [460, 350, 400, 60], content: { fontFamily: 'Noto Sans SC', text: '<p><span style="font-family:Unna">中文</span></p>' } },
        {
          elementId: 'aliases',
          elementType: 'table',
          bounds: [40, 420, 500, 80],
          columnWidths: [1],
          rowHeights: [0.5, 0.5],
          style: { cellStyle: { fontFamily: 'Liter' }, firstRowStyle: { fontFamily: 'Unna' } },
          rows: [[shared], [shared]],
        },
      ],
    };
    const source = makeDeck(dir, {
      manifest: JSON.stringify(manifest),
      page: JSON.stringify(page),
    });
    const pagePath = path.join(dir, 'pages', '01.page');
    const originalSource = fs.readFileSync(pagePath);
    const output = path.join(dir, 'deck.pptx');

    const summary = await exportPptx(source, { output, offline: true, quiet: true });
    assert.deepEqual([summary.icons, summary.formulas, summary.tableImageFills], [1, 3, 2]);
    assert.ok(summary.fontParts >= 3);
    assert.ok(summary.warnings.some((w) => w.includes('MissingCellFont')));
    assert.deepEqual(fs.readFileSync(pagePath), originalSource);

    const archive = readZip(fs.readFileSync(output));
    const slideDoc = parseXml(archive.read('ppt/slides/slide1.xml'));
    assert.ok(slideDoc.getElementsByTagNameNS(A_NS, 'custGeom').length > 0);
    assert.ok(slideDoc.getElementsByTagNameNS(M_NS, 'f').length > 0);
    assert.ok(slideDoc.getElementsByTagNameNS(M_NS, 'rad').length > 0);
    assert.ok(slideDoc.getElementsByTagNameNS(M_NS, 'm').length > 0);
    assert.ok(slideDoc.getElementsByTagNameNS(A_NS, 'blipFill').length >= 2);
    assert.doesNotMatch(archive.read('ppt/slides/slide1.xml').toString('utf8'), /MissingCellFont/);

    const presDoc = parseXml(archive.read('ppt/presentation.xml'));
    const listing = presDoc.getElementsByTagNameNS(P_NS, 'embeddedFontLst')[0];
    const fonts = new Map();
    for (let node = listing.firstChild; node; node = node.nextSibling) {
      if (node.nodeType !== 1) continue;
      const fontEl = node.getElementsByTagNameNS(P_NS, 'font')[0];
      fonts.set(fontEl.getAttribute('typeface'), node);
    }
    assert.deepEqual(new Set(fonts.keys()), new Set(['Unna', 'Liter', 'Coda ExtraBold', 'Noto Sans SC']));
    assert.ok(fonts.get('Unna').getElementsByTagNameNS(P_NS, 'regular').length === 1);
    assert.ok(fonts.get('Unna').getElementsByTagNameNS(P_NS, 'bold').length === 1);
    assert.ok(fonts.get('Unna').getElementsByTagNameNS(P_NS, 'boldItalic').length === 1);
    assert.ok(fonts.get('Coda ExtraBold').getElementsByTagNameNS(P_NS, 'regular').length === 1);

    const shapes = new Map();
    for (const sp of slideDoc.getElementsByTagNameNS(P_NS, 'sp')) {
      const name = sp.getElementsByTagNameNS(P_NS, 'cNvPr')[0]?.getAttribute('name');
      if (name) shapes.set(name, sp);
    }
    assert.equal(shapes.get('weight').getElementsByTagNameNS(A_NS, 'latin')[0].getAttribute('typeface'), 'Coda ExtraBold');
    assert.equal(shapes.get('cjk-inline').getElementsByTagNameNS(A_NS, 'ea')[0].getAttribute('typeface'), 'Noto Sans SC');

    const frames = [...slideDoc.getElementsByTagNameNS(P_NS, 'graphicFrame')];
    const aliasesFrame = frames.find((f) => f.getElementsByTagNameNS(P_NS, 'cNvPr')[0]?.getAttribute('name') === 'aliases');
    const rows = [...aliasesFrame.getElementsByTagNameNS(A_NS, 'tr')];
    assert.deepEqual(
      rows.map((r) => r.getElementsByTagNameNS(A_NS, 'latin')[0].getAttribute('typeface')),
      ['Unna', 'Liter'],
    );

    for (const part of archive.names()) {
      if (!part.startsWith('ppt/fonts/')) continue;
      const data = archive.read(part);
      assert.equal(data.readUInt32LE(0), data.length);
      assert.equal(data.subarray(34, 36).toString('ascii'), 'LP');
      assert.ok(fonts.has(readFontFaces(data)[0].family));
    }

    // A failed replacement must not publish the writer's fallback or overwrite a good file.
    const originalOutput = fs.readFileSync(output);
    fs.writeFileSync(pagePath, originalSource.toString('utf8').replace('frac', 'unsupportedcommand'));
    await assert.rejects(exportPptx(source, { output, force: true, offline: true, quiet: true }), /formula/);
    assert.deepEqual(fs.readFileSync(output), originalOutput);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('package verification catches invalid notes XML and missing internal relationships', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-verify-'));
  try {
    const original = path.join(dir, 'good.pptx');
    await exportPptx(MINIMAL, { output: original, embedFonts: false, offline: true, quiet: true });
    const goodBytes = fs.readFileSync(original);

    const brokenNotes = updateZip(goodBytes, {
      'ppt/notesSlides/notesSlide999.xml': Buffer.from('<notes>bad\0note</notes>'),
    });
    assert.throws(() => verifyOutput(brokenNotes, 'fade'), /invalid XML part/);

    const goodArchive = readZip(goodBytes);
    const badRels = goodArchive.read('ppt/_rels/presentation.xml.rels').toString('utf8').replace('slides/slide1.xml', 'slides/missing.xml');
    const brokenRels = updateZip(goodBytes, { 'ppt/_rels/presentation.xml.rels': Buffer.from(badRels) });
    assert.throws(() => verifyOutput(brokenRels, 'fade'), /missing part/);

    const extraSlide = updateZip(goodBytes, {
      'ppt/slides/slide2.xml': goodArchive.read('ppt/slides/slide1.xml'),
      'ppt/slides/_rels/slide2.xml.rels': goodArchive.read('ppt/slides/_rels/slide1.xml.rels'),
    });
    assert.throws(() => verifyOutput(extraSlide, 'fade'), /unlinked slide part/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
