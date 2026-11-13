#!/usr/bin/env node
// Public PPTD → PPTX export CLI (single-process Node.js runtime).
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { readProject } from './lib/deck/project.mjs';
import { loadWasmExporter } from './lib/pptx/writer.mjs';
import { patchFontBindings, patchTableImages } from './lib/pptx/patch.mjs';
import { patchTransitions, verifyOutput } from './lib/pptx/verify.mjs';
import { prepareAdvancedCharts } from './lib/prepare/charts.mjs';
import { prepareFonts } from './lib/prepare/fonts.mjs';
import { exportWithMath } from './lib/prepare/formulas.mjs';
import { prepareIcons } from './lib/prepare/icons.mjs';
import { resolveImages } from './lib/prepare/images.mjs';
import { createSvgFontOutliner } from './lib/prepare/svg_text.mjs';

const SKILL_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const CANONICAL_WASM = path.join(SKILL_DIR, 'assets', 'wasm', 'pptd_wasm_bg.wasm');
export const WASM_SHA256 = '589b362a444824c948f21ae99cdc32958c83b28e47a296d4f5905c76b04e0e6e';

function log(message) {
  process.stderr.write(`[pptd] ${message}\n`);
}

export function checkNodeVersion(version = process.versions.node) {
  const major = Number.parseInt(String(version).replace(/^v/i, '').split('.')[0], 10);
  if (!Number.isFinite(major) || major < 18) {
    throw new Error(`Node.js 18+ is required; found ${version}`);
  }
}

export function resolveWasm(override = null) {
  const target = override ? path.resolve(override) : CANONICAL_WASM;
  if (!fs.existsSync(target) || !fs.statSync(target).isFile()) {
    throw new Error(`PPTD WASM writer not found: ${target}`);
  }
  if (!override) {
    const digest = crypto.createHash('sha256').update(fs.readFileSync(target)).digest('hex');
    if (digest !== WASM_SHA256) {
      throw new Error('bundled WASM does not match the version-locked writer; repair the skill installation');
    }
  }
  return target;
}

/** The writer's custom-shape path may carry a `width,height;` prefix instead of a viewBox. */
function normalizeCustomShape(shape, size) {
  if (shape?.shapeName !== 'custom' || !shape.path || shape.viewBox) return shape;
  const separator = String(shape.path).indexOf(';');
  if (separator >= 0) {
    const [width, height] = String(shape.path).slice(0, separator).split(',').map(Number);
    if (!(width > 0) || !(height > 0)) return shape;
    return { ...shape, viewBox: [width, height], path: String(shape.path).slice(separator + 1) };
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

export function buildWasmProject(project) {
  return {
    ...project.manifest,
    version: 'v2',
    pages: project.pages.map(({ path: pagePath, data }) => ({
      ...data,
      pagePath: String(pagePath).replaceAll('\\', '/'),
      elements: data.elements.map(normalizeElement),
    })),
    pptdFileName: path.basename(project.manifestPath),
  };
}

function offlineSignature(value) {
  return `offline-bypass-${crypto.createHash('sha256').update(value, 'utf8').digest('hex').slice(0, 32)}`;
}

export async function exportPptx(source, options = {}) {
  const {
    output: outputOption = null,
    transition = 'fade',
    force = false,
    wasm = null,
    fontDirs = [],
    embedFonts = true,
    offline = false,
    quiet = false,
  } = options;

  checkNodeVersion();
  if (transition !== 'fade' && transition !== 'none') {
    throw new Error('transition must be fade or none');
  }
  const wasmPath = resolveWasm(wasm);
  const project = readProject(source);

  const output = outputOption
    ? path.resolve(outputOption)
    : path.join(path.dirname(project.manifestPath), `${path.basename(project.manifestPath, path.extname(project.manifestPath))}.pptx`);
  if (path.extname(output).toLowerCase() !== '.pptx') {
    throw new Error(`output must have a .pptx extension: ${output}`);
  }
  if (fs.existsSync(output) && !force) {
    throw new Error(`output already exists (pass --force to replace it): ${output}`);
  }

  for (const warning of project.warnings) {
    if (!quiet) log(`warning: ${warning}`);
  }

  const fonts = await prepareFonts(project, { fontDirs, embed: embedFonts, offline });
  for (const warning of fonts.warnings) {
    if (!quiet) log(`warning: ${warning}`);
  }

  const wasmProject = buildWasmProject(project);
  const { exportPPTDToPPTXBytes } = await loadWasmExporter(wasmPath);
  const icons = prepareIcons(wasmProject);
  const mediaRecords = [];
  const images = await resolveImages(wasmProject, path.dirname(project.manifestPath), mediaRecords, offline);
  await prepareAdvancedCharts(wasmProject, images);

  if (Object.keys(images).some((key) => key.startsWith('wasm-assets/chart-'))) {
    const outline = createSvgFontOutliner(fonts.outlines);
    for (const [key, image] of Object.entries(images)) {
      if (key.startsWith('wasm-assets/chart-')) {
        images[key] = new Uint8Array(Buffer.from(outline(Buffer.from(image).toString('utf8')), 'utf8'));
      }
    }
  }

  const { bytes, formulas } = exportWithMath(
    exportPPTDToPPTXBytes,
    wasmProject,
    {
      fonts: fonts.data,
      customFonts: [],
      images,
      fileName: path.basename(output),
      slideTransition: { effect: 'fade', speed: 'fast' },
      chartImages: [],
    },
    offlineSignature,
  );

  let pptxBuffer = Buffer.from(bytes);
  if (pptxBuffer[0] !== 0x50 || pptxBuffer[1] !== 0x4b) {
    throw new Error('WASM writer did not return a ZIP/PPTX payload');
  }

  pptxBuffer = patchFontBindings(pptxBuffer, fonts.bindings);
  const tablePatch = patchTableImages(pptxBuffer, project, mediaRecords);
  pptxBuffer = tablePatch.buffer;
  const transitionPatch = patchTransitions(pptxBuffer, transition);
  pptxBuffer = transitionPatch.buffer;
  const summary = verifyOutput(pptxBuffer, transition, project.pages.length);

  const warnings = [...project.warnings, ...fonts.warnings];
  if (mediaRecords.some((item) => /^https?:\/\//i.test(item.source))) {
    warnings.push(
      'PPTX embeds remote media, but the PPTD source still needs network access; localize media before self-contained delivery',
    );
  }

  fs.mkdirSync(path.dirname(output), { recursive: true });
  const tempPath = path.join(
    path.dirname(output),
    `.${path.basename(output, '.pptx')}-${crypto.randomUUID()}.tmp`,
  );
  try {
    fs.writeFileSync(tempPath, pptxBuffer);
    if (fs.existsSync(output) && !force) {
      throw new Error(`output already exists (pass --force to replace it): ${output}`);
    }
    fs.renameSync(tempPath, output);
  } finally {
    fs.rmSync(tempPath, { force: true });
  }

  return {
    ...summary,
    output,
    exporter: 'wasm',
    transitionPatchedSlides: transitionPatch.slideCount,
    icons,
    formulas,
    tableImageFills: tablePatch.count,
    fontFamilies: fonts.families,
    renderedQA: 'not_run',
    warnings,
  };
}

export function parseArgs(argv) {
  const args = {
    input: null,
    output: null,
    transition: 'fade',
    wasm: null,
    force: false,
    fontDirs: [],
    embedFonts: true,
    offline: false,
    help: false,
  };
  const values = [...argv];
  while (values.length) {
    const arg = values.shift();
    if (arg === '--help' || arg === '-h') args.help = true;
    else if (arg === '--output' || arg === '-o') args.output = values.shift() ?? throwMissing(arg);
    else if (arg === '--transition') args.transition = values.shift() ?? throwMissing(arg);
    else if (arg === '--wasm') args.wasm = values.shift() ?? throwMissing(arg);
    else if (arg === '--force') args.force = true;
    else if (arg === '--font-dir') args.fontDirs.push(values.shift() ?? throwMissing(arg));
    else if (arg === '--no-embed-fonts') args.embedFonts = false;
    else if (arg === '--offline') args.offline = true;
    else if (arg.startsWith('-')) throw new Error(`unknown option: ${arg}`);
    else if (!args.input) args.input = arg;
    else throw new Error(`unexpected positional argument: ${arg}`);
  }
  return args;
}

function throwMissing(flag) {
  throw new Error(`${flag} requires a value`);
}

function usage() {
  return [
    'Usage: node export.mjs <manifest.pptd|project directory> [options]',
    '',
    'Options:',
    '  -o, --output PATH      Output .pptx path (defaults beside manifest)',
    '  --transition MODE      fade (default) or none',
    '  --wasm PATH            Override the bundled WASM writer',
    '  --force                Replace an existing output',
    '  --font-dir PATH        Additional local TTF/TTC/OTF/EOT font directory (repeatable)',
    '  --no-embed-fonts       Write font names without embedding font data',
    '  --offline              Use only local media and bundled/local/cached fonts',
    '  -h, --help             Show this help message',
  ].join('\n');
}

export async function runCli(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  if (args.help) {
    console.log(usage());
    return 0;
  }
  if (!args.input) {
    throw new Error('input .pptd manifest or project directory is required');
  }
  const summary = await exportPptx(args.input, args);
  console.log(JSON.stringify(summary, null, 2));
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  runCli().then(
    (code) => { process.exitCode = code; },
    (error) => {
      console.error(`pptd export failed: ${error.message}`);
      process.exitCode = 1;
    },
  );
}
