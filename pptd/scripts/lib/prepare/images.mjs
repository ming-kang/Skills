// Resolve every image source to real bytes and remap the holders to WASM asset keys.
// Data URLs, remote URLs and project-local files all land in one byte-identity map.
import fs from 'node:fs';
import path from 'node:path';

import { imageHolders, imageInfo } from './media.mjs';

function safeJoin(root, relative) {
  const base = path.resolve(root);
  const target = path.resolve(base, relative.replaceAll('\\', '/'));
  const prefix = base.endsWith(path.sep) ? base : base + path.sep;
  if (target !== base && !target.startsWith(prefix)) throw new Error(`project path escapes the PPTD directory: ${relative}`);
  return target;
}

async function imageBytes(src, projectRoot, offline) {
  if (src.startsWith('data:')) {
    const match = /^data:([^;,]+)?(;base64)?,(.*)$/s.exec(src);
    if (!match) throw new Error('invalid data URL image');
    return match[2] ? Buffer.from(match[3], 'base64') : Buffer.from(decodeURIComponent(match[3]));
  }
  if (/^https?:\/\//i.test(src)) {
    if (offline) throw new Error('offline export requires local media');
    const response = await fetch(src, { signal: AbortSignal.timeout(30000) });
    if (!response.ok) throw new Error(`image fetch failed ${response.status}: ${src}`);
    return Buffer.from(await response.arrayBuffer());
  }
  const local = safeJoin(projectRoot, src.replace(/^file:\/\/+/, ''));
  if (!fs.existsSync(local)) throw new Error(`missing local image: ${src}`);
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
  const sources = [...new Set([...imageHolders(project)].map((holder) => holder.src).filter(Boolean))];
  await Promise.all(sources.map(async (src, index) => {
    let bytes;
    let info;
    try {
      bytes = await imageBytes(src, projectRoot, offline);
      info = imageInfo(bytes, src);
    } catch (error) {
      throw new Error(`image ${String(src).slice(0, 180)}: ${error.message}`);
    }
    const key = `wasm-assets/img-${index}${info.extension}`;
    images[key] = new Uint8Array(bytes);
    records.push({ source: src, key, bytes, info });
    remapped.set(src, key);
  }));
  for (const holder of imageHolders(project)) {
    if (remapped.has(holder.src)) holder.src = remapped.get(holder.src);
  }
  return images;
}
