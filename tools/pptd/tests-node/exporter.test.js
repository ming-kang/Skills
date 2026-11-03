import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  buildProject,
  normalizeElement,
  resolveImages,
} from '../../../pptd/scripts/export_pptd.mjs';
import { loadWasmExporter } from '../../../pptd/scripts/wasm-exporter.mjs';

const WASM = new URL('../../../pptd/assets/wasm/pptd_wasm_bg.wasm', import.meta.url);

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

test('project JSON becomes the page-object shape expected by WASM', () => {
  const project = buildProject({
    manifestPath: path.resolve('fixture', 'deck.pptd'),
    manifest: { version: 'v2', title: 'Fixture', pages: ['pages/01.page'] },
    pages: [{ path: 'pages/01.page', data: { elements: [] } }],
  });
  assert.equal(project.version, 'v2');
  assert.equal(project.pptdFileName, 'deck.pptd');
  assert.equal(project.pages[0].pagePath, 'pages/01.page');
  assert.deepEqual(project.pages[0].elements, []);
});

test('local media resolves to bytes and all matching sources are remapped', async () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pptd-media-'));
  try {
    fs.mkdirSync(path.join(root, 'media'));
    const bytes = Buffer.from([0x89, 0x50, 0x4e, 0x47]);
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

test('the bundled writer matches the version-locked adapter', async () => {
  const exporter = await loadWasmExporter(fileURLToPath(WASM));
  assert.equal(typeof exporter.exportPPTDToPPTXBytes, 'function');
});
