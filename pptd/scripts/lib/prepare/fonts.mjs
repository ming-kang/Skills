// Font resolution, Google Fonts caching, rich-text inline font rewriting and EOT embedding.
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { textStyleReference, tableCells } from '../deck/schema.mjs';
import { embeddingAllowed, extractTtcFace, readFontFaces, ttfToEot } from './font_data.mjs';

const SKILL_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const ASSETS = path.join(SKILL_DIR, 'assets', 'fonts');
const FONT_SUFFIXES = new Set(['.ttf', '.ttc', '.otf', '.eot', '.fntdata']);
const FONT_USER_AGENT = 'Mozilla/4.0 (compatible; pptd-font-loader/1)';
const LOCAL_ALIASES = {
  '微软雅黑': 'Microsoft YaHei',
  '微软正黑体': 'Microsoft JhengHei',
  '宋体': 'SimSun',
  '黑体': 'SimHei',
};
const CJK = /[\u3400-\u9fff\uf900-\ufaff]/;
const VOID_TAGS = new Set(['br', 'img', 'hr']);
const MAX_FONT_BYTES = 64 * 1024 * 1024;
const ALLOWED_GOOGLE_HOSTS = new Set(['fonts.googleapis.com', 'fonts.gstatic.com']);

const key = (name) => String(name).replace(/[\s_-]+/g, '').toLowerCase();
const slotOf = (bold, italic) => (bold && italic ? 'boldItalic' : bold ? 'bold' : italic ? 'italic' : 'regular');
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
  let current = assertGoogleUrl(url).href;
  for (let redirects = 0; redirects < 6; redirects++) {
    const response = await fetch(current, {
      headers: { 'User-Agent': FONT_USER_AGENT },
      redirect: 'manual',
      signal: AbortSignal.timeout(30000),
    });
    if (response.status >= 300 && response.status < 400) {
      const location = response.headers.get('location');
      if (!location) throw new Error('custom font download redirect missing location');
      const next = new URL(location, current);
      if (next.protocol !== 'https:' || !ALLOWED_GOOGLE_HOSTS.has(next.hostname)) {
        throw new Error('custom font download redirected outside Google Fonts');
      }
      current = next.href;
      continue;
    }
    if (!response.ok) throw new Error(`custom font download failed (${response.status}): ${current}`);
    const lengthHeader = Number(response.headers.get('content-length') ?? 0);
    if (lengthHeader > MAX_FONT_BYTES) throw new Error('custom font exceeds the 64 MiB download limit');
    const data = Buffer.from(await response.arrayBuffer());
    if (data.length > MAX_FONT_BYTES) throw new Error('custom font exceeds the 64 MiB download limit');
    return data;
  }
  throw new Error('too many redirects downloading custom font');
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

  const css = (await fetchGoogle(url)).toString('utf8');
  const matches = [];
  for (const [, block] of css.matchAll(/@font-face\s*\{([^}]+)\}/g)) {
    const props = {};
    for (const [, prop, val] of block.matchAll(/([\w-]+)\s*:\s*([^;]+)/g)) {
      props[prop.trim().toLowerCase()] = val.trim();
    }
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

export class FontStore {
  constructor(fontDirs = []) {
    this.catalog = JSON.parse(fs.readFileSync(path.join(ASSETS, 'catalog.json'), 'utf8'));
    this.faces = [];
    this.aliases = new Map();
    for (const [alias, target] of Object.entries({ ...this.catalog.aliases, ...LOCAL_ALIASES })) {
      this.aliases.set(key(alias), target);
    }
    this.extraDirs = fontDirs.map((dir) => path.resolve(String(dir).replace(/^~(?=$|[\\/])/, os.homedir())));
    this.scanned = false;
    this.warnings = [];
    this.needed = new Map();
    this.resolved = new Map();

    for (const entry of this.catalog.faces) {
      this.faces.push({ ...entry, path: path.join(ASSETS, entry.src), priority: 1 });
    }
    for (const dir of this.extraDirs) {
      if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) {
        throw new Error(`font directory does not exist: ${dir}`);
      }
      this.scan(dir, 0);
    }
  }

  warn(message) {
    if (!this.warnings.includes(message)) this.warnings.push(message);
  }

  add(filePath, priority, family = null) {
    try {
      const data = fs.readFileSync(filePath);
      const faces = readFontFaces(data);
      if (family && !faces.some((face) => key(family) === key(face.family) || face.aliases.some((alias) => key(alias) === key(family)))) {
        throw new Error(`custom font family does not match its file: ${family} / ${path.basename(filePath)}`);
      }
      for (const face of faces) {
        this.faces.push({ ...face, path: filePath, priority });
      }
    } catch (error) {
      if (family) throw new Error(`cannot load custom font ${family}: ${error.message}`);
    }
  }

  scan(directory, priority) {
    if (!fs.existsSync(directory) || !fs.statSync(directory).isDirectory()) return;
    let entries;
    try {
      entries = fs.readdirSync(directory, { withFileTypes: true, recursive: true });
    } catch {
      return;
    }
    const files = entries
      .filter((entry) => entry.isFile() && FONT_SUFFIXES.has(path.extname(entry.name).toLowerCase()))
      .map((entry) => path.join(entry.parentPath ?? entry.path, entry.name))
      .sort();
    for (const file of files) this.add(file, priority);
  }

  resolve(rawName, requested, eastAsian = false) {
    const name = this.aliases.get(key(rawName)) ?? rawName;
    const candidates = () => this.faces.filter(
      (face) => key(face.family) === key(name) || (face.aliases ?? []).some((alias) => key(alias) === key(name)),
    );
    let available = candidates();
    if (!available.length && !this.scanned) {
      this.scanned = true;
      for (const dir of systemFontDirs()) this.scan(dir, 2);
      available = candidates();
    }
    if (!available.length) {
      const fallback = this.catalog.fallbacks[eastAsian || name === 'MiSans' ? 'ea' : 'latin'];
      this.warn(`font '${name}' is unavailable; exported text uses '${fallback}'`);
      return this.resolve(fallback, requested, eastAsian);
    }
    const minPriority = Math.min(...available.map((face) => face.priority));
    available = available.filter((face) => face.priority === minPriority);
    available.sort((a, b) => {
      const reqDiff = Number(a.slot !== requested) - Number(b.slot !== requested);
      if (reqDiff !== 0) return reqDiff;
      return Number(a.slot !== 'regular') - Number(b.slot !== 'regular');
    });
    const entry = available.find((face) => face.slot === requested) ?? available[0];
    if (entry.slot !== requested) {
      this.warn(`font '${name}' has no ${requested} face; presentation software must synthesize that style`);
    }
    if (entry.face === undefined) {
      const raw = fs.readFileSync(entry.path);
      if (sha256(raw) !== entry.sha256) {
        throw new Error(`bundled font does not match its catalog: ${path.basename(entry.path)}`);
      }
      Object.assign(entry, readFontFaces(raw)[0]);
    }
    this.needed.set(`${entry.family}\0${entry.slot}`, entry);
    this.resolved.set(`${entry.family}\0${requested}`, entry);
    return entry.family;
  }

  family(value, bold = false, italic = false, text = '') {
    const requested = slotOf(bold, italic);
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      const mapped = {};
      for (const [k, name] of Object.entries(value)) {
        mapped[k] = this.resolve(name, requested, k === 'ea');
      }
      return mapped;
    }
    const name = value || 'MiSans';
    if (String(name).includes(',')) {
      const parts = String(name).split(',').map((part) => part.trim().replace(/^['"]+|['"]+$/g, '')).filter(Boolean);
      return {
        latin: this.resolve(parts[0], requested),
        ea: this.resolve(parts.at(-1), requested, true),
      };
    }
    const family = this.resolve(name, requested, CJK.test(text));
    if (CJK.test(text) && !this.resolved.get(`${family}\0${requested}`)?.cjk) {
      this.warn(`font '${family}' does not cover CJK; East Asian text uses 'Noto Sans SC'`);
      return { latin: family, ea: this.resolve('Noto Sans SC', requested, true) };
    }
    return family;
  }
}

function escapeAttr(value) {
  return String(value ?? '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function decodeHtmlEntities(text) {
  return text.replace(/&(#x[\da-f]+|#\d+|amp|lt|gt|quot|apos|nbsp);/gi, (full, entity) => {
    const lower = entity.toLowerCase();
    if (lower === 'amp') return '&';
    if (lower === 'lt') return '<';
    if (lower === 'gt') return '>';
    if (lower === 'quot') return '"';
    if (lower === 'apos') return "'";
    if (lower === 'nbsp') return '\u00a0';
    const code = lower.startsWith('#x') ? parseInt(lower.slice(2), 16) : parseInt(lower.slice(1), 10);
    return Number.isFinite(code) && code > 0 && code <= 0x10ffff ? String.fromCodePoint(code) : full;
  });
}

function parseAttributes(raw) {
  const attrs = [];
  const pattern = /([A-Za-z_:][\w:.-]*)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
  let match;
  while ((match = pattern.exec(raw))) {
    const value = match[2] ?? match[3] ?? match[4] ?? '';
    attrs.push([match[1], decodeHtmlEntities(value)]);
  }
  return attrs;
}

function tokenizeHtml(html) {
  const tokens = [];
  const tagPattern = /<!--[\s\S]*?-->|<\/?([A-Za-z][A-Za-z0-9:-]*)((?:\s+[^<>]*?)?)\s*(\/?)>/g;
  let last = 0;
  let match;
  while ((match = tagPattern.exec(html))) {
    if (match.index > last) tokens.push({ type: 'text', raw: html.slice(last, match.index) });
    if (match[0].startsWith('<!--')) {
      tokens.push({ type: 'comment', raw: match[0] });
    } else if (match[0].startsWith('</')) {
      tokens.push({ type: 'end', tag: match[1].toLowerCase(), raw: match[0] });
    } else {
      tokens.push({
        type: 'start',
        tag: match[1].toLowerCase(),
        attrs: parseAttributes(match[2] ?? ''),
        selfClosing: Boolean(match[3]),
        raw: match[0],
      });
    }
    last = tagPattern.lastIndex;
  }
  if (last < html.length) tokens.push({ type: 'text', raw: html.slice(last) });
  return tokens;
}

function textFonts(holder, style, store) {
  const baseFamily = store.family(
    style.fontFamily ?? 'MiSans',
    Boolean(style.bold),
    Boolean(style.italic),
    holder.text ?? '',
  );
  holder.fontFamily = baseFamily;
  const html = holder.text ?? '';
  if (!html) return;

  const tokens = tokenizeHtml(html);
  // Pre-compute descendant decoded text for every start token.
  const descendants = new Map();
  const textStack = [];
  for (const token of tokens) {
    if (token.type === 'start') {
      descendants.set(token, '');
      if (!VOID_TAGS.has(token.tag) && !token.selfClosing) textStack.push(token);
    } else if (token.type === 'end') {
      if (!VOID_TAGS.has(token.tag) && textStack.length) textStack.pop();
    } else if (token.type === 'text') {
      const decoded = decodeHtmlEntities(token.raw);
      for (const ancestor of textStack) {
        descendants.set(ancestor, descendants.get(ancestor) + decoded);
      }
    }
  }

  const stateStack = [{ family: baseFamily, bold: Boolean(style.bold), italic: Boolean(style.italic) }];
  const output = [];
  for (const token of tokens) {
    if (token.type === 'start') {
      const parent = stateStack.at(-1);
      let family = parent.family;
      let bold = parent.bold || token.tag === 'strong' || token.tag === 'b';
      let italic = parent.italic || token.tag === 'em' || token.tag === 'i';
      const attrMap = new Map(token.attrs);
      const css = new Map();
      for (const [, prop, val] of (attrMap.get('style') ?? '').matchAll(/([\w-]+)\s*:\s*([^;]+)/g)) {
        css.set(prop.trim().toLowerCase(), val.trim());
      }
      if (['bold', '700', '800', '900'].includes(css.get('font-weight') ?? '')) bold = true;
      if ((css.get('font-style') ?? '') === 'italic') italic = true;
      if (css.has('font-family')) {
        const inlineName = css.get('font-family').replace(/^['"]+|['"]+$/g, '');
        family = store.family(inlineName, bold, italic, descendants.get(token) ?? '');
        css.set('font-family', typeof family === 'object' ? Object.values(family).join(', ') : family);
        attrMap.set('style', [...css.entries()].map(([k, v]) => `${k}:${v}`).join(';'));
      }
      store.family(family, bold, italic);
      if (!VOID_TAGS.has(token.tag) && !token.selfClosing) stateStack.push({ family, bold, italic });
      const attrsText = [...attrMap.entries()].map(([k, v]) => ` ${k}="${escapeAttr(v)}"`).join('');
      output.push(`<${token.tag}${attrsText}${token.selfClosing ? '/>' : '>'}`);
    } else if (token.type === 'end') {
      if (!VOID_TAGS.has(token.tag) && stateStack.length > 1) stateStack.pop();
      output.push(token.raw);
    } else if (token.type === 'text') {
      const current = stateStack.at(-1);
      store.family(current.family, current.bold, current.italic, decodeHtmlEntities(token.raw));
      output.push(token.raw);
    } else {
      output.push(token.raw);
    }
  }
  if (html.includes('font-family')) holder.text = output.join('');
}

function visitChartFonts(value, store, chartText) {
  if (Array.isArray(value)) {
    for (const child of value) visitChartFonts(child, store, chartText);
  } else if (value && typeof value === 'object') {
    if ('fontFamily' in value) {
      value.fontFamily = store.family(value.fontFamily, Boolean(value.bold), Boolean(value.italic), chartText);
    }
    for (const [k, child] of Object.entries(value)) {
      if (k !== 'data') visitChartFonts(child, store, chartText);
    }
  }
}

export async function prepareFonts(project, { fontDirs = [], embed = true, offline = false } = {}) {
  const store = new FontStore(fontDirs);
  const root = path.dirname(project.manifestPath);
  for (const custom of project.manifest.customFonts ?? []) {
    const src = custom.src;
    const fontPath = /^https:\/\//i.test(src)
      ? await resolveGoogleFont(src, custom.family, offline)
      : path.resolve(root, src);
    store.add(fontPath, -1, custom.family);
  }

  const theme = project.manifest.theme ?? {};
  for (const page of project.pages) {
    for (const item of page.data.elements) {
      if (item.elementType === 'text') {
        const content = item.content;
        const baseStyle = textStyleReference(theme, content.style, `${item.elementId}.content.style`);
        textFonts(content, { ...baseStyle, ...content }, store);
      } else if (item.elementType === 'table') {
        for (const cellInfo of tableCells(item, theme, item.elementId)) {
          const holder = { text: cellInfo.cell.text ?? '', fontFamily: cellInfo.style.fontFamily };
          textFonts(holder, cellInfo.style, store);
          cellInfo.cell.fontFamily = holder.fontFamily;
          if (holder.text !== (cellInfo.cell.text ?? '')) cellInfo.cell.text = holder.text;
        }
      } else if (item.elementType === 'chart') {
        const chartText = JSON.stringify(item);
        item.fontFamily = store.family(item.fontFamily ?? 'MiSans', false, false, chartText);
        visitChartFonts(item, store, chartText);
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
      const raw = fs.readFileSync(entry.path);
      const faceBytes = entry.eot ? raw : extractTtcFace(raw, entry.face);
      const eotBytes = ttfToEot(faceBytes);
      data.push({ typeface: entry.family, data: new Uint8Array(eotBytes) });
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
    family: entry.family,
    slot: entry.slot,
    path: entry.path,
    face: entry.face,
    eot: entry.eot,
  }));

  const families = [...new Set([...store.needed.values()].map((entry) => entry.family))].sort();
  return { data, bindings, outlines, warnings: store.warnings, families };
}
