#!/usr/bin/env node
// Vendor licensed original fonts, not undocumented legacy EOT files.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

import { readFontFaces } from '../../pptd/scripts/lib/prepare/font_data.mjs';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const REF = '86aced91de05cd4f96a06838124cca45be337b2b';
const BASE = `https://raw.githubusercontent.com/google/fonts/${REF}/ofl/`;
const OUTPUT = path.join(ROOT, 'pptd', 'assets', 'fonts');
const FAMILIES = [
  ['Liter', 'liter', 'Liter', ['Regular'], []],
  ['Hedvig Letters Sans', 'hedvigletterssans', 'HedvigLettersSans', ['Regular'], ['HedvigLettersSans']],
  ['Oranienbaum', 'oranienbaum', 'Oranienbaum', ['Regular'], []],
  ['Quattrocento Sans', 'quattrocentosans', 'QuattrocentoSans', ['Regular', 'Bold', 'Italic', 'BoldItalic'], ['QuattrocentoSans']],
  ['Sorts Mill Goudy', 'sortsmillgoudy', 'SortsMillGoudy', ['Regular', 'Italic'], ['SortsMillGoudy']],
  ['Unna', 'unna', 'Unna', ['Regular', 'Bold', 'Italic', 'BoldItalic'], []],
  ['Coda', 'coda', 'Coda', ['Regular', 'ExtraBold'], []],
  ['Jersey 15', 'jersey15', 'Jersey15', ['Regular'], ['Jersey15']],
  ['Jersey 20 Charted', 'jersey20charted', 'Jersey20Charted', ['Regular'], ['Jersey20Charted']],
];
const NOTO = 'https://fonts.gstatic.com/s/notosanssc/v41/k3kCo84MPvpLmixcA63oeAL7Iqp5IZJF9bmaG9_FnYw.ttf';
const MAX_FONT_BYTES = 64 * 1024 * 1024;

async function download(url) {
  const response = await fetch(url, {
    headers: { 'User-Agent': 'pptd-font-build/1' },
    signal: AbortSignal.timeout(45000),
  });
  if (!response.ok) throw new Error(`font download failed (${response.status}): ${url}`);
  const data = Buffer.from(await response.arrayBuffer());
  if (data.length > MAX_FONT_BYTES) throw new Error(`font source exceeds build limit: ${url}`);
  return data;
}

async function main() {
  const jobs = [];
  const aliases = {};
  for (const [family, folder, stem, styles, names] of FAMILIES) {
    for (const name of names) aliases[name] = family;
    jobs.push([family, folder, 'OFL.txt', `${BASE}${folder}/OFL.txt`]);
    for (const style of styles) {
      const filename = `${stem}-${style}.ttf`;
      jobs.push([family, folder, filename, `${BASE}${folder}/${encodeURIComponent(filename)}`]);
    }
  }
  jobs.push(['Noto Sans SC', 'notosanssc', 'OFL.txt', `${BASE}notosanssc/OFL.txt`]);
  jobs.push(['Noto Sans SC', 'notosanssc', 'NotoSansSC-Regular.ttf', NOTO]);

  const payloads = await Promise.all(jobs.map((job) => download(job[3])));
  const catalog = {
    sourceRevision: REF,
    aliases,
    fallbacks: { latin: 'Liter', ea: 'Noto Sans SC' },
    faces: [],
  };

  for (let i = 0; i < jobs.length; i++) {
    const [, folder, filename, source] = jobs[i];
    const data = payloads[i];
    const target = path.join(OUTPUT, folder, filename);
    if (filename.endsWith('.ttf')) {
      const face = readFontFaces(data)[0];
      if (face.variable) throw new Error(`expected a static font, got variable source: ${source}`);
      catalog.faces.push({
        family: face.family,
        slot: face.slot,
        src: `${folder}/${filename}`,
        license: `${folder}/OFL.txt`,
        source,
        sha256: crypto.createHash('sha256').update(data).digest('hex'),
      });
    }
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, data);
  }
  fs.writeFileSync(path.join(OUTPUT, 'catalog.json'), JSON.stringify(catalog, null, 2) + '\n', 'utf8');
  console.log(`Vendored ${catalog.faces.length} static font faces with OFL licenses`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
