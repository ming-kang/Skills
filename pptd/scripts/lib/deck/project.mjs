// Read a PPTD project from disk into one validated plain-data project object.
// Every consumer (CLI, exporter, validator) starts here; nothing else reads YAML.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { checkJsonValue, checkRelativePath, fail, isFiniteNumber, isPlainObject, requireString } from './contract.mjs';
import { checkPage, checkStyles } from './schema.mjs';
import { readYamlMapping } from './yaml.mjs';

const SKILL_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
let SHAPE_NAMES = new Set();
let ICON_NAMES = new Set();

function readText(relative) {
  return fs.readFileSync(path.join(SKILL_DIR, relative), 'utf8');
}

function loadNames() {
  if (SHAPE_NAMES.size) return;
  // Shape and icon names are data, not code: the reference tables and the icon catalog own them.
  const shapes = [...readText('references/shapes.md').matchAll(/^\| ([A-Za-z][A-Za-z0-9]*) \|/gm)].map((match) => match[1]);
  const catalog = JSON.parse(readText('assets/icons/fontawesome.json'));
  SHAPE_NAMES = new Set(shapes);
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

function checkTheme(manifest) {
  const theme = manifest.theme;
  if (theme !== undefined && !isPlainObject(theme)) fail('manifest.theme must be a mapping');
  for (const key of ['colors', 'textStyles', 'tableStyles']) {
    const config = theme?.[key] ?? {};
    if (!isPlainObject(config)) fail(`manifest.theme.${key} must be a mapping`);
    if (key !== 'colors' && !Object.values(config).every(isPlainObject)) fail(`manifest.theme.${key} entries must be mappings`);
  }
}

function checkCustomFonts(manifest, root) {
  if (!('customFonts' in manifest) || manifest.customFonts === undefined) return;
  if (!Array.isArray(manifest.customFonts)) fail('manifest.customFonts must be an array');
  const realRoot = fs.realpathSync(root);
  const rootPrefix = realRoot.endsWith(path.sep) ? realRoot : realRoot + path.sep;
  for (const [index, entry] of manifest.customFonts.entries()) {
    const label = `manifest.customFonts[${index}]`;
    if (!isPlainObject(entry)) fail(`${label} must be a mapping`);
    requireString(entry.family, `${label}.family`);
    const src = requireString(entry.src, `${label}.src`);
    if (/^https:\/\//i.test(src)) continue;
    if (/^[a-z]+:\/\//i.test(src)) fail(`${label}.src must be a relative path or Google Fonts HTTPS URL: ${src}`);
    const relative = checkRelativePath(src, `${label}.src`);
    const resolved = path.join(root, relative);
    if (!fs.existsSync(resolved) || !fs.statSync(resolved).isFile()) fail(`${label}.src missing local font: ${src}`);
    const realTarget = fs.realpathSync(resolved);
    if (realTarget !== realRoot && !realTarget.startsWith(rootPrefix)) {
      fail(`${label}.src escapes the PPTD directory: ${src}`);
    }
  }
}

/**
 * Read, validate and return the project. `pages[i].path` stays relative to the manifest;
 * `pages[i].data` is the page mapping. Media entries record the local files the export needs.
 */
export function readProject(source) {
  loadNames();
  const manifestPath = findManifest(source);
  const manifest = readYamlMapping(fs.readFileSync(manifestPath, 'utf8'), manifestPath);
  checkJsonValue(manifest, manifestPath);
  if (manifest.version !== 'v2') fail('only PPTD version: v2 is supported');
  const size = manifest.size;
  if (!Array.isArray(size) || size.length !== 2 || !size.every((item) => isFiniteNumber(item) && item > 0)) {
    fail('manifest.size must contain two positive finite numbers');
  }
  if ('title' in manifest && typeof manifest.title !== 'string') fail('manifest.title must be a string');
  checkTheme(manifest);
  checkStyles(manifest, 'manifest');
  const root = path.dirname(manifestPath);
  checkCustomFonts(manifest, root);
  const pages = manifest.pages;
  if (!Array.isArray(pages) || !pages.length) fail('manifest.pages must be a non-empty array');
  if (!pages.every((entry) => typeof entry === 'string' && entry.trim())) fail('every manifest.pages entry must be a non-empty string');
  if (new Set(pages).size !== pages.length) fail('manifest.pages contains duplicate paths');

  const media = new Map();
  const warnings = [];
  const project = [];
  const readPage = (entry) => {
    const relative = checkRelativePath(entry, 'manifest.pages entry');
    const pagePath = path.join(root, relative);
    if (!fs.existsSync(pagePath)) fail(`missing page file: ${entry}`);
    const data = readYamlMapping(fs.readFileSync(pagePath, 'utf8'), pagePath);
    checkPage(data, entry, { size, theme: manifest.theme ?? {}, shapeNames: SHAPE_NAMES, iconNames: ICON_NAMES, warnings, media });
    return data;
  };
  for (const entry of pages) {
    const data = readPage(entry);
    for (const item of media.values()) {
      if (!item.path) continue;
      const absolute = path.join(root, item.path);
      if (!fs.existsSync(absolute)) fail(`${item.label}: missing local image: ${item.path}`);
      const extension = path.extname(item.path).toLowerCase();
      if (!['.png', '.jpg', '.jpeg', '.gif', '.svg'].includes(extension)) fail(`${item.label}: unsupported local image type: ${item.path}`);
    }
    project.push({ path: entry, data });
  }
  return { manifestPath, manifest, pages: project, warnings: [...warnings], media: [...media.values()] };
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
