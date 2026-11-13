// Resolve every image source to real bytes and remap the holders to WASM asset keys.
// Data URLs, remote URLs and project-local files all land in one byte-identity map.
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

import { normalizeLocalPath } from '../deck/contract.mjs';
import { imageHolders, imageInfo } from './media.mjs';

const MAX_IMAGE_BYTES = 64 * 1024 * 1024;

function safeJoin(root, relative) {
  const base = path.resolve(root);
  const target = path.resolve(base, relative.replaceAll('\\', '/'));
  const prefix = base.endsWith(path.sep) ? base : base + path.sep;
  if (target !== base && !target.startsWith(prefix)) throw new Error(`project path escapes the PPTD directory: ${relative}`);
  return target;
}

async function fetchRemoteImage(src) {
  let current = new URL(src).href;
  for (let redirects = 0; redirects < 6; redirects++) {
    const response = await fetch(current, {
      redirect: 'manual',
      signal: AbortSignal.timeout(30000),
    });
    if (response.status >= 300 && response.status < 400) {
      const location = response.headers?.get?.('location');
      if (!location) throw new Error(`image redirect missing location: ${current}`);
      const next = new URL(location, current);
      if (next.protocol !== 'https:' && next.protocol !== 'http:') {
        throw new Error(`image redirected to unsupported protocol: ${next.protocol}`);
      }
      current = next.href;
      continue;
    }
    if (!response.ok) throw new Error(`image fetch failed ${response.status}: ${current}`);
    const lengthHeader = Number(response.headers?.get?.('content-length') ?? 0);
    if (lengthHeader > MAX_IMAGE_BYTES) throw new Error('remote image exceeds the 64 MiB download limit');
    const data = Buffer.from(await response.arrayBuffer());
    if (data.length > MAX_IMAGE_BYTES) throw new Error('remote image exceeds the 64 MiB download limit');
    return data;
  }
  throw new Error(`too many redirects fetching image: ${src}`);
}

async function imageBytes(src, projectRoot, offline) {
  if (src.startsWith('data:')) {
    const match = /^data:([^;,]+)?(;base64)?,(.*)$/s.exec(src);
    if (!match) throw new Error('invalid data URL image');
    return match[2] ? Buffer.from(match[3], 'base64') : Buffer.from(decodeURIComponent(match[3]));
  }
  if (/^https?:\/\//i.test(src)) {
    if (offline) throw new Error('offline export requires local media');
    return fetchRemoteImage(src);
  }
  const local = safeJoin(projectRoot, normalizeLocalPath(src));
  if (!fs.existsSync(local) || !fs.statSync(local).isFile()) throw new Error(`missing local image: ${src}`);
  const root = fs.realpathSync(projectRoot);
  const resolved = fs.realpathSync(local);
  safeJoin(root, path.relative(root, resolved));
  return fs.readFileSync(resolved);
}

/**
 * Returns WASM asset keys → bytes, and populates `records` with `{ source, key, bytes, info }`
 * used later for native table image fills. Holders are remapped in place.
 */
export async function resolveImages(project, projectRoot, records = [], offline = false) {
  const images = {};
  const remapped = new Map();
  const byDigest = new Map();
  const sources = [...new Set([...imageHolders(project)].map((holder) => holder.src).filter(Boolean))];
  const loaded = await Promise.all(sources.map(async (src) => {
    try {
      const bytes = await imageBytes(src, projectRoot, offline);
      const info = imageInfo(bytes, src);
      const digest = crypto.createHash('sha256').update(bytes).digest('hex');
      return { src, bytes, info, digest };
    } catch (error) {
      throw new Error(`image ${String(src).slice(0, 180)}: ${error.message}`);
    }
  }));

  let nextIndex = 0;
  for (const { src, bytes, info, digest } of loaded) {
    let key = byDigest.get(digest);
    if (!key) {
      key = `wasm-assets/img-${nextIndex++}${info.extension}`;
      byDigest.set(digest, key);
      images[key] = new Uint8Array(bytes);
    }
    records.push({ source: src, key, bytes, info });
    remapped.set(src, key);
  }
  for (const holder of imageHolders(project)) {
    if (remapped.has(holder.src)) holder.src = remapped.get(holder.src);
  }
  return images;
}
