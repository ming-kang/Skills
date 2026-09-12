#!/usr/bin/env node
// Repository-only visual review tooling; generated SVGs have no runtime dependencies.
import { chromium } from 'playwright';
import { mkdir, readdir, readFile, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

const repoDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const { values } = parseArgs({
  options: {
    output: { type: 'string', default: '.artifacts/visualize/current' },
    filter: { type: 'string', default: '' },
    compare: { type: 'string' },
    input: { type: 'string', default: 'visualize/assets' },
    help: { type: 'boolean', default: false },
  },
});

if (values.help) {
  console.log('Usage: npm run visualize:render -- [--input SVG_OR_DIR] [--output DIR] [--filter NAME] [--compare PRIOR_DIR]');
  process.exit(0);
}

const outputDir = path.resolve(repoDir, values.output);
const inputPath = path.resolve(repoDir, values.input);
const inputIsFile = (await stat(inputPath)).isFile();
const assetDir = inputIsFile ? path.dirname(inputPath) : inputPath;
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[char]);

async function svgFiles(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const filename = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await svgFiles(filename));
    else if (entry.name.endsWith('.svg')) files.push(filename);
  }
  return files.sort();
}

// Use the browser's actual font metrics, complementing the Python geometry checks.
function inspectText() {
  const svg = document.documentElement;
  const canvas = svg.getBoundingClientRect();
  const texts = [...svg.querySelectorAll('text')].flatMap((element) => {
    if (element.closest('defs')) return [];
    const style = getComputedStyle(element);
    if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) return [];
    const rect = element.getBoundingClientRect();
    if (!rect.width || !rect.height) return [];
    return [{
      text: element.textContent.trim(),
      x: rect.x - canvas.x, y: rect.y - canvas.y,
      width: rect.width, height: rect.height,
    }];
  });
  const issues = [];
  for (const text of texts) {
    if (text.x < -0.5 || text.y < -0.5 ||
        text.x + text.width > canvas.width + 0.5 ||
        text.y + text.height > canvas.height + 0.5) {
      issues.push(`Text outside canvas: ${text.text}`);
    }
  }
  for (let i = 0; i < texts.length; i++) {
    for (let j = i + 1; j < texts.length; j++) {
      const a = texts[i], b = texts[j];
      const overlapX = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
      const overlapY = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);
      if (overlapX > 0.5 && overlapY > 0.5) {
        issues.push(`Text overlap: ${a.text} / ${b.text}`);
      }
    }
  }
  return { title: svg.querySelector('title')?.textContent, texts, issues };
}

function reviewHtml(records) {
  const cards = records.map((record) => `<article>
    <header><h2>${escapeHtml(record.name)}</h2><span>${record.width} × ${record.height}</span></header>
    <a href="${escapeHtml(record.png)}"><img src="${escapeHtml(record.png)}" alt="${escapeHtml(record.title)}" loading="lazy"></a>
    <footer>${record.issues.length ? record.issues.map(escapeHtml).join('<br>') : 'Browser text checks passed'}
    · <a href="${escapeHtml(record.svg)}">SVG</a> · <a href="${escapeHtml(record.png)}">Full-size PNG</a></footer>
  </article>`).join('\n');
  return `<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Visualize gallery review</title><style>
*{box-sizing:border-box}body{margin:0;padding:32px;background:#F5F4ED;color:#141413;font:14px/1.5 system-ui,sans-serif}
h1{margin:0;font-size:24px;font-weight:600}p{margin:8px 0 24px;color:#3D3D3A}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,600px),1fr));gap:24px}
article{background:#fff;border:1px solid #dddcd5;border-radius:10px;overflow:hidden}header,footer{padding:14px 20px}header{display:flex;justify-content:space-between;gap:16px;border-bottom:1px solid #eee}
h2{font-size:14px;font-weight:600;margin:0}span,footer{font-size:12px;color:#3D3D3A}img{display:block;width:100%;height:460px;object-fit:contain}a{color:#085041}footer{border-top:1px solid #eee}
@media(max-width:680px){body{padding:16px}img{height:auto}header{flex-wrap:wrap}}
</style><h1>Visualize gallery review</h1><p>${records.length} diagrams · Chromium · device scale 2 · open each PNG to inspect at full resolution. Automated text checks do not replace visual review.</p><main>${cards}</main></html>`;
}

function comparisonHtml(records, previous, previousDir) {
  const before = new Map(previous.records.map((record) => [record.name, record]));
  const rows = records.map((record) => {
    const prior = before.get(record.name);
    const imagePath = prior && path.relative(outputDir, path.join(previousDir, prior.png)).split(path.sep).join('/');
    return `<section><h2>${escapeHtml(record.name)}</h2><div class="pair">
      <figure><figcaption>Before${prior ? ` · ${prior.width} × ${prior.height}` : ''}</figcaption>
      ${prior ? `<a href="${escapeHtml(imagePath)}"><img src="${escapeHtml(imagePath)}" alt="Before: ${escapeHtml(prior.title)}" loading="lazy"></a>` : '<p>No prior capture</p>'}</figure>
      <figure><figcaption>After · ${record.width} × ${record.height}</figcaption>
      <a href="${escapeHtml(record.png)}"><img src="${escapeHtml(record.png)}" alt="After: ${escapeHtml(record.title)}" loading="lazy"></a></figure>
    </div></section>`;
  }).join('\n');
  return `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Visualize before and after</title><style>
  *{box-sizing:border-box}body{margin:0;padding:32px;color:#141413;background:#F5F4ED;font:14px/1.5 system-ui,sans-serif}h1{margin:0;font-size:24px}h2{margin:0;padding:16px 20px;font-size:14px;border-bottom:1px solid #dddcd5}
  section{margin:24px 0;border:1px solid #dddcd5;border-radius:10px;overflow:hidden;background:white}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0;padding:16px}figcaption{margin-bottom:12px;color:#3D3D3A}img{display:block;width:100%;height:auto}
  @media(max-width:800px){body{padding:16px}.pair{grid-template-columns:1fr}}
  </style><h1>Visualize before and after</h1><p>${records.length} diagrams · open an image to inspect at full resolution. Each version retains its own canvas proportions.</p>${rows}</html>`;
}

await mkdir(outputDir, { recursive: true });
const files = (inputIsFile ? [inputPath] : await svgFiles(assetDir))
  .filter((file) => file.endsWith('.svg') && path.relative(assetDir, file).split(path.sep).join('/').includes(values.filter));
if (!files.length) throw new Error(`No SVG assets match ${JSON.stringify(values.filter)}`);
const previousDir = values.compare && path.resolve(repoDir, values.compare);
const previous = previousDir && JSON.parse(await readFile(path.join(previousDir, 'report.json'), 'utf8'));
const browser = await chromium.launch();
const records = [];
try {
  const context = await browser.newContext({ deviceScaleFactor: 2, colorScheme: 'light' });
  const page = await context.newPage();
  for (const filename of files) {
    await page.goto(pathToFileURL(filename).href);
    const size = await page.locator('svg').evaluate((svg) => {
      const rect = svg.getBoundingClientRect();
      return { width: Math.ceil(rect.width), height: Math.ceil(rect.height) };
    });
    await page.setViewportSize(size);
    await page.evaluate(() => document.fonts.ready);
    const inspection = await page.evaluate(inspectText);
    const name = path.relative(assetDir, filename).split(path.sep).join('/');
    const png = `${name.slice(0, -4).replaceAll('/', '--')}.png`;
    const svg = png.replace(/\.png$/, '.svg');
    await page.locator('svg').screenshot({ path: path.join(outputDir, png), animations: 'disabled' });
    await writeFile(path.join(outputDir, svg), await readFile(filename));
    records.push({
      name, ...size, ...inspection, png, svg,
    });
    console.log(`${name}: ${size.width}×${size.height}, ${inspection.issues.length} text issue(s)`);
  }
  await writeFile(path.join(outputDir, 'report.json'), JSON.stringify({ browser: browser.version(), platform: process.platform, deviceScaleFactor: 2, records }, null, 2) + '\n');
  await writeFile(path.join(outputDir, 'index.html'), reviewHtml(records));
  if (previous) {
    await writeFile(path.join(outputDir, 'comparison.html'), comparisonHtml(records, previous, previousDir));
    console.log(`Comparison: ${path.join(outputDir, 'comparison.html')}`);
  }
  console.log(`Review: ${path.join(outputDir, 'index.html')}`);
  if (records.some((record) => record.issues.length)) process.exitCode = 1;
} finally {
  await browser.close();
}
