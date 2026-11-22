// Font resolution, Google Fonts caching, rich-text inline font rewriting and EOT embedding.
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { create as createFont } from '../../../assets/vendor/fontkit.mjs';
import { readCatalog } from '../core/catalog.mjs';
import { parseCss, splitCss } from '../core/css.mjs';
import { splitFormulas, stripFormulas } from '../core/markup.mjs';
import { fetchBounded } from '../core/net.mjs';
import { walkObjects } from '../core/walk.mjs';
import {
  EAST_ASIAN,
  embeddingAllowed,
  extractEotSfnt,
  extractTtcFace,
  fontSlot,
  matchFontFamily,
  normalizeFontKey as key,
  readFontBytes,
  readFontFaces,
  readFontFacesFromFile,
  ttfToEot,
} from './font_data.mjs';

const SKILL_DIR = path.resolve(import.meta.dirname, '..', '..', '..');
const ASSETS = path.join(SKILL_DIR, 'assets', 'fonts');
const FONT_SUFFIXES = new Set(['.ttf', '.ttc', '.otf', '.eot', '.fntdata']);
const FONT_USER_AGENT = 'Mozilla/4.0 (compatible; pptd-font-loader/1)';
const LOCAL_ALIASES = {
  '微软雅黑': 'Microsoft YaHei',
  '微软正黑体': 'Microsoft JhengHei',
  '宋体': 'SimSun',
  '黑体': 'SimHei',
};
const ALLOWED_GOOGLE_HOSTS = new Set(['fonts.googleapis.com', 'fonts.gstatic.com']);
const GOOGLE_WEIGHT_BOLD = new Map([['400', false], ['normal', false], ['700', true], ['bold', true]]);
/** Mirror the writer's own emphasis rules: `bold`/`bolder`/≥600 is bold, `oblique` is italic. */
const NUMBER = /^[+-]?\d+(?:\.\d+)?$/;
const FONT_STYLE_ITALIC = new Set(['italic', 'oblique']);
const BOLD_FONT_WEIGHTS = new Set(['bold', 'bolder']);
const isBoldWeight = (value) => BOLD_FONT_WEIGHTS.has(value) || (NUMBER.test(value) && Number(value) >= 600);
/** Chars excluded from glyph-coverage checks: layout whitespace and controls are not glyphs. */
const COVERAGE_SKIP = /[\p{White_Space}\p{Default_Ignorable_Code_Point}\p{Control}]/u;
const GRAPHEMES = new Intl.Segmenter('und', { granularity: 'grapheme' });

const sha256 = (value) => crypto.createHash('sha256').update(value).digest('hex');
const compareKeys = ([a], [b]) => (a < b ? -1 : a > b ? 1 : 0);

function writeAtomic(filePath, data) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const temp = `${filePath}.${process.pid}.${crypto.randomUUID()}.tmp`;
  try {
    fs.writeFileSync(temp, data);
    fs.renameSync(temp, filePath);
  } finally {
    fs.rmSync(temp, { force: true });
  }
}

function cacheDir() {
  const base = process.env.PPTD_FONT_CACHE
    ? process.env.PPTD_FONT_CACHE.replace(/^~(?=$|[\\/])/, os.homedir())
    : (process.env.LOCALAPPDATA || process.env.XDG_CACHE_HOME || path.join(os.homedir(), '.cache'));
  return path.join(path.resolve(base), 'pptd', 'fonts');
}

function assertGoogleUrl(rawUrl) {
  let parsed;
  try {
    parsed = new URL(rawUrl);
  } catch {
    throw new Error(`invalid custom font URL: ${rawUrl}`);
  }
  if (parsed.protocol !== 'https:' || !ALLOWED_GOOGLE_HOSTS.has(parsed.hostname)) {
    throw new Error('custom font URLs must use Google Fonts HTTPS endpoints');
  }
  return parsed;
}

async function fetchGoogle(url) {
  assertGoogleUrl(url);
  return fetchBounded(url, {
    label: 'custom font',
    headers: { 'User-Agent': FONT_USER_AGENT },
    validateUrl: (next) => {
      if (next.protocol !== 'https:' || !ALLOWED_GOOGLE_HOSTS.has(next.hostname)) {
        throw new Error('custom font download redirected outside Google Fonts');
      }
    },
  });
}

function validCachedFont(filePath) {
  if (!fs.existsSync(filePath)) return false;
  try {
    readFontFacesFromFile(filePath);
    return true;
  } catch {
    return false;
  }
}

function readCachedGooglePaths(cache, url) {
  const manifestPath = path.join(cache, `${sha256(`${url}\0${FONT_USER_AGENT}`)}.json`);
  if (fs.existsSync(manifestPath)) {
    try {
      const { files } = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
      if (Array.isArray(files) && files.length && files.every((name) => typeof name === 'string' && !/[\\/]/.test(name))) {
        const paths = files.map((name) => path.join(cache, name));
        if (paths.every(validCachedFont)) return paths;
      }
    } catch {
      // Re-fetch if cached manifest or payload is corrupt.
    }
  }
  const legacyPath = path.join(cache, `${sha256(url + FONT_USER_AGENT)}.ttf`);
  return validCachedFont(legacyPath) ? [legacyPath] : null;
}

/**
 * Resolve one Google Fonts CSS/CSS2 URL into one or more cached static RIBBI TrueType files.
 * Complete `400`/`700` `normal`/`italic` faces are accepted and downloaded in parallel;
 * `text=` requests, `unicode-range` subsets, duplicate slots and non-RIBBI weights fail closed.
 */
async function resolveGoogleFont(url, family, offline) {
  const parsed = assertGoogleUrl(url);
  if (parsed.hostname !== 'fonts.googleapis.com' || (parsed.pathname !== '/css' && parsed.pathname !== '/css2')) {
    throw new Error('customFonts.src must be a local font or a Google Fonts CSS URL');
  }
  if (parsed.searchParams.has('text')) {
    throw new Error('subset-only Google Fonts text= requests cannot provide complete editable fonts');
  }
  const cache = cacheDir();
  const cached = readCachedGooglePaths(cache, url);
  if (cached) return cached;
  if (offline) throw new Error(`custom font is not cached for offline use: ${family}`);

  const css = (await fetchGoogle(url)).toString('utf8').replace(/\/\*[\s\S]*?\*\//g, '');
  const bySlot = new Map();
  for (const [, block] of css.matchAll(/@font-face\s*\{([^}]+)\}/g)) {
    const props = Object.fromEntries(parseCss(block));
    const name = (props['font-family'] ?? '').replace(/^['"]+|['"]+$/g, '');
    const srcMatch = /url\(([^)]+)\)/.exec(props.src ?? '');
    if (key(name) !== key(family) || !srcMatch) continue;
    if ('unicode-range' in props) {
      throw new Error(`Google Fonts returned subset-only font rules: ${family}`);
    }
    const style = (props['font-style'] ?? 'normal').trim().toLowerCase();
    const weight = (props['font-weight'] ?? '400').trim().toLowerCase();
    const bold = GOOGLE_WEIGHT_BOLD.get(weight);
    const italic = style === 'normal' ? false : FONT_STYLE_ITALIC.has(style) ? true : null;
    if (bold === undefined || italic === null) {
      throw new Error(`Google Fonts rule for ${family} has unsupported style/weight (${style} ${weight}); request RIBBI faces (normal/italic, 400/700)`);
    }
    const slot = fontSlot(bold, italic);
    if (bySlot.has(slot)) {
      throw new Error(`Google Fonts returned multiple ${slot} rules for ${family}`);
    }
    bySlot.set(slot, srcMatch[1].trim().replace(/^['"]+|['"]+$/g, ''));
  }
  if (!bySlot.size) {
    throw new Error(`Google Fonts must provide one or more complete RIBBI TTF faces for ${family}`);
  }

  const urls = [...bySlot.entries()].sort(compareKeys).map(([, ttfUrl]) => ttfUrl);
  const files = await Promise.all(urls.map(async (ttfUrl) => {
    const fileName = `${sha256(ttfUrl)}.ttf`;
    const filePath = path.join(cache, fileName);
    if (!validCachedFont(filePath)) {
      const data = await fetchGoogle(ttfUrl);
      readFontFaces(data);
      writeAtomic(filePath, data);
    }
    return fileName;
  }));

  const manifestPath = path.join(cache, `${sha256(`${url}\0${FONT_USER_AGENT}`)}.json`);
  writeAtomic(manifestPath, JSON.stringify({ files }));
  return files.map((name) => path.join(cache, name));
}

function systemFontDirs() {
  if (process.platform === 'win32') {
    return [
      path.join(process.env.WINDIR || 'C:/Windows', 'Fonts'),
      path.join(process.env.LOCALAPPDATA || '', 'Microsoft', 'Windows', 'Fonts'),
    ].filter(Boolean);
  }
  if (process.platform === 'darwin') {
    return ['/System/Library/Fonts', '/Library/Fonts', path.join(os.homedir(), 'Library', 'Fonts')];
  }
  return [
    '/usr/share/fonts',
    '/usr/local/share/fonts',
    path.join(os.homedir(), '.fonts'),
    path.join(process.env.XDG_DATA_HOME || path.join(os.homedir(), '.local', 'share'), 'fonts'),
  ];
}

function addGlyphs(map, mapKey, codepoints) {
  let set = map.get(mapKey);
  if (!set) map.set(mapKey, (set = new Set()));
  for (const cp of codepoints) set.add(cp);
}

function formatCodePoints(cps) {
  const list = [...cps];
  const shown = list.slice(0, 8)
    .map((cp) => `'${String.fromCodePoint(cp)}' (U+${cp.toString(16).toUpperCase()})`)
    .join(', ');
  return `${shown}${list.length > 8 ? ` (+${list.length - 8} more)` : ''}`;
}

/** Return missing non-skip codepoints in `segment`, or `null` if `font` cannot be inspected. */
function missingCodePoints(font, segment) {
  if (!font || typeof font.hasGlyphForCodePoint !== 'function') return null;
  const missing = [];
  for (const char of segment) {
    if (COVERAGE_SKIP.test(char)) continue;
    const cp = char.codePointAt(0);
    if (!font.hasGlyphForCodePoint(cp)) missing.push(cp);
  }
  return missing;
}

class FontStore {
  constructor(fontDirs) {
    this.catalog = readCatalog('fonts/catalog.json');
    this.faces = new Map();
    this.aliases = new Map(Object.entries({ ...this.catalog.aliases, ...LOCAL_ALIASES }).map(([alias, target]) => [key(alias), target]));
    this.scannedDirs = new Set();
    this.scanned = false;
    this.warnings = [];
    this.needed = new Map();
    this.resolved = new Map();
    this.rerouted = new Map();
    this.missing = new Map();
    this.fileBytes = new Map();
    this.containers = new WeakMap();
    this.fontCache = new Map();
    for (const entry of this.catalog.faces) this.index({ ...entry, path: path.join(ASSETS, entry.src), priority: 1 });
    for (const raw of fontDirs) {
      const dir = path.resolve(String(raw).replace(/^~(?=$|[\\/])/, os.homedir()));
      if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) throw new Error(`font directory does not exist: ${dir}`);
      this.scan(dir, 0);
    }
  }

  index(entry) {
    for (const name of new Set([entry.family, ...(entry.aliases ?? [])].map(key))) {
      if (!this.faces.has(name)) this.faces.set(name, []);
      const faces = this.faces.get(name);
      if (!faces.includes(entry)) faces.push(entry);
    }
    this.resolved.clear();
  }

  warn(message) {
    if (!this.warnings.includes(message)) this.warnings.push(message);
  }

  /** Lazily parse a face for glyph coverage, sharing parsed containers across TTC faces. */
  faceFont(entry) {
    const cacheKey = `${entry.path}\0${entry.face}`;
    if (!this.fontCache.has(cacheKey)) {
      let font = null;
      try {
        const raw = this.readBytes(entry.path);
        let container = this.containers.get(raw);
        if (!container) {
          container = createFont(entry.eot ? extractEotSfnt(raw) : raw);
          this.containers.set(raw, container);
        }
        font = container.type === 'TTC' ? container.fonts[entry.face] : entry.face === 0 ? container : null;
      } catch {
        font = null;
      }
      this.fontCache.set(cacheKey, font);
    }
    return this.fontCache.get(cacheKey);
  }

  add(filePath, priority, family = null) {
    try {
      const faces = readFontFacesFromFile(filePath);
      if (family && !matchFontFamily(faces, family)) throw new Error(`custom font family does not match its file: ${family} / ${path.basename(filePath)}`);
      for (const face of faces) this.index({ ...face, path: filePath, priority });
    } catch (error) {
      if (family) throw new Error(`cannot load custom font ${family}: ${error.message}`);
    }
  }

  scan(directory, priority) {
    try {
      const real = fs.realpathSync(directory);
      if (this.scannedDirs.has(real)) return;
      this.scannedDirs.add(real);
      const files = fs.readdirSync(real, { withFileTypes: true, recursive: true })
        .filter((entry) => entry.isFile() && FONT_SUFFIXES.has(path.extname(entry.name).toLowerCase()))
        .map((entry) => path.join(entry.parentPath, entry.name)).sort();
      for (const file of files) this.add(file, priority);
    } catch {
      // Missing/inaccessible optional system font directories are not export failures.
    }
  }

  readBytes(filePath) {
    if (!this.fileBytes.has(filePath)) this.fileBytes.set(filePath, readFontBytes(filePath));
    return this.fileBytes.get(filePath);
  }

  /** Select the winning face without committing it to `needed` or emitting warnings. */
  pick(rawName, requested, eastAsian = false) {
    const name = this.aliases.get(key(rawName)) ?? rawName;
    let available = this.faces.get(key(name)) ?? [];
    if (!available.length && !this.scanned) {
      this.scanned = true;
      for (const dir of systemFontDirs()) this.scan(dir, 2);
      available = this.faces.get(key(name)) ?? [];
    }
    if (!available.length) {
      const fallback = this.catalog.fallbacks[eastAsian ? 'ea' : 'latin'];
      if (key(name) === key(fallback)) throw new Error(`bundled fallback font is missing: ${fallback}`);
      return { ...this.pick(fallback, requested, eastAsian), substitutedFrom: name };
    }
    // Explicit/bundled faces stay ahead of lazily-scanned system fonts; within a tier,
    // an exact style match (then regular as the safe synthesis base) beats source priority
    // so a lone custom bold pairs with a bundled regular instead of shadowing it.
    const entry = available.toSorted((a, b) =>
      Number(a.priority >= 2) - Number(b.priority >= 2) ||
      Number(a.slot !== requested) - Number(b.slot !== requested) ||
      Number(a.slot !== 'regular') - Number(b.slot !== 'regular') ||
      a.priority - b.priority)[0];
    if (entry.face === undefined) {
      Object.assign(entry, readFontFaces(this.readBytes(entry.path))[0]);
      this.index(entry);
    }
    return { entry, name, substitutedFrom: null };
  }

  resolve(rawName, requested, eastAsian = false) {
    const name = this.aliases.get(key(rawName)) ?? rawName;
    const cacheKey = `${key(name)}\0${requested}\0${eastAsian}`;
    if (this.resolved.has(cacheKey)) return this.resolved.get(cacheKey);
    const picked = this.pick(rawName, requested, eastAsian);
    if (picked.substitutedFrom) {
      this.warn(`font '${picked.substitutedFrom}' is unavailable; exported text uses '${picked.name}'`);
    }
    const { entry } = picked;
    if (entry.slot !== requested) {
      this.warn(`font '${picked.name}' has no ${requested} face; presentation software must synthesize that style`);
    }
    this.needed.set(`${entry.family}\0${entry.slot}`, entry);
    this.resolved.set(cacheKey, entry);
    return entry;
  }

  family(value, bold = false, italic = false, text = '') {
    const requested = fontSlot(bold, italic);
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      return Object.fromEntries(Object.entries(value).map(([script, name]) => [script, this.resolve(name, requested, script === 'ea').family]));
    }
    let list = value || 'MiSans';
    // The private rich-text format also accepts a quoted combined Latin/CJK pair.
    const quote = list[0];
    if ((quote === '"' || quote === "'") && list.at(-1) === quote && !list.slice(1, -1).includes(quote)) list = list.slice(1, -1);
    const parts = splitCss(list, ',').map((part) => part.trim().replace(/^['"]+|['"]+$/g, '')).filter(Boolean);
    if (parts.length > 1) {
      return { latin: this.resolve(parts[0], requested).family, ea: this.resolve(parts.at(-1), requested, true).family };
    }
    const hasEastAsian = EAST_ASIAN.test(text), face = this.resolve(parts[0], requested, hasEastAsian);
    if (hasEastAsian && !face.cjk) {
      const eaFallback = this.catalog.fallbacks.ea;
      this.warn(`font '${face.family}' does not cover CJK; East Asian text uses '${eaFallback}'`);
      return { latin: face.family, ea: this.resolve(eaFallback, requested, true).family };
    }
    return face.family;
  }
}

/**
 * Find a covering fallback face without committing unused candidates to `store.needed`.
 * Order: the run's already-paired EA face → lightweight bundled symbol face (non-CJK) →
 * broad bundled EA face.
 */
function findGlyphFallback(primary, ea, slot, cluster, isEa, store) {
  const seen = new Set([key(primary.family)]);
  const candidates = [];
  if (ea && !seen.has(key(ea.family))) {
    seen.add(key(ea.family));
    candidates.push({ entry: ea, family: ea.family, eastAsian: true });
  }
  const symbolFallback = !isEa ? store.catalog.fallbacks.symbol : null;
  if (symbolFallback && !seen.has(key(symbolFallback))) {
    seen.add(key(symbolFallback));
    candidates.push({ entry: null, family: symbolFallback, eastAsian: false });
  }
  const eaFallback = store.catalog.fallbacks.ea;
  if (eaFallback && !seen.has(key(eaFallback))) {
    seen.add(key(eaFallback));
    candidates.push({ entry: null, family: eaFallback, eastAsian: true });
  }
  for (const candidate of candidates) {
    const entry = candidate.entry ?? store.pick(candidate.family, slot, candidate.eastAsian).entry;
    if (missingCodePoints(store.faceFont(entry), cluster)?.length === 0) {
      return candidate.entry ?? store.resolve(candidate.family, slot, candidate.eastAsian);
    }
  }
  return null;
}

/**
 * Resolve one leaf text node's actual faces and check/re-route uncovered grapheme clusters.
 * Formula segments (`\(...\)`) stay untouched for the Office Math pipeline; nested spans
 * cascade run weight/color/links in the writer.
 */
function processTextNode(textNode, ctx, store, { mutate }) {
  const text = textNode.textContent;
  if (!text) return;
  const slot = fontSlot(ctx.bold, ctx.italic);
  const fam = ctx.family;
  const latin = store.resolve(typeof fam === 'object' ? fam.latin : fam, slot);
  const ea = typeof fam === 'object' ? store.resolve(fam.ea, slot, true) : latin;

  const pieces = [];
  const push = (chunk, family) => {
    const last = pieces.at(-1);
    if (last && last.family === family) last.text += chunk;
    else pieces.push({ text: chunk, family });
  };

  for (const segment of splitFormulas(text)) {
    if (segment.formula) {
      push(segment.text, null);
      continue;
    }
    for (const { segment: cluster } of GRAPHEMES.segment(segment.text)) {
      const isEa = EAST_ASIAN.test(cluster);
      const primary = isEa ? ea : latin;
      const missing = missingCodePoints(store.faceFont(primary), cluster);
      if (!missing?.length) {
        push(cluster, null);
        continue;
      }
      const fallback = findGlyphFallback(primary, ea, slot, cluster, isEa, store);
      if (fallback) {
        addGlyphs(store.rerouted, `${primary.family}\0${primary.slot}\0${fallback.family}`, missing);
        push(cluster, fallback.family);
      } else {
        addGlyphs(store.missing, `${primary.family}\0${primary.slot}`, missing);
        push(cluster, null);
      }
    }
  }

  if (!mutate || !pieces.some((piece) => piece.family !== null)) return;

  const doc = textNode.ownerDocument, parent = textNode.parentNode;
  for (const piece of pieces) {
    if (!piece.text) continue;
    if (piece.family === null) {
      parent.insertBefore(doc.createTextNode(piece.text), textNode);
      continue;
    }
    const span = doc.createElementNS(parent.namespaceURI, 'span');
    span.setAttribute('style', `font-family:${piece.family}`);
    span.appendChild(doc.createTextNode(piece.text));
    parent.insertBefore(span, textNode);
  }
  parent.removeChild(textNode);
}

function checkPlainCoverage(text, family, slot, store) {
  if (!text) return;
  const latin = store.resolve(typeof family === 'object' ? family.latin : family, slot);
  const ea = typeof family === 'object' ? store.resolve(family.ea, slot, true) : latin;
  for (const { segment: cluster } of GRAPHEMES.segment(text)) {
    const primary = EAST_ASIAN.test(cluster) ? ea : latin;
    const missing = missingCodePoints(store.faceFont(primary), cluster);
    if (missing?.length) addGlyphs(store.missing, `${primary.family}\0${primary.slot}`, missing);
  }
}

function textFonts({ holder, style, markup }, store, { mutate }) {
  const cssCache = new WeakMap();
  const cssOf = (node) => {
    if (!cssCache.has(node)) cssCache.set(node, parseCss(node.getAttribute('style') ?? ''));
    return cssCache.get(node);
  };
  // Only un-overridden, non-formula visible text chooses a block's or span's family;
  // comments, URLs, formulas and descendants with their own family must not trigger CJK fallback.
  const ownText = (node, isRoot = false) => {
    if (node.nodeType === 3 || node.nodeType === 4) return stripFormulas(node.textContent);
    if (node.nodeType !== 1 || (!isRoot && cssOf(node).has('font-family'))) return '';
    return [...node.childNodes].map((child) => ownText(child)).join('');
  };
  const base = { bold: Boolean(style.bold), italic: Boolean(style.italic) };
  base.family = store.family(style.fontFamily, base.bold, base.italic, ownText(markup.root, true));
  if (mutate) holder.fontFamily = base.family;

  const visit = (node, parent) => {
    if (node.nodeType === 3 || node.nodeType === 4) {
      processTextNode(node, parent, store, { mutate });
      return;
    }
    if (node.nodeType !== 1) return;
    const css = cssOf(node), tag = node.localName.toLowerCase();
    const bold = css.has('font-weight')
      ? isBoldWeight(css.get('font-weight'))
      : parent.bold || tag === 'strong' || tag === 'b';
    const italic = css.has('font-style')
      ? FONT_STYLE_ITALIC.has(css.get('font-style'))
      : parent.italic || tag === 'em' || tag === 'i';
    let family = parent.family;
    if (css.has('font-family')) {
      family = store.family(css.get('font-family'), bold, italic, ownText(node, true));
      if (mutate) {
        css.set('font-family', typeof family === 'object' ? Object.values(family).join(', ') : family);
        node.setAttribute('style', [...css].map(([prop, value]) => `${prop}:${value}`).join(';'));
      }
    }
    for (const child of [...node.childNodes]) visit(child, { family, bold, italic });
  };
  visit(markup.root, base);
  if (mutate && holder.text) holder.text = markup.serialize();
}

function chartVisibleText(chart) {
  const parts = [];
  const addText = (v) => {
    if (typeof v === 'string') parts.push(v);
  };
  addText(typeof chart.title === 'string' ? chart.title : chart.title?.text);
  for (const axisKey of ['xAxis', 'yAxis', 'spokeAxis']) {
    const axes = Array.isArray(chart[axisKey]) ? chart[axisKey] : [chart[axisKey]];
    for (const axis of axes) {
      if (axis && typeof axis === 'object') {
        addText(typeof axis.title === 'string' ? axis.title : axis.title?.text);
      }
    }
  }
  for (const s of chart.series ?? []) {
    if (s && typeof s === 'object') addText(s.name);
  }
  for (const row of chart.data?.rows ?? []) {
    if (!Array.isArray(row)) continue;
    for (const cell of row) {
      if (typeof cell === 'string') parts.push(cell);
    }
  }
  return parts.join(' ');
}

async function analyzeFonts(project, content, { projectRoot, fontDirs = [], offline = false, mutate = true, checkEmbed = true }) {
  const store = new FontStore(fontDirs);
  for (const custom of project.customFonts ?? []) {
    const src = custom.src;
    const fontPaths = /^https:\/\//i.test(src)
      ? await resolveGoogleFont(src, custom.family, offline)
      : [path.resolve(projectRoot, src)];
    for (const fontPath of fontPaths) store.add(fontPath, -1, custom.family);
  }

  for (const block of content.texts) textFonts(block, store, { mutate });
  for (const page of project.pages) {
    for (const chart of page.elements.filter((element) => element.elementType === 'chart')) {
      const chartText = chartVisibleText(chart);
      const chartFamily = store.family(chart.fontFamily, false, false, chartText);
      if (mutate) chart.fontFamily = chartFamily;
      checkPlainCoverage(chartText, chartFamily, 'regular', store);
      for (const [config] of walkObjects(chart)) {
        if (config !== chart && 'fontFamily' in config) {
          const configText = typeof config.text === 'string' ? config.text : chartText;
          const slot = fontSlot(Boolean(config.bold), Boolean(config.italic));
          const resolved = store.family(config.fontFamily, Boolean(config.bold), Boolean(config.italic), configText);
          if (mutate) config.fontFamily = resolved;
          checkPlainCoverage(configText, resolved, slot, store);
        }
      }
    }
  }

  for (const [rerouteKey, cps] of [...store.rerouted.entries()].sort(compareKeys)) {
    const [family, slot, target] = rerouteKey.split('\0');
    store.warn(`font '${family}' / ${slot} cannot shape ${formatCodePoints(cps)}; those characters use '${target}'`);
  }

  const sortedNeeded = [...store.needed.entries()].sort(compareKeys);
  if (checkEmbed) {
    for (const [, entry] of sortedNeeded) {
      if (!embeddingAllowed(entry)) {
        store.warn(`font '${entry.family}' / ${entry.slot} cannot be embedded for editable output; install it on the playback machine`);
      }
    }
  } else if (sortedNeeded.length) {
    store.warn('font embedding is disabled; install the selected fonts on the rendering/playback machine');
  }

  for (const [missKey, cps] of [...store.missing.entries()].sort(compareKeys)) {
    const [family, slot] = missKey.split('\0');
    store.warn(`font '${family}' / ${slot} lacks glyphs used in deck text: ${formatCodePoints(cps)}`);
  }

  const families = [...new Set(sortedNeeded.map(([, entry]) => entry.family))].sort();
  return { store, sortedNeeded, families };
}

/** Resolve fonts and collect substitution/style/embedding/coverage warnings without mutating the deck or building EOTs. */
export async function checkFonts(project, content, { projectRoot, fontDirs = [], offline = false }) {
  const { store, families } = await analyzeFonts(project, content, {
    projectRoot, fontDirs, offline, mutate: false, checkEmbed: true,
  });
  return { warnings: store.warnings, families };
}

export async function prepareFonts(project, content, { projectRoot, fontDirs = [], embed = true, offline = false }) {
  const { store, sortedNeeded, families } = await analyzeFonts(project, content, {
    projectRoot, fontDirs, offline, mutate: true, checkEmbed: embed,
  });

  const data = [];
  const bindings = [];
  if (embed) {
    for (const [, entry] of sortedNeeded) {
      if (!embeddingAllowed(entry)) continue;
      const raw = store.readBytes(entry.path);
      const faceBytes = entry.eot ? raw : extractTtcFace(raw, entry.face);
      const eotBytes = ttfToEot(faceBytes);
      data.push({ typeface: entry.family, data: new Uint8Array(eotBytes.buffer, eotBytes.byteOffset, eotBytes.byteLength) });
      bindings.push({
        family: entry.family,
        slot: entry.slot,
        charset: entry.charset,
        pitchFamily: entry.pitchFamily,
      });
    }
  }

  const outlines = sortedNeeded.map(([, entry]) => ({
    family: entry.family, slot: entry.slot, face: entry.face,
    // Lazy original SFNT/TTC bytes, shared with embedding; never re-read a selected font.
    read: () => entry.eot ? extractEotSfnt(store.readBytes(entry.path)) : store.readBytes(entry.path),
  }));

  return { data, bindings, outlines, warnings: store.warnings, families };
}
