// Read and validate a PPTD v2 project from disk into one plain-data project object.
// Every consumer (CLI, exporter, validator) starts here; nothing else reads YAML.

import fs from 'node:fs';
import path from 'node:path';

import {
  checkContainedFile,
  checkRelativePath,
  fail,
  isPlainObject,
  normalizeElement,
  requireString,
} from './contract.mjs';
import { readCatalog } from '../core/catalog.mjs';
import { resolveThemeColor } from '../core/color.mjs';
import { dataUrlBytes, imageInfo } from '../core/media.mjs';
import { readContent } from './content.mjs';
import { checkPage } from './schema.mjs';
import { checkColor, checkStyle } from './style.mjs';
import { checkTableStyleConfig } from './table.mjs';
import { readYamlMapping } from './yaml.mjs';

function findManifest(source) {
  const target = path.resolve(source);
  if (fs.existsSync(target) && fs.statSync(target).isFile()) {
    if (path.extname(target).toLowerCase() !== '.pptd') fail(`input must be a .pptd file or project directory: ${target}`);
    return target;
  }
  if (!fs.existsSync(target)) fail(`input does not exist: ${target}`);
  const manifests = fs.readdirSync(target, { withFileTypes: true, recursive: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.pptd'))
    .map((entry) => path.join(entry.parentPath, entry.name))
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
    resolveThemeColor(value, colors, `manifest.theme.colors.${token}`);
  }
  for (const [name, style] of Object.entries(theme?.textStyles ?? {})) {
    checkStyle(style, `manifest.theme.textStyles.${name}`, colors);
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

/** Document properties written to docProps; unknown keys are silently dropped by the writer. */
const METADATA_KEYS = ['title', 'author', 'company', 'subject', 'copyright'];
function checkMetadata(manifest) {
  const metadata = manifest.metadata;
  if (metadata === undefined) return;
  if (!isPlainObject(metadata)) fail('manifest.metadata must be a mapping');
  for (const [key, value] of Object.entries(metadata)) {
    if (!METADATA_KEYS.includes(key)) {
      fail(`manifest.metadata.${key} is not a supported document property; supported: ${METADATA_KEYS.join(', ')}`);
    }
    requireString(value, `manifest.metadata.${key}`);
  }
}

/**
 * Read, validate and return the canonical DeckIR project.
 * `pages[i].pagePath` stays relative to the manifest (POSIX slashes) and elements are normalized.
 */
export function readProject(source) {
  const manifestPath = findManifest(source);
  const manifest = readYamlMapping(fs.readFileSync(manifestPath, 'utf8'), manifestPath);
  if (manifest.version !== 'v2') fail('only PPTD version: v2 is supported');
  const size = manifest.size;
  if (!Array.isArray(size) || size.length !== 2 || !size.every((item) => Number.isFinite(item) && item > 0)) {
    fail('manifest.size must contain two positive finite numbers');
  }
  if ('title' in manifest && typeof manifest.title !== 'string') fail('manifest.title must be a string');
  checkMetadata(manifest);

  const root = path.dirname(manifestPath);
  const realRoot = fs.realpathSync(root);
  const media = new Map();
  const dataImages = [];
  const warnings = [];
  const theme = manifest.theme ?? {};

  checkTheme(manifest, { theme, media, dataImages });
  checkCustomFonts(manifest, root, realRoot);

  const pages = manifest.pages;
  if (!Array.isArray(pages) || !pages.length) fail('manifest.pages must be a non-empty array');
  if (!pages.every((entry) => typeof entry === 'string' && entry.trim())) fail('every manifest.pages entry must be a non-empty string');
  if (new Set(pages).size !== pages.length) fail('manifest.pages contains duplicate paths');

  const projectPages = [];
  for (const entry of pages) {
    const relative = checkRelativePath(entry, 'manifest.pages entry');
    const pagePath = checkContainedFile(root, realRoot, relative, 'manifest.pages entry', `missing page file: ${entry}`);
    const data = readYamlMapping(fs.readFileSync(pagePath, 'utf8'), pagePath);
    checkPage(data, entry, { size, theme, shapes: readCatalog('shapes.json'), warnings, media, dataImages });
    projectPages.push({
      ...data,
      pagePath: String(entry).replaceAll('\\', '/'),
      elements: data.elements.map(normalizeElement),
    });
  }

  for (const item of media.values()) {
    if (!item.path) continue;
    checkContainedFile(root, realRoot, item.path, item.label, `${item.label}: missing local image: ${item.path}`);
  }
  for (const item of dataImages) {
    imageInfo(dataUrlBytes(item.src), item.label);
  }

  return { ...manifest, manifestPath, pages: projectPages, warnings, media: [...media.values()] };
}

/** Build an isolated, mutable WASM writer project from a canonical DeckIR project. */
export function buildWasmProject(project) {
  const { manifestPath, warnings, media, ...deck } = project;
  return structuredClone({ ...deck, pptdFileName: path.basename(manifestPath) });
}

/** Full semantic + local-asset validation used by `validate.mjs`. */
export async function validateProject(source, { checkFonts = false, fontDirs = [], offline = false } = {}) {
  const project = readProject(source);
  const root = path.dirname(project.manifestPath);

  if (project.media.length) {
    for (const item of project.media) {
      if (!item.path) continue;
      const bytes = fs.readFileSync(path.join(root, item.path));
      imageInfo(bytes, `${item.label} (${item.path})`);
    }
  }

  // Parse the same content plan as export, without mutating any source holder.
  const content = readContent(project);
  if (content.formulas.length) {
    const { validateFormulas } = await import('../prepare/formulas.mjs');
    validateFormulas(content.formulas);
  }

  if (checkFonts) {
    const { checkFonts: runFontCheck } = await import('../prepare/fonts.mjs');
    const fonts = await runFontCheck(project, content, { projectRoot: root, fontDirs, offline });
    project.warnings.push(...fonts.warnings);
  } else {
    const localFonts = (project.customFonts ?? []).filter((f) => !/^https:\/\//i.test(f.src));
    if (localFonts.length) {
      const { checkCustomFont } = await import('../prepare/font_data.mjs');
      for (const entry of localFonts) checkCustomFont(path.join(root, entry.src), entry.family);
    }
  }

  return project;
}

export function projectSummary(project) {
  return {
    valid: true,
    manifest: project.manifestPath,
    title: project.title,
    slides: project.pages.length,
    elements: project.pages.reduce((sum, page) => sum + page.elements.length, 0),
    warnings: project.warnings,
  };
}
