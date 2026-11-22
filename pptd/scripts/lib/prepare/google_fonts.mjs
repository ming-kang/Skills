// Google Fonts CSS resolution and download caching for manifest.customFonts entries.
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { parseCss } from '../core/css.mjs';
import { fetchBounded } from '../core/net.mjs';
import { FONT_STYLE_ITALIC } from '../core/text.mjs';
import {
  fontSlot,
  normalizeFontKey as key,
  readFontFaces,
  readFontFacesFromFile,
} from './font_data.mjs';

const FONT_USER_AGENT = 'Mozilla/4.0 (compatible; pptd-font-loader/1)';
const ALLOWED_GOOGLE_HOSTS = new Set(['fonts.googleapis.com', 'fonts.gstatic.com']);
const GOOGLE_WEIGHT_BOLD = new Map([['400', false], ['normal', false], ['700', true], ['bold', true]]);

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
export async function resolveGoogleFont(url, family, offline) {
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
