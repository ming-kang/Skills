#!/usr/bin/env node
// Rebuild lossless font storage from the catalog's pinned original bytes and sources.
// The catalog is also runtime metadata/attribution; never bless a changed download
// by silently regenerating its SHA-256 or Windows family/style identity.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { gzipSync } from 'node:zlib';

import { fetchBounded } from '../../pptd/scripts/lib/core/net.mjs';
import { checkRelativePath } from '../../pptd/scripts/lib/deck/contract.mjs';
import { readFontBytes, readFontFaces } from '../../pptd/scripts/lib/prepare/font_data.mjs';

const ROOT = path.resolve(import.meta.dirname, '../../pptd/assets/fonts');
const catalog = JSON.parse(fs.readFileSync(path.join(ROOT, 'catalog.json'), 'utf8'));
const sha256 = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');
const target = (relative) => path.join(ROOT, checkRelativePath(relative, 'font catalog path'));
const download = (url) => fetchBounded(url, {
  label: 'font asset', timeoutMs: 45000, headers: { 'User-Agent': 'pptd-font-build/1' },
});

const fonts = await Promise.all(catalog.faces.map(async (entry) => {
  if (!entry.src.endsWith('.ttf.gz')) throw new Error(`bundled font storage must be .ttf.gz: ${entry.src}`);
  const file = target(entry.src);
  let bytes;
  // An intact installed payload makes normal asset rebuilds offline.
  try { bytes = readFontBytes(fs.existsSync(file) ? file : file.slice(0, -3)); } catch { /* Restore below. */ }
  if (!bytes || sha256(bytes) !== entry.sha256) bytes = await download(entry.source);
  if (sha256(bytes) !== entry.sha256) throw new Error(`original font SHA-256 changed: ${entry.source}`);
  const face = readFontFaces(bytes)[0];
  if (face.variable || face.family !== entry.family || face.slot !== entry.slot) {
    throw new Error(`font catalog family/style does not match ${entry.src}`);
  }
  return { file, bytes };
}));

const licenses = await Promise.all([...new Set(catalog.faces.map((entry) => entry.license))].map(async (license) => {
  const file = target(license);
  if (fs.existsSync(file)) return null;
  const url = `https://raw.githubusercontent.com/google/fonts/${catalog.sourceRevision}/ofl/${license}`;
  return { file, bytes: await download(url) };
}));

let original = 0, packed = 0;
for (const { file, bytes } of fonts) {
  const compressed = gzipSync(bytes, { level: 9 });
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, compressed);
  fs.rmSync(file.slice(0, -3), { force: true }); // Only the managed legacy raw copy.
  original += bytes.length;
  packed += compressed.length;
}
for (const item of licenses.filter(Boolean)) {
  fs.mkdirSync(path.dirname(item.file), { recursive: true });
  fs.writeFileSync(item.file, item.bytes);
}
console.log(`Vendored ${fonts.length} original font faces: ${original} → ${packed} bytes (lossless gzip); OFL licenses retained`);
