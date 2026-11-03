#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { loadWasmExporter } from './wasm-exporter.mjs';

const DEFAULT_WASM = new URL('../assets/wasm/pptd_wasm_bg.wasm', import.meta.url);

function safeJoin(root, relative) {
  if (typeof relative !== 'string' || !relative.trim()) {
    throw new Error('project path must be a non-empty string');
  }
  const base = path.resolve(root);
  const target = path.resolve(base, relative.replace(/\\/g, '/'));
  const prefix = base.endsWith(path.sep) ? base : base + path.sep;
  if (target !== base && !target.startsWith(prefix)) {
    throw new Error(`project path escapes the PPTD directory: ${relative}`);
  }
  return target;
}

function normalizeCustomShape(shape, size) {
  if (shape?.shapeName !== 'custom' || !shape.path || shape.viewBox) return shape;
  const separator = String(shape.path).indexOf(';');
  if (separator >= 0) {
    const [width, height] = String(shape.path)
      .slice(0, separator)
      .split(',')
      .map(Number);
    if (!(width > 0) || !(height > 0)) return shape;
    return {
      ...shape,
      viewBox: [width, height],
      path: String(shape.path).slice(separator + 1),
    };
  }
  return { ...shape, viewBox: size };
}

export function normalizeElement(element) {
  const size = [element.bounds?.[2], element.bounds?.[3]];
  if (element.elementType === 'shape') return normalizeCustomShape(element, size);
  if (element.elementType === 'image' && element.cropShape) {
    return { ...element, cropShape: normalizeCustomShape(element.cropShape, size) };
  }
  return element;
}

export function buildProject(payload) {
  const { manifestPath, manifest } = payload;
  if (typeof manifestPath !== 'string' || !manifestPath) {
    throw new Error('project JSON needs manifestPath');
  }
  if (manifest?.version !== 'v2') throw new Error('only PPTD version v2 is supported');
  if (!Array.isArray(payload.pages) || !payload.pages.length) {
    throw new Error('project JSON needs a non-empty pages array');
  }
  return {
    ...manifest,
    version: 'v2',
    pages: payload.pages.map(({ path: pagePath, data }) => {
      if (!data || !Array.isArray(data.elements)) {
        throw new Error(`invalid page elements: ${pagePath}`);
      }
      return {
        ...data,
        pagePath: String(pagePath).replace(/\\/g, '/'),
        elements: data.elements.map(normalizeElement),
      };
    }),
    pptdFileName: path.basename(manifestPath),
  };
}

function collectImageSources(project) {
  const sources = new Set();
  const visit = (holder) => {
    if (holder && typeof holder.src === 'string' && holder.src) sources.add(holder.src);
  };
  for (const page of project.pages) {
    if (page.background?.type === 'image') visit(page.background);
    for (const element of page.elements) {
      if (element.elementType === 'image') visit(element);
      if (element.fill?.type === 'image') visit(element.fill);
    }
  }
  return [...sources];
}

function extensionFor(src, contentType = '') {
  const match = /\.(png|jpe?g|gif|svg)(?:$|[?#])/i.exec(src);
  const byType = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/gif': 'gif',
    'image/svg+xml': 'svg',
  }[String(contentType).split(';')[0].trim()];
  let extension = match?.[1]?.toLowerCase() || byType || 'png';
  if (extension === 'jpeg') extension = 'jpg';
  return `.${extension}`;
}

async function imageBytes(src, projectRoot) {
  if (src.startsWith('data:')) {
    const match = /^data:([^;,]+)?(;base64)?,(.*)$/s.exec(src);
    if (!match) throw new Error('invalid data URL image');
    return {
      bytes: match[2]
        ? Buffer.from(match[3], 'base64')
        : Buffer.from(decodeURIComponent(match[3])),
      extension: extensionFor(src, match[1] || ''),
    };
  }
  if (/^https?:\/\//i.test(src)) {
    const response = await fetch(src, { signal: AbortSignal.timeout(30000) });
    if (!response.ok) throw new Error(`image fetch failed ${response.status}: ${src}`);
    return {
      bytes: Buffer.from(await response.arrayBuffer()),
      extension: extensionFor(src, response.headers.get('content-type') || ''),
    };
  }
  const local = safeJoin(projectRoot, src.replace(/^file:\/\/+/, ''));
  if (!fs.existsSync(local)) throw new Error(`missing local image: ${src}`);
  return { bytes: fs.readFileSync(local), extension: extensionFor(src) };
}

export async function resolveImages(project, projectRoot) {
  const images = {};
  const remapped = new Map();
  const sources = collectImageSources(project);
  await Promise.all(
    sources.map(async (src, index) => {
      const { bytes, extension } = await imageBytes(src, projectRoot);
      const key = `wasm-assets/img-${index}${extension}`;
      images[key] = new Uint8Array(bytes);
      remapped.set(src, key);
    }),
  );
  const rewrite = (holder) => {
    if (holder && remapped.has(holder.src)) holder.src = remapped.get(holder.src);
  };
  for (const page of project.pages) {
    if (page.background?.type === 'image') rewrite(page.background);
    for (const element of page.elements) {
      if (element.elementType === 'image') rewrite(element);
      if (element.fill?.type === 'image') rewrite(element.fill);
    }
  }
  return images;
}

function offlineSignature(value) {
  const digest = crypto.createHash('sha256').update(value, 'utf8').digest('hex');
  return `offline-bypass-${digest.slice(0, 32)}`;
}

function parseArgs(argv) {
  const args = { json: null, output: null, wasm: DEFAULT_WASM, help: false };
  const values = [...argv];
  while (values.length) {
    const arg = values.shift();
    if (arg === '--json') args.json = values.shift();
    else if (arg === '--output' || arg === '-o') args.output = values.shift();
    else if (arg === '--wasm') args.wasm = values.shift();
    else if (arg === '--help' || arg === '-h') args.help = true;
    else throw new Error(`unknown argument: ${arg}`);
  }
  return args;
}

async function main(argv) {
  const args = parseArgs(argv);
  if (args.help || !args.json || !args.output) {
    console.log(
      'Usage: node export_pptd.mjs --json project.json --output deck.pptx [--wasm writer.wasm]',
    );
    if (!args.help) throw new Error('--json and --output are required');
    return;
  }
  const payload = JSON.parse(fs.readFileSync(args.json, 'utf8'));
  const project = buildProject(payload);
  const images = await resolveImages(project, path.dirname(payload.manifestPath));
  const signature = offlineSignature(JSON.stringify(project));
  const { exportPPTDToPPTXBytes } = await loadWasmExporter(args.wasm);
  const bytes = exportPPTDToPPTXBytes(
    project,
    {
      fonts: [],
      customFonts: [],
      images,
      fileName: path.basename(args.output),
      slideTransition: { effect: 'fade', speed: 'fast' },
      chartImages: [],
    },
    signature,
  );
  const output = Buffer.from(bytes);
  if (output[0] !== 0x50 || output[1] !== 0x4b) {
    throw new Error('WASM writer did not return a ZIP/PPTX payload');
  }
  fs.writeFileSync(args.output, output);
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  main(process.argv.slice(2)).catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
