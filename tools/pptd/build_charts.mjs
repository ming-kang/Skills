#!/usr/bin/env node
// Vendor the published, standalone ESM bundle; no packages are needed at runtime.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const output = fileURLToPath(new URL('../../pptd/assets/charts/', import.meta.url));
const copies = [
  ['echarts', 'dist/echarts.esm.min.mjs', 'echarts.mjs'],
  ['echarts', 'LICENSE', 'LICENSE'],
  ['echarts', 'NOTICE', 'NOTICE'],
  ['echarts', 'licenses/LICENSE-d3', 'licenses/LICENSE-d3'],
  ['zrender', 'LICENSE', 'licenses/LICENSE-zrender'],
  ['tslib', 'LICENSE.txt', 'licenses/LICENSE-tslib'],
  ['tslib', 'CopyrightNotice.txt', 'licenses/CopyrightNotice-tslib.txt'],
];
for (const [pkg, source, destination] of copies) {
  const root = path.dirname(require.resolve(pkg === 'tslib' ? pkg : `${pkg}/package.json`));
  const target = path.join(output, destination);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(path.join(root, source), target);
}
console.log('Vendored ECharts SVG renderer and third-party notices into pptd/assets/charts/');
