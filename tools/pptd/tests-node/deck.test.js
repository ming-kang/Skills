import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

import { readProject, validateProject } from '../../../pptd/scripts/lib/deck/project.mjs';
import { parseArgs as parseValidateArgs } from '../../../pptd/scripts/validate.mjs';
import { makeDeck } from './helpers.mjs';

const REPO_ROOT = path.resolve(import.meta.dirname, '..', '..', '..');
const SKILL_ROOT = path.join(REPO_ROOT, 'pptd');
const VALIDATE_CLI = path.join(SKILL_ROOT, 'scripts', 'validate.mjs');
const MINIMAL = path.join(REPO_ROOT, 'tools', 'pptd', 'tests', 'fixtures', 'minimal');

test('validate CLI rejects a missing manifest and succeeds on valid fixtures', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-missing-'));
  try {
    const failRes = spawnSync(process.execPath, [VALIDATE_CLI, path.join(dir, 'nope')], { encoding: 'utf8' });
    assert.equal(failRes.status, 1);
    assert.match(failRes.stderr, /pptd validation failed/);

    const okRes = spawnSync(process.execPath, [VALIDATE_CLI, MINIMAL], { encoding: 'utf8' });
    assert.equal(okRes.status, 0);
    const summary = JSON.parse(okRes.stdout);
    assert.equal(summary.valid, true);
    assert.equal(summary.slides, 1);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('validate CLI keeps warnings on stderr so stdout remains clean JSON', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-warn-json-'));
  try {
    makeDeck(dir, {
      page: [
        'elements:',
        '  - elementId: bleed',
        '    elementType: text',
        '    bounds: [-20, 100, 400, 80]',
        '    content:',
        '      text: Bleed',
        '',
      ].join('\n'),
    });
    const res = spawnSync(process.execPath, [VALIDATE_CLI, dir], { encoding: 'utf8' });
    assert.equal(res.status, 0);
    assert.match(res.stderr, /\[pptd\] warning:.*extends beyond/);
    const summary = JSON.parse(res.stdout);
    assert.equal(summary.warnings.length, 1);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('YAML 1.2 dates and yes/no stay strings', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-yaml12-'));
  try {
    const manifestPath = makeDeck(dir, {
      page: [
        'notes: 2026-11-14',
        'elements:',
        '  - {elementId: title, elementType: text, bounds: [100, 100, 400, 80], content: {text: yes}}',
        '',
      ].join('\n'),
    });
    const project = readProject(manifestPath);
    assert.equal(project.pages[0].notes, '2026-11-14');
    assert.equal(project.pages[0].elements[0].content.text, 'yes');
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('YAML non-finite chart values cannot silently become missing cells during normalization', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-non-finite-'));
  try {
    for (const value of ['.nan', '.inf', '-.inf']) {
      makeDeck(dir, { page: `elements:
  - elementId: chart
    elementType: chart
    bounds: [0, 0, 300, 200]
    data: {cols: [x, y], rows: [[A, 5], [B, ${value}]]}
    series: [{type: bar, encode: {x: x, y: y}}]
` });
      assert.throws(() => readProject(dir), /finite number/);
    }
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('invalid manifests, path escapes, customFonts escapes, and unknown $textStyle are rejected', () => {
  const head = 'version: v2\nsize: [960, 540]\n';
  const cases = [
    [head + 'pages:\n  - {}\n', /non-empty string/],
    [head + 'pages: [../outside.page]\n', /escapes/],
    [head + 'pages: [pages/01.page, pages/01.page]\n', /duplicate paths/],
    ['version: v3\nsize: [960, 540]\npages: [pages/01.page]\n', /only PPTD version: v2/],
    [head + 'customFonts:\n  - family: Evil\n    src: ../../secret.ttf\npages: [pages/01.page]\n', /escapes/],
  ];
  for (const [manifest, pattern] of cases) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-invalid-'));
    try {
      const manifestPath = makeDeck(dir, { manifest });
      assert.throws(() => readProject(manifestPath), pattern);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  }

  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-bad-style-'));
  try {
    const manifestPath = makeDeck(dir, {
      page: [
        'elements:',
        '  - elementId: t',
        '    elementType: text',
        '    bounds: [0, 0, 200, 60]',
        '    content:',
        '      style: $missing',
        '      text: Hello',
        '',
      ].join('\n'),
    });
    assert.throws(() => readProject(manifestPath), /unknown text style/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('all 44 design presets are retained and indexed', () => {
  const root = path.join(SKILL_ROOT, 'references', 'design_system');
  const index = fs.readFileSync(path.join(root, 'README.md'), 'utf8');
  const presets = new Set(
    fs.readdirSync(root).filter((name) => name.endsWith('.md') && name !== 'README.md').map((name) => name.slice(0, -3)),
  );
  const indexed = new Set([...index.matchAll(/`([a-z0-9-]+)`/g)].map((match) => match[1]));
  assert.equal(presets.size, 44);
  assert.deepEqual(indexed, presets);
});

test('all 7 slide category guides are retained and routed', () => {
  const root = path.join(SKILL_ROOT, 'references', 'slides_categories');
  const router = fs.readFileSync(path.join(SKILL_ROOT, 'references', 'slides_categories.md'), 'utf8');
  const scenarios = fs.readdirSync(root).filter((name) => name.endsWith('.md')).sort();
  assert.equal(scenarios.length, 7);
  for (const name of scenarios) {
    assert.ok(router.includes(`references/slides_categories/${name}`), `missing route for ${name}`);
  }
});

test('schema catches shape header leak, bad adjustments, invalid lines, missing $tokens, and float table sums pass', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-schema-fixes-'));
  try {
    // Valid float columnWidths [0.1, 0.1, 0.1, 0.7] (sums to 0.9999999999999999 in IEEE 754) + line + inferred horizontal bar
    const okManifest = makeDeck(dir, {
      manifest: JSON.stringify({
        version: 'v2',
        size: [960, 540],
        theme: { colors: { primary: '#2563EB' } },
        pages: ['pages/01.page'],
      }),
      page: JSON.stringify({
        background: { type: 'solid', color: '$primary' },
        elements: [
          {
            elementId: 'tbl',
            elementType: 'table',
            bounds: [40, 40, 400, 100],
            columnWidths: [0.1, 0.1, 0.1, 0.7],
            rowHeights: [1],
            rows: [[{ text: 'a' }, { text: 'b' }, { text: 'c' }, { text: 'd' }]],
          },
          {
            elementId: 'ln',
            elementType: 'line',
            bounds: [40, 160, 200, 40],
            viewBox: [200, 40],
            points: '0,0 100,40 200,0',
            curve: 'smooth',
            arrow: [null, 'arrow'],
          },
          {
            elementId: 'hbar',
            elementType: 'chart',
            bounds: [40, 220, 400, 200],
            data: { cols: ['dept', 'count'], rows: [['Eng', 10], ['Ops', 5]] },
            series: [{ type: 'bar', encode: { x: 'count', y: 'dept' } }],
          },
        ],
      }),
    });
    const project = readProject(okManifest);
    assert.equal(project.pages[0].elements.length, 3);

    // Reject shapeName: "shapeName" header leak and wrong adjustment arity
    const badShapes = [
      { elementId: 's1', elementType: 'shape', bounds: [0, 0, 100, 100], shapeName: 'shapeName' },
      { elementId: 's2', elementType: 'shape', bounds: [0, 0, 100, 100], shapeName: 'roundRect', adjustments: [1, 2] },
      { elementId: 's3', elementType: 'shape', bounds: [0, 0, 100, 100], shapeName: 'custom', path: '0,100;M0 0L10 10' },
      { elementId: 'l1', elementType: 'line', bounds: [0, 0, 100, 100], viewBox: [100, 100], points: '0,0' },
      { elementId: 't1', elementType: 'text', bounds: [0, 0, 100, 100], content: { color: '$typo', text: 'Hi' } },
    ];
    for (const el of badShapes) {
      makeDeck(dir, { page: JSON.stringify({ elements: [el] }) });
      assert.throws(() => readProject(dir));
    }

    // Reject missing ImageFill in page.background
    makeDeck(dir, {
      page: JSON.stringify({ background: { type: 'image', src: 'media/missing.png' }, elements: [] }),
    });
    assert.throws(() => readProject(dir), /missing local image/);

    // validate.mjs catches invalid formulas, advanced-chart cycles, and fake image bytes
    makeDeck(dir, {
      page: JSON.stringify({
        elements: [
          { elementId: 'badmath', elementType: 'text', bounds: [0, 0, 200, 60], content: { text: '\\(\\xrightarrow{f}\\)' } },
        ],
      }),
    });
    assert.equal(spawnSync(process.execPath, [VALIDATE_CLI, dir], { encoding: 'utf8' }).status, 0);

    makeDeck(dir, {
      page: JSON.stringify({
        elements: [
          { elementId: 'badmath', elementType: 'text', bounds: [0, 0, 200, 60], content: { text: '\\(\\notacommand\\)' } },
        ],
      }),
    });
    const badMathRes = spawnSync(process.execPath, [VALIDATE_CLI, dir], { encoding: 'utf8' });
    assert.equal(badMathRes.status, 1);
    assert.match(badMathRes.stderr, /notacommand/);

    makeDeck(dir, {
      page: JSON.stringify({
        elements: [
          {
            elementId: 'cycle',
            elementType: 'chart',
            bounds: [0, 0, 300, 200],
            data: { cols: ['s', 't', 'f'], rows: [['a', 'b', 1], ['b', 'a', 1]] },
            series: [{ type: 'sankey', encode: { source: 's', target: 't', flow: 'f' } }],
          },
        ],
      }),
    });
    const badSankeyRes = spawnSync(process.execPath, [VALIDATE_CLI, dir], { encoding: 'utf8' });
    assert.equal(badSankeyRes.status, 1);
    assert.match(badSankeyRes.stderr, /cycle/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('validate --check-fonts keeps stderr and JSON warnings aligned, stays read-only, and enforces CLI options', async () => {
  assert.throws(() => parseValidateArgs(['deck', '--font-dir', 'fonts']), /--font-dir requires --check-fonts/);
  const parsed = parseValidateArgs(['deck', '--check-fonts', '--font-dir', 'a', '--font-dir=b', '--offline']);
  assert.deepEqual(parsed.fontDirs, ['a', 'b']);
  assert.equal(parsed.checkFonts, true);
  assert.equal(parsed.offline, true);

  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-check-fonts-'));
  try {
    makeDeck(dir, {
      page: JSON.stringify({
        elements: [{
          elementId: 't1',
          elementType: 'text',
          bounds: [20, 20, 400, 60],
          content: { fontFamily: 'Unna', text: '<p>Step 1 → Step 2 😀</p>' },
        }],
      }),
    });

    const project = await validateProject(dir, { checkFonts: true, offline: true });
    // Validation must not mutate the canonical project's text or fontFamily.
    assert.equal(project.pages[0].elements[0].content.text, '<p>Step 1 → Step 2 😀</p>');
    assert.equal(project.pages[0].elements[0].content.fontFamily, 'Unna');
    assert.ok(project.warnings.some((w) => /Unna.*cannot shape.*2192.*Inter/.test(w)), project.warnings.join('\n'));
    assert.ok(project.warnings.some((w) => /Unna.*lacks glyphs.*1F600/.test(w)), project.warnings.join('\n'));

    const res = spawnSync(process.execPath, [VALIDATE_CLI, dir, '--check-fonts', '--offline'], { encoding: 'utf8' });
    assert.equal(res.status, 0, res.stderr);
    const summary = JSON.parse(res.stdout);
    assert.deepEqual(summary.warnings, project.warnings);
    for (const warning of summary.warnings) {
      assert.ok(res.stderr.includes(`[pptd] warning: ${warning}`), res.stderr);
    }

    // --offline must reject an uncached Google Fonts customFont during --check-fonts.
    makeDeck(dir, {
      manifest: [
        'version: v2',
        'size: [960, 540]',
        'customFonts:',
        '  - family: Inter',
        '    src: "https://fonts.googleapis.com/css2?family=Inter:wght@400&uncached=1"',
        'pages: [pages/01.page]',
        '',
      ].join('\n'),
    });
    const offRes = spawnSync(process.execPath, [VALIDATE_CLI, dir, '--check-fonts', '--offline'], { encoding: 'utf8' });
    assert.equal(offRes.status, 1);
    assert.match(offRes.stderr, /not cached for offline use/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
