// Font resolution, Google Fonts caching, rich-text inline font rewriting and EOT embedding.
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { readCatalog } from '../core/catalog.mjs';
import { parseCss, splitCss } from '../core/css.mjs';
import { textNodes } from '../core/markup.mjs';
import { walkObjects } from '../core/walk.mjs';
import {
  EAST_ASIAN,
  embeddingAllowed,
  extractEotSfnt,
  fontSlot,
  extractTtcFace,
  matchFontFamily,
  normalizeFontKey as key,
  readFontBytes,
  readFontFaces,
  readFontFacesFromFile,
  ttfToEot,
} from './font_data.mjs';
import { fetchBounded } from '../core/net.mjs';

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

const sha256 = (value) => crypto.createHash('sha256').update(value).digest('hex');

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

async function resolveGoogleFont(url, family, offline) {
  const parsed = assertGoogleUrl(url);
  if (parsed.hostname !== 'fonts.googleapis.com' || (parsed.pathname !== '/css' && parsed.pathname !== '/css2')) {
    throw new Error('customFonts.src must be a local font or a Google Fonts CSS URL');
  }
  if (parsed.searchParams.has('text')) {
    throw new Error('subset-only Google Fonts text= requests cannot provide complete editable fonts');
  }
  const cache = cacheDir();
  const digest = sha256(url + FONT_USER_AGENT);
  const metadataPath = path.join(cache, `${digest}.json`);
  const fontPath = path.join(cache, `${digest}.ttf`);
  if (fs.existsSync(metadataPath) && fs.existsSync(fontPath)) {
    try {
      const record = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
      const raw = fs.readFileSync(fontPath);
      if (sha256(raw) === record.sha256) return fontPath;
    } catch {
      // Re-fetch if cache metadata or payload is corrupt.
    }
  }
  if (offline) throw new Error(`custom font is not cached for offline use: ${family}`);

  const css = (await fetchGoogle(url)).toString('utf8').replace(/\/\*[\s\S]*?\*\//g, '');
  const matches = [];
  for (const [, block] of css.matchAll(/@font-face\s*\{([^}]+)\}/g)) {
    const props = Object.fromEntries(parseCss(block));
    const name = (props['font-family'] ?? '').replace(/^['"]+|['"]+$/g, '');
    const srcMatch = /url\(([^)]+)\)/.exec(props.src ?? '');
    const style = (props['font-style'] ?? 'normal').trim();
    const weight = (props['font-weight'] ?? '400').trim();
    if (key(name) === key(family) && srcMatch && style === 'normal' && weight === '400') {
      if ('unicode-range' in props) {
        throw new Error(`Google Fonts returned subset-only font rules: ${family}`);
      }
      matches.push(srcMatch[1].trim().replace(/^['"]+|['"]+$/g, ''));
    }
  }
  if (matches.length !== 1) {
    throw new Error(`Google Fonts must provide one complete, normal-weight TTF for ${family}`);
  }
  const data = await fetchGoogle(matches[0]);
  readFontFaces(data);
  fs.mkdirSync(cache, { recursive: true });
  const temp = path.join(cache, `${digest}.tmp`);
  fs.writeFileSync(temp, data);
  fs.renameSync(temp, fontPath);
  fs.writeFileSync(metadataPath, JSON.stringify({
    request: url,
    source: matches[0],
    sha256: sha256(data),
    family,
  }));
  return fontPath;
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
    this.fileBytes = new Map();
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

  resolve(rawName, requested, eastAsian = false) {
    const name = this.aliases.get(key(rawName)) ?? rawName;
    const cacheKey = `${key(name)}\0${requested}\0${eastAsian}`;
    if (this.resolved.has(cacheKey)) return this.resolved.get(cacheKey);
    let available = this.faces.get(key(name)) ?? [];
    if (!available.length && !this.scanned) {
      this.scanned = true;
      for (const dir of systemFontDirs()) this.scan(dir, 2);
      available = this.faces.get(key(name)) ?? [];
    }
    if (!available.length) {
      const fallback = this.catalog.fallbacks[eastAsian ? 'ea' : 'latin'];
      if (key(name) === key(fallback)) throw new Error(`bundled fallback font is missing: ${fallback}`);
      this.warn(`font '${name}' is unavailable; exported text uses '${fallback}'`);
      const entry = this.resolve(fallback, requested, eastAsian);
      this.resolved.set(cacheKey, entry);
      return entry;
    }
    const entry = available.toSorted((a, b) =>
      a.priority - b.priority || Number(a.slot !== requested) - Number(b.slot !== requested) ||
      Number(a.slot !== 'regular') - Number(b.slot !== 'regular'))[0];
    if (entry.slot !== requested) this.warn(`font '${name}' has no ${requested} face; presentation software must synthesize that style`);
    if (entry.face === undefined) {
      const raw = this.readBytes(entry.path);
      if (sha256(raw) !== entry.sha256) throw new Error(`bundled font does not match its catalog: ${path.basename(entry.path)}`);
      Object.assign(entry, readFontFaces(raw)[0]);
      this.index(entry);
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
      this.warn(`font '${face.family}' does not cover CJK; East Asian text uses 'Noto Sans SC'`);
      return { latin: face.family, ea: this.resolve('Noto Sans SC', requested, true).family };
    }
    return face.family;
  }
}

function textFonts({ holder, style, markup }, store) {
  const cssCache = new WeakMap();
  const cssOf = (node) => {
    if (!cssCache.has(node)) cssCache.set(node, parseCss(node.getAttribute('style') ?? ''));
    return cssCache.get(node);
  };
  // Only un-overridden visible text chooses the block's base family; comments, URLs,
  // CSS family names and descendants with their own family must not trigger CJK fallback.
  const baseText = (node) => {
    if (node.nodeType === 3 || node.nodeType === 4) return node.textContent;
    if (node.nodeType !== 1 || cssOf(node).has('font-family')) return '';
    return [...node.childNodes].map(baseText).join('');
  };
  const base = { bold: Boolean(style.bold), italic: Boolean(style.italic) };
  base.family = store.family(style.fontFamily, base.bold, base.italic, baseText(markup.root));
  holder.fontFamily = base.family;
  const visit = (node, parent) => {
    if (node.nodeType === 3 || node.nodeType === 4) {
      if (node.textContent) store.family(parent.family, parent.bold, parent.italic, node.textContent);
      return;
    }
    if (node.nodeType !== 1) return;
    const css = cssOf(node), tag = node.localName.toLowerCase();
    const bold = parent.bold || ['strong', 'b'].includes(tag) || ['bold', '700', '800', '900'].includes(css.get('font-weight'));
    const italic = parent.italic || ['em', 'i'].includes(tag) || css.get('font-style') === 'italic';
    let family = parent.family;
    if (css.has('font-family')) {
      family = store.family(css.get('font-family'), bold, italic, [...textNodes(node)].map((text) => text.textContent).join(''));
      css.set('font-family', typeof family === 'object' ? Object.values(family).join(', ') : family);
      node.setAttribute('style', [...css].map(([key, value]) => `${key}:${value}`).join(';'));
    }
    for (const child of [...node.childNodes]) visit(child, { family, bold, italic });
  };
  visit(markup.root, base);
  if (holder.text) holder.text = markup.serialize();
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

export async function prepareFonts(project, content, { projectRoot, fontDirs = [], embed = true, offline = false }) {
  const store = new FontStore(fontDirs);
  for (const custom of project.customFonts ?? []) {
    const src = custom.src;
    const fontPath = /^https:\/\//i.test(src)
      ? await resolveGoogleFont(src, custom.family, offline)
      : path.resolve(projectRoot, src);
    store.add(fontPath, -1, custom.family);
  }

  for (const block of content.texts) textFonts(block, store);
  for (const page of project.pages) {
    for (const chart of page.elements.filter((element) => element.elementType === 'chart')) {
      const chartText = chartVisibleText(chart);
      chart.fontFamily = store.family(chart.fontFamily, false, false, chartText);
      for (const [config] of walkObjects(chart)) {
        if (config !== chart && 'fontFamily' in config) {
          config.fontFamily = store.family(config.fontFamily, Boolean(config.bold), Boolean(config.italic), chartText);
        }
      }
    }
  }

  const data = [];
  const bindings = [];
  const sortedNeeded = [...store.needed.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
  if (embed) {
    for (const [, entry] of sortedNeeded) {
      if (!embeddingAllowed(entry)) {
        store.warn(`font '${entry.family}' / ${entry.slot} cannot be embedded for editable output; install it on the playback machine`);
        continue;
      }
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
  } else if (sortedNeeded.length) {
    store.warn('font embedding is disabled; install the selected fonts on the rendering/playback machine');
  }

  const outlines = sortedNeeded.map(([, entry]) => ({
    family: entry.family, slot: entry.slot, face: entry.face,
    // Lazy original SFNT/TTC bytes, shared with embedding; never re-read a selected font.
    read: () => entry.eot ? extractEotSfnt(store.readBytes(entry.path)) : store.readBytes(entry.path),
  }));

  const families = [...new Set([...store.needed.values()].map((entry) => entry.family))].sort();
  return { data, bindings, outlines, warnings: store.warnings, families };
}
