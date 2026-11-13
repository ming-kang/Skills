// Read and validate a PPTD v2 project from disk into one plain-data project object.
// Every consumer (CLI, exporter, validator) starts here; nothing else reads YAML.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  checkContainedFile,
  checkJsonValue,
  checkRelativePath,
  fail,
  isFiniteNumber,
  isPlainObject,
  requireString,
} from './contract.mjs';
import {
  checkColor,
  checkPage,
  checkStyles,
  checkTableStyleConfig,
  IMAGE_EXTENSIONS,
} from './schema.mjs';
import { readYamlMapping } from './yaml.mjs';

const SKILL_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
let SHAPES = null;
let ICON_NAMES = new Set();

function readText(relative) {
  return fs.readFileSync(path.join(SKILL_DIR, relative), 'utf8');
}

function loadAssets() {
  if (SHAPES) return;
  SHAPES = JSON.parse(readText('assets/shapes.json'));
  const catalog = JSON.parse(readText('assets/icons/fontawesome.json'));
  ICON_NAMES = new Set([...Object.keys(catalog.icons), ...Object.keys(catalog.aliases)]);
}

export function findManifest(source) {
  const target = path.resolve(source);
  if (fs.existsSync(target) && fs.statSync(target).isFile()) {
    if (path.extname(target).toLowerCase() !== '.pptd') fail(`input must be a .pptd file or project directory: ${target}`);
    return target;
  }
  if (!fs.existsSync(target)) fail(`input does not exist: ${target}`);
  const manifests = fs.readdirSync(target, { withFileTypes: true, recursive: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.pptd'))
    .map((entry) => path.join(entry.parentPath ?? entry.path, entry.name))
    .sort();
  if (!manifests.length) fail(`no .pptd manifest found under: ${target}`);
  if (manifests.length > 1) {
    const choices = manifests.slice(0, 20).map((manifest) => `  ${manifest}`).join('\n');
    fail(`multiple .pptd manifests found; pass one manifest explicitly:\n${choices}`);
  }
  return manifests[0];
}

function checkTheme(manifest, context) {
  const theme = manifest.theme;
  if (theme !== undefined && !isPlainObject(theme)) fail('manifest.theme must be a mapping');
  for (const key of ['colors', 'textStyles', 'tableStyles']) {
    const config = theme?.[key] ?? {};
    if (!isPlainObject(config)) fail(`manifest.theme.${key} must be a mapping`);
    if (key !== 'colors' && !Object.values(config).every(isPlainObject)) {
      fail(`manifest.theme.${key} entries must be mappings`);
    }
  }
  const colors = theme?.colors ?? {};
  for (const [token, value] of Object.entries(colors)) {
    checkColor(value, `manifest.theme.colors.${token}`, colors);
    const visited = new Set([token]);
    let current = value;
    while (typeof current === 'string' && current.startsWith('$')) {
      const next = current.slice(1);
      if (visited.has(next)) fail(`manifest.theme.colors.${token} contains a cyclic color reference`);
      visited.add(next);
      current = colors[next];
    }
  }
  for (const [name, config] of Object.entries(theme?.tableStyles ?? {})) {
    checkTableStyleConfig(config, `manifest.theme.tableStyles.${name}`, context);
  }
}

function checkCustomFonts(manifest, root, realRoot) {
  if (!('customFonts' in manifest) || manifest.customFonts === undefined) return;
  if (!Array.isArray(manifest.customFonts)) fail('manifest.customFonts must be an array');
  for (const [index, entry] of manifest.customFonts.entries()) {
    const label = `manifest.customFonts[${index}]`;
    if (!isPlainObject(entry)) fail(`${label} must be a mapping`);
    requireString(entry.family, `${label}.family`);
    const src = requireString(entry.src, `${label}.src`);
    if (/^https:\/\//i.test(src)) continue;
    if (/^[a-z]+:\/\//i.test(src)) fail(`${label}.src must be a relative path or Google Fonts HTTPS URL: ${src}`);
    const relative = checkRelativePath(src, `${label}.src`);
    checkContainedFile(root, realRoot, relative, `${label}.src`, `${label}.src missing local font: ${src}`);
  }
}

/**
 * Read, validate and return the project. `pages[i].path` stays relative to the manifest;
 * `pages[i].data` is the page mapping. Media entries record the local files the export needs.
 */
export function readProject(source) {
  loadAssets();
  const manifestPath = findManifest(source);
  const manifest = readYamlMapping(fs.readFileSync(manifestPath, 'utf8'), manifestPath);
  checkJsonValue(manifest, manifestPath);
  if (manifest.version !== 'v2') fail('only PPTD version: v2 is supported');
  const size = manifest.size;
  if (!Array.isArray(size) || size.length !== 2 || !size.every((item) => isFiniteNumber(item) && item > 0)) {
    fail('manifest.size must contain two positive finite numbers');
  }
  if ('title' in manifest && typeof manifest.title !== 'string') fail('manifest.title must be a string');

  const root = path.dirname(manifestPath);
  const realRoot = fs.realpathSync(root);
  const media = new Map();
  const warnings = [];
  const theme = manifest.theme ?? {};

  checkTheme(manifest, { theme, media });
  checkStyles(manifest, 'manifest', theme.colors ?? {});
  checkCustomFonts(manifest, root, realRoot);

  const pages = manifest.pages;
  if (!Array.isArray(pages) || !pages.length) fail('manifest.pages must be a non-empty array');
  if (!pages.every((entry) => typeof entry === 'string' && entry.trim())) fail('every manifest.pages entry must be a non-empty string');
  if (new Set(pages).size !== pages.length) fail('manifest.pages contains duplicate paths');

  const project = [];
  for (const entry of pages) {
    const relative = checkRelativePath(entry, 'manifest.pages entry');
    const pagePath = checkContainedFile(root, realRoot, relative, 'manifest.pages entry', `missing page file: ${entry}`);
    const data = readYamlMapping(fs.readFileSync(pagePath, 'utf8'), pagePath);
    checkPage(data, entry, { size, theme, shapes: SHAPES, iconNames: ICON_NAMES, warnings, media });
    project.push({ path: entry, data });
  }

  for (const item of media.values()) {
    if (!item.path) continue;
    checkContainedFile(root, realRoot, item.path, item.label, `${item.label}: missing local image: ${item.path}`);
    const extension = path.extname(item.path).toLowerCase();
    if (!IMAGE_EXTENSIONS.has(extension)) fail(`${item.label}: unsupported local image type: ${item.path}`);
  }

  return { manifestPath, manifest, pages: project, warnings: [...warnings], media: [...media.values()] };
}

/** Full semantic + local-asset validation used by `validate.mjs`. */
export async function validateProject(source) {
  const project = readProject(source);
  const root = path.dirname(project.manifestPath);

  if (project.media.length) {
    const { imageInfo } = await import('../prepare/media.mjs');
    for (const item of project.media) {
      if (!item.path) continue;
      const bytes = fs.readFileSync(path.join(root, item.path));
      imageInfo(bytes, `${item.label} (${item.path})`);
    }
  }

  const hasMath = project.pages.some(({ data }) => data.elements.some((el) => {
    if (el.elementType === 'text') return /\\[()]|data-math/.test(el.content?.text ?? '');
    if (el.elementType === 'table') {
      return el.rows.some((row) => row.some((cell) => /\\[()]|data-math/.test(cell.text ?? '')));
    }
    return false;
  }));
  if (hasMath) {
    const { validateFormulas } = await import('../prepare/formulas.mjs');
    validateFormulas(project.pages);
  }

  const localFonts = (project.manifest.customFonts ?? []).filter((f) => !/^https:\/\//i.test(f.src));
  if (localFonts.length) {
    const { readFontFaces } = await import('../prepare/font_data.mjs');
    const norm = (name) => String(name).replace(/[\s_-]+/g, '').toLowerCase();
    for (const entry of localFonts) {
      const data = fs.readFileSync(path.join(root, checkRelativePath(entry.src, 'customFonts.src')));
      const faces = readFontFaces(data);
      const matches = faces.some((face) => norm(entry.family) === norm(face.family) || face.aliases.some((alias) => norm(alias) === norm(entry.family)));
      if (!matches) {
        fail(`custom font family does not match its file: ${entry.family} / ${entry.src}`);
      }
    }
  }

  return project;
}

export function projectSummary(project) {
  return {
    valid: true,
    manifest: project.manifestPath,
    title: project.manifest.title,
    slides: project.pages.length,
    elements: project.pages.reduce((sum, page) => sum + page.data.elements.length, 0),
    warnings: project.warnings,
  };
}

export { requireString };
