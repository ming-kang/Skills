#!/usr/bin/env node
// Public PPTD → PPTX export CLI (single-process Node.js runtime).
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { parseArgs as parseNodeArgs } from 'node:util';

import { isAdvancedChart } from './lib/deck/chart.mjs';
import { readContent } from './lib/deck/content.mjs';
import { buildWasmProject, readProject } from './lib/deck/project.mjs';
import { PptxPackage } from './lib/pptx/package.mjs';
import {
  patchFontBindings,
  patchTableImages,
  patchTransitions,
} from './lib/pptx/patch.mjs';
import { verifyOutput } from './lib/pptx/verify.mjs';
import { loadWasmExporter } from './lib/pptx/writer.mjs';
import { prepareIcons, resolveImages } from './lib/prepare/assets.mjs';
import { prepareAdvancedCharts } from './lib/prepare/charts.mjs';
import { prepareFonts } from './lib/prepare/fonts.mjs';

function log(message) {
  process.stderr.write(`[pptd] ${message}\n`);
}

/**
 * The writer ignores `Cell.textStyle`, so the referenced theme text style has to be
 * materialized onto the cell. Only keys the cell does not set are copied, which keeps
 * the documented precedence (cell fields > textStyle) intact.
 */
const CELL_TEXT_KEYS = ['color', 'fontSize', 'fontFamily', 'bold', 'italic', 'backgroundColor', 'lineHeight', 'lineHeightPx', 'letterSpacing', 'marginTop'];
function materializeCellTextStyles(content) {
  for (const { cells } of content.tables) {
    for (const { cell, style } of cells) {
      if (typeof cell.textStyle !== 'string') continue;
      for (const key of CELL_TEXT_KEYS) {
        if (!(key in cell) && style[key] !== undefined) cell[key] = style[key];
      }
    }
  }
}

/** Manifest document properties; the writer only understands these five keys. */
function writerMetadata(project) {
  const metadata = { ...(project.metadata ?? {}) };
  if (metadata.title === undefined && typeof project.title === 'string' && project.title) {
    metadata.title = project.title;
  }
  return Object.keys(metadata).length ? metadata : undefined;
}

export function checkNodeVersion(version = process.versions.node) {
  const major = Number.parseInt(String(version).replace(/^v/i, '').split('.')[0], 10);
  if (!Number.isFinite(major) || major < 26) {
    throw new Error(`Node.js 26+ is required; found ${version}`);
  }
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
  const sourceProject = readProject(source);

  const output = outputOption
    ? path.resolve(outputOption)
    : path.join(path.dirname(sourceProject.manifestPath), `${path.basename(sourceProject.manifestPath, path.extname(sourceProject.manifestPath))}.pptx`);
  if (path.extname(output).toLowerCase() !== '.pptx') {
    throw new Error(`output must have a .pptx extension: ${output}`);
  }
  if (fs.existsSync(output) && !force) {
    throw new Error(`output already exists (pass --force to replace it): ${output}`);
  }

  for (const warning of sourceProject.warnings) {
    if (!quiet) log(`warning: ${warning}`);
  }

  // Build one isolated, normalized working project used across all prepare and patch passes.
  const projectRoot = path.dirname(sourceProject.manifestPath);
  const wasmProject = buildWasmProject(sourceProject);
  const { exportPPTDToPPTXBytes } = await loadWasmExporter(wasm);
  const content = readContent(wasmProject);
  materializeCellTextStyles(content);
  // Font and image preparation mutate disjoint fields; starting both lets remote
  // downloads overlap local font analysis/embedding instead of serializing them.
  const fontsPromise = prepareFonts(wasmProject, content, { projectRoot, fontDirs, embed: embedFonts, offline });
  const mediaByKey = new Map();
  const imagesPromise = resolveImages(wasmProject, projectRoot, mediaByKey, offline);
  const [fonts, images] = await Promise.all([fontsPromise, imagesPromise]);
  for (const warning of fonts.warnings) {
    if (!quiet) log(`warning: ${warning}`);
  }

  const icons = prepareIcons(wasmProject);

  let outlineText = null;
  if (wasmProject.pages.some((page) => page.elements.some(isAdvancedChart))) {
    const { createSvgFontOutliner } = await import('./lib/prepare/svg_text.mjs');
    outlineText = createSvgFontOutliner(fonts.outlines);
  }
  await prepareAdvancedCharts(wasmProject, images, { outlineText });

  const writerOptions = {
    fonts: fonts.data,
    customFonts: [],
    images,
    fileName: path.basename(output),
    slideTransition: { effect: 'fade', speed: 'fast' },
    chartImages: [],
    metadata: writerMetadata(sourceProject),
  };

  const math = content.formulas.length
    ? (await import('./lib/prepare/formulas.mjs')).createMathBridge(content.formulas)
    : null;
  const unexpectedMath = [];
  const bytes = exportPPTDToPPTXBytes(
    wasmProject,
    {
      ...writerOptions,
      mathLoader: math ? math.mathLoader : (latex) => {
        unexpectedMath.push(latex);
        return null;
      },
    },
  );
  if (unexpectedMath.length) throw new Error(`writer requested an unexpected formula: ${JSON.stringify(unexpectedMath[0])}`);
  const formulas = math ? math.assertComplete() : 0;

  let pptxBuffer = Buffer.from(bytes.buffer, bytes.byteOffset, bytes.byteLength);

  // Single-pass archive postprocessing (fonts + table image fills + slide transitions).
  const pkg = PptxPackage.open(pptxBuffer);
  patchFontBindings(pkg, fonts.bindings);
  const tableImageFills = patchTableImages(pkg, content.tables, mediaByKey);
  const transitionPatchedSlides = patchTransitions(pkg, transition);
  pptxBuffer = pkg.toBuffer();

  const summary = verifyOutput(pptxBuffer, transition, wasmProject.pages.length);

  const warnings = [...sourceProject.warnings, ...fonts.warnings];
  if ([...mediaByKey.values()].some((item) => item.remote)) {
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
    transitionPatchedSlides,
    icons,
    formulas,
    tableImageFills,
    fontFamilies: fonts.families,
    renderedQA: 'not_run',
    warnings,
  };
}

export function parseArgs(argv) {
  const { values, positionals } = parseNodeArgs({
    args: argv, allowPositionals: true,
    options: {
      output: { type: 'string', short: 'o' },
      transition: { type: 'string', default: 'fade' },
      wasm: { type: 'string' },
      force: { type: 'boolean', default: false },
      'font-dir': { type: 'string', multiple: true },
      'no-embed-fonts': { type: 'boolean', default: false },
      offline: { type: 'boolean', default: false },
      help: { type: 'boolean', short: 'h', default: false },
    },
  });
  if (positionals.length > 1) throw new Error(`unexpected positional argument: ${positionals[1]}`);
  return {
    input: positionals[0] ?? null, output: values.output, transition: values.transition,
    wasm: values.wasm, force: values.force, fontDirs: values['font-dir'] ?? [],
    embedFonts: !values['no-embed-fonts'], offline: values.offline, help: values.help,
  };
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

if (process.argv[1] && path.resolve(process.argv[1]) === import.meta.filename) {
  runCli().then(
    (code) => { process.exitCode = code; },
    (error) => {
      console.error(`pptd export failed: ${error.message}`);
      process.exitCode = 1;
    },
  );
}
