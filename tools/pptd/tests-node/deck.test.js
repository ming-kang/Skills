import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import { readProject } from '../../../pptd/scripts/lib/deck/project.mjs';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const SKILL_ROOT = path.join(REPO_ROOT, 'pptd');
const VALIDATE_CLI = path.join(SKILL_ROOT, 'scripts', 'validate.mjs');
const MINIMAL = path.join(REPO_ROOT, 'tools', 'pptd', 'tests', 'fixtures', 'minimal');

function makeDeck(root, { manifest, page } = {}) {
  fs.mkdirSync(path.join(root, 'pages'), { recursive: true });
  const manifestPath = path.join(root, 'deck.pptd');
  fs.writeFileSync(
    manifestPath,
    manifest ?? [
      'version: v2',
      'title: Validation fixture',
      'size: [960, 540]',
      'pages:',
      '  - pages/01.page',
      '',
    ].join('\n'),
    'utf8',
  );
  fs.writeFileSync(
    path.join(root, 'pages', '01.page'),
    page ?? [
      'elements:',
      '  - elementId: title',
      '    elementType: text',
      '    bounds: [100, 100, 400, 80]',
      '    content:',
      '      text: Hello',
      '',
    ].join('\n'),
    'utf8',
  );
  return manifestPath;
}

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
    assert.equal(project.pages[0].data.notes, '2026-11-14');
    assert.equal(project.pages[0].data.elements[0].content.text, 'yes');
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
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
