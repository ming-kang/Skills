import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

import { exportPptx, parseArgs } from '../../../pptd/scripts/export.mjs';
import { makeDeck } from './helpers.mjs';
import { parseCss, splitCss } from '../../../pptd/scripts/lib/core/css.mjs';
import { fetchBounded } from '../../../pptd/scripts/lib/core/net.mjs';
import { checkXmlString, parseXml } from '../../../pptd/scripts/lib/core/xml.mjs';
import { checkChart } from '../../../pptd/scripts/lib/deck/chart.mjs';
import { readContent } from '../../../pptd/scripts/lib/deck/content.mjs';
import { tableCells } from '../../../pptd/scripts/lib/deck/table.mjs';
import { PptxPackage } from '../../../pptd/scripts/lib/pptx/package.mjs';
import { readZip, writeZip } from '../../../pptd/scripts/lib/pptx/zip.mjs';
import { prepareFonts } from '../../../pptd/scripts/lib/prepare/fonts.mjs';
import { createMathBridge, validateFormulas } from '../../../pptd/scripts/lib/prepare/formulas.mjs';
import { readFontBytes } from '../../../pptd/scripts/lib/prepare/font_data.mjs';
import { create as createFont } from '../../../pptd/assets/vendor/fontkit.mjs';

const SKILL = path.resolve(import.meta.dirname, '../../../pptd');

function textProject(text) {
  return { pages: [{ pagePath: 'pages/01.page', elements: [{
    elementId: 'text', elementType: 'text', bounds: [0, 0, 800, 80],
    content: { text, fontFamily: 'Liter' },
  }] }] };
}

test('the common XML boundary permits supplementary characters but rejects lone surrogates and controls', () => {
  checkXmlString('中文 😀 𝑥', 'text');
  assert.equal(parseXml('<r>😀</r>').documentElement.textContent, '😀');
  for (const value of ['\0', '\ud800', '\udfff', '\ufffe']) assert.throws(() => checkXmlString(value, 'text'), /XML-forbidden/);
});

test('one table expansion preserves sparse positions, source labels and row/column/text-style precedence', () => {
  const theme = { textStyles: { body: { fontSize: 16 } }, tableStyles: {
    sample: { cellStyle: { fontFamily: 'Liter' }, firstRowStyle: { color: '#FF0000' },
      firstColumnStyle: { color: '#0000FF' }, rowOverColumn: false },
  } };
  const table = {
    elementId: 'table', elementType: 'table', bounds: [0, 0, 600, 300], style: '$sample',
    columnWidths: [0.25, 0.25, 0.5], rowHeights: [0.4, 0.2, 0.4],
    rows: [[{ text: 'merged', rowSpan: 2, colSpan: 2, textStyle: '$body' }, { text: 'r0c2' }],
      [{ text: 'r1c2' }], [{ text: 'r2c0' }, { text: 'r2c1' }, { text: 'r2c2', color: '#00FF00' }]],
  };
  const cells = tableCells(table, theme);
  assert.deepEqual(cells.map(({ row, column }) => [row, column]), [[0, 0], [0, 2], [1, 2], [2, 0], [2, 1], [2, 2]]);
  assert.equal(cells[0].style.color, '#0000FF');
  assert.equal(cells[0].style.fontSize, 16);
  assert.equal(cells[5].style.color, '#00FF00');
  const blocks = readContent({ theme, pages: [{ pagePath: 'p.page', elements: [table] }] }).texts;
  assert.equal(blocks[2].holder, table.rows[1][0]);
  assert.equal(blocks[2].location, 'p.page: table.rows[1][0]');
  theme.tableStyles.sample.rowOverColumn = true;
  assert.equal(tableCells(table, theme)[0].style.color, '#FF0000');
  const broken = structuredClone(table);
  broken.rows[1].push({ text: 'overruns' });
  assert.throws(() => tableCells(broken, theme), /beyond the table grid/);
});

test('CSS parsing respects quoted delimiters, URLs and important precedence; fonts share the rich-text DOM', async () => {
  assert.deepEqual(splitCss("'Family, One', Liter", ','), ["'Family, One'", ' Liter']);
  const css = parseCss('background:url("https://example.test/a;b:c");font-family:Unna!important;font-family:Liter');
  assert.equal(css.get('background'), 'url("https://example.test/a;b:c")');
  assert.equal(css.get('font-family'), 'Unna');
  // Authored CSS is read like a browser would; generated SVG must be fully understood.
  assert.deepEqual([...parseCss('color:;font-family:"Unna;bogus')], [['font-family', '"Unna']]);
  assert.equal(parseCss('/* note */ color:#FF0000').get('/* note */ color'), '#FF0000');
  assert.throws(() => parseCss('font-family:"Unna', { strict: true }), /unbalanced/);
  assert.throws(() => parseCss('/* note */ color:#FF0000', { strict: true }), /comments/);
  assert.throws(() => parseCss('color', { strict: true }), /unsupported inline CSS/);
  const project = textProject('<p><!-- 中文注释 --><a href="https://example.test/中文">link</a> <span style="font-family:\'Unna\'"><strong>AV<em>fi</em></strong></span></p>');
  const content = readContent(project);
  const fonts = await prepareFonts(project, content, { projectRoot: os.tmpdir(), offline: true });
  assert.equal(content.texts[0].holder, project.pages[0].elements[0].content);
  assert.deepEqual(fonts.families, ['Liter', 'Unna']);
  assert.deepEqual(fonts.bindings.filter((face) => face.family === 'Unna').map((face) => face.slot), ['bold', 'boldItalic', 'regular']);
  assert.equal(fonts.warnings.length, 0);
  const text = project.pages[0].elements[0].content.text;
  assert.match(text, /font-family:Unna/);
  assert.match(text, /中文注释/);
});

test('one text grammar: documented tags are markup, entities decode, everything else is literal paragraphs', async () => {
  const canonical = async (text) => {
    const project = textProject(text);
    await prepareFonts(project, readContent(project), { projectRoot: os.tmpdir(), offline: true, embed: false });
    return project.pages[0].elements[0].content.text;
  };
  // The writer alone deletes `<0.05 … >`, `&nbsp;`, text beside a block and inline tags outside one.
  assert.equal(await canonical('p<0.05, R&D; AT&T > 1 &copy; &nbsp;| List<String>'), '<p>p&lt;0.05, R&amp;D; AT&amp;T &gt; 1 © \u00a0| List&lt;String&gt;</p>');
  assert.equal(await canonical('first\r\n\nthird\n\n'), '<p>first</p><p></p><p>third</p>');
  assert.equal(await canonical('lead <strong>bold</strong>\na<br>b'), '<p>lead <strong>bold</strong></p><p>a<br/>b</p>');
  assert.equal(await canonical('<!-- note -->\n<p>one</p>\n tail\n<ul><li>item</li></ul>\n'), '<p>one</p><p> tail</p><ul><li>item</li></ul>');
  assert.equal(await canonical('<p><span style=color:#FF0000;bogus>x</span></p>'), '<p><span style="color:#FF0000;bogus">x</span></p>');
  for (const text of ['Hello', 'a\nb', '<P>Upper</P>', '<p>\\(a < b & c\\)</p>']) {
    const once = await canonical(text);
    assert.equal(await canonical(once), once);
  }
  for (const broken of ['<p><strong>bold</p>', '<p>one</span></p>', 'if a <b and c> d']) {
    await assert.rejects(canonical(broken), /invalid rich text pages\/01\.page: text: .*close every tag/);
  }
  assert.throws(() => readContent(textProject('<p>\\(x + &#0;\\)</p>')), /XML-forbidden/);
  assert.throws(() => readContent(textProject('\\(a <strong>b</strong>\\)')), /tags are not allowed inside formulas/);
});

test('encoded CJK text and legacy quoted Latin/CJK font pairs select covering fonts', async () => {
  for (const text of ['&#x4e2d;&#x6587;', '<p>&#x4e2d;&#x6587;</p>']) {
    const project = textProject(text);
    project.pages[0].elements[0].content.fontFamily = 'Unna';
    const fonts = await prepareFonts(project, readContent(project), { projectRoot: os.tmpdir(), offline: true, embed: false });
    assert.deepEqual(fonts.families, ['Noto Sans SC', 'Unna']);
    assert.deepEqual(project.pages[0].elements[0].content.fontFamily, { latin: 'Unna', ea: 'Noto Sans SC' });
  }
  const paired = textProject('<p><span style="font-family:\'Unna, Noto Sans SC\'">AV 中文</span></p>');
  await prepareFonts(paired, readContent(paired), { projectRoot: os.tmpdir(), offline: true, embed: false });
  assert.match(paired.pages[0].elements[0].content.text, /font-family:Unna, Noto Sans SC/);
});

test('the formula bridge shares parsed trees while preserving per-use styles and refusing incomplete conversion', () => {
  const project = textProject('<p><!-- \\) is not a formula -->\\(x+1\\) and \\(x+1\\)</p><span data-math-node="" data-tex="\\frac{x}{y}">legacy</span>');
  const original = project.pages[0].elements[0].content.text;
  const content = readContent(project);
  assert.equal(validateFormulas(content.formulas), 3);
  assert.equal(project.pages[0].elements[0].content.text, original);
  const bridge = createMathBridge(content.formulas);
  assert.equal(bridge.expectedCount, 3);
  assert.match(bridge.mathLoader(' x+1 ', { fontSize: 12, color: '#FF0000' }), /sz="1200"/);
  assert.match(bridge.mathLoader('x+1', { fontSize: 18, color: '#00FF00' }), /sz="1800"/);
  assert.match(bridge.mathLoader('\\frac{x}{y}', {}), /<m:f>/);
  assert.equal(bridge.assertComplete(), 3);
  assert.doesNotMatch(content.texts[0].markup.serialize(), /data-math-node|data-tex/);
  assert.equal(project.pages[0].elements[0].content.text, original);
  const incomplete = createMathBridge(readContent(textProject('\\(x\\)')).formulas);
  assert.throws(() => incomplete.assertComplete(), /count mismatch/);
  assert.equal(incomplete.mathLoader('unexpected', {}), null);
  assert.throws(() => incomplete.assertComplete(), /unexpected formula/);
  for (const text of ['\\(x', '\\)', '\\(\\)', '\\(x \\(y\\)\\)']) assert.throws(() => readContent(textProject(text)), /formula/);
});

test('the content plan keeps multiline math intact and the public exporter preserves canonical text', async () => {
  const latex = String.raw`\begin{matrix}1&2\\
3&4\end{matrix}`;
  const text = `Lead p<0.05 \\(a < b \\land b > c\\)\nMatrix \\(${latex}\\)\nList<T> &copy; &nbsp;end`;
  const project = textProject(text);
  const content = readContent(project);
  assert.deepEqual(content.formulas.map((item) => item.latex), ['a < b \\land b > c', latex]);
  assert.equal(content.texts[0].markup.root.childNodes.length, 3);
  const root = content.texts[0].markup.root;
  await prepareFonts(project, content, { projectRoot: os.tmpdir(), offline: true, embed: false });
  assert.equal(content.texts[0].markup.root, root);
  assert.equal(validateFormulas(content.formulas), 2);

  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-content-plan-'));
  try {
    project.pages[0].elements[0].bounds = [40, 40, 800, 380];
    project.pages[0].elements[0].content = { fontFamily: 'Unna', text };
    const source = makeDeck(dir, { page: JSON.stringify({ elements: project.pages[0].elements }) });
    const page = path.join(dir, 'pages/01.page');
    const original = fs.readFileSync(page);
    const output = path.join(dir, 'deck.pptx');
    const summary = await exportPptx(source, { output, offline: true, quiet: true });
    assert.equal(summary.formulas, 2);
    const archive = readZip(fs.readFileSync(output));
    const xml = archive.read('ppt/slides/slide1.xml').toString('utf8');
    assert.match(xml, /Lead p&lt;0\.05/);
    assert.match(xml, /List&lt;T&gt; © \u00a0end/);
    assert.match(xml, /<m:m>/);
    assert.deepEqual(fs.readFileSync(page), original);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('native candlesticks infer a value y-axis, and prototype names are not chart types', () => {
  const chart = {
    data: { cols: ['quarter', 'open', 'high', 'low', 'close'], rows: [['Q1', 2, 5, 1, 3], ['Q2', 3, 6, 2, '4']] },
    series: [{ type: 'candlestick', encode: { x: 'quarter', open: 'open', high: 'high', low: 'low', close: 'close' } }],
  };
  assert.deepEqual(checkChart(chart, 'stock'), []);
  assert.throws(() => checkChart({ ...chart, xAxis: { type: 'value' } }, 'stock'), /finite number/);
  assert.throws(() => checkChart({ ...chart, series: [{ type: 'toString' }] }, 'stock'), /unsupported/);
});

test('bounded downloads cancel oversized streams and reject an unsafe redirect before fetching it', async () => {
  const originalFetch = globalThis.fetch;
  let cancelled = false, calls = 0;
  try {
    globalThis.fetch = async () => new Response(new ReadableStream({
      pull(controller) { controller.enqueue(new Uint8Array(4)); },
      cancel() { cancelled = true; },
    }));
    await assert.rejects(fetchBounded('https://example.test/image', { maxBytes: 8 }), /download limit/);
    assert.equal(cancelled, true);
    globalThis.fetch = async () => { calls++; return new Response(null, { status: 302, headers: { location: 'file:///unsafe' } }); };
    await assert.rejects(fetchBounded('https://example.test/redirect'), /unsupported protocol/);
    assert.equal(calls, 1);
  } finally { globalThis.fetch = originalFetch; }
});

test('ZIP reads are cached; XML reads are not edits; binary/XML replacements invalidate the right cache', () => {
  const bytes = writeZip([{ name: 'part.xml', data: '<r a="old"/>' }, { name: 'plain.txt', data: 'bytes', method: 0 }]);
  const pkg = PptxPackage.open(bytes);
  const doc = pkg.readXml('part.xml');
  assert.equal(pkg.dirty, false);
  assert.equal(pkg.toBuffer(), bytes);
  doc.documentElement.setAttribute('a', 'new');
  pkg.writeXml('part.xml', doc);
  assert.match(pkg.readBytes('part.xml').toString(), /a="new"/);
  pkg.writeBytes('part.xml', Buffer.from('<replacement/>'));
  assert.equal(pkg.readXml('part.xml').documentElement.localName, 'replacement');
  pkg.readOrCreateXml('created.xml', 'urn:test', 'r');
  assert.equal(pkg.has('created.xml'), true);
  const archive = readZip(pkg.toBuffer());
  archive.verifyAll();
  assert.equal(archive.read('plain.txt'), archive.read('plain.txt'));
  const corrupt = readZip(Buffer.from(bytes));
  corrupt.entries.find((entry) => entry.name === 'plain.txt').compressed[0] ^= 1;
  assert.throws(() => corrupt.verifyAll(), /CRC/);
});

test('the slim fontkit bundle retains legacy getter/method caches, kerning, glyph paths and CJK coverage', () => {
  const unna = createFont(readFontBytes(path.join(SKILL, 'assets/fonts/unna/Unna-Regular.ttf.gz')));
  assert.equal(unna.bbox, unna.bbox);
  assert.equal(unna.characterSet, unna.characterSet);
  const glyph = unna.glyphForCodePoint(65);
  assert.equal(glyph.path, glyph.path);
  assert.equal(unna._cmapProcessor.codePointsForGlyph(glyph.id), unna._cmapProcessor.codePointsForGlyph(glyph.id));
  assert.match(glyph.path.toSVG(), /^M/);
  const av = unna.layout('AV');
  assert.ok(av.positions.reduce((sum, position) => sum + position.xAdvance, 0) < av.glyphs.reduce((sum, item) => sum + item.advanceWidth, 0));
  const noto = createFont(readFontBytes(path.join(SKILL, 'assets/fonts/notosanssc/NotoSansSC-Regular.ttf.gz')));
  assert.ok(noto.layout('中文').glyphs.every((item) => item.id !== 0 && item.path.toSVG()));
  assert.throws(() => createFont(Buffer.from('wOF2' + '\0'.repeat(64))), /Unknown font format/);
});

test('stdlib CLI parsing preserves repeated options and the writer facade rejects a corrupted canonical binary', async () => {
  const args = parseArgs(['deck', '-o', 'out.pptx', '--font-dir', 'one', '--font-dir', 'two', '--no-embed-fonts', '--offline']);
  assert.deepEqual(args.fontDirs, ['one', 'two']);
  assert.equal(args.embedFonts, false);
  assert.equal(args.output, 'out.pptx');
  assert.throws(() => parseArgs(['deck', '--unknown']), /Unknown option/);
  assert.throws(() => parseArgs(['deck', '--output']), /argument/);
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-writer-gate-'));
  try {
    const writer = path.join(temp, 'scripts/lib/pptx/writer.mjs');
    const wasm = path.join(temp, 'assets/wasm/pptd_wasm_bg.wasm');
    fs.mkdirSync(path.dirname(writer), { recursive: true });
    fs.mkdirSync(path.dirname(wasm), { recursive: true });
    fs.copyFileSync(path.join(SKILL, 'scripts/lib/pptx/writer.mjs'), writer);
    const bytes = fs.readFileSync(path.join(SKILL, 'assets/wasm/pptd_wasm_bg.wasm'));
    bytes[bytes.length - 1] ^= 1;
    fs.writeFileSync(wasm, bytes);
    const { loadWasmExporter } = await import(pathToFileURL(writer));
    await assert.rejects(loadWasmExporter(), /version-locked writer/);
  } finally { fs.rmSync(temp, { recursive: true, force: true }); }
});
