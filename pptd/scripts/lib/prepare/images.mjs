// Resolve every image source to real bytes and remap the holders to WASM asset keys.
// Data URLs, remote URLs and project-local files all land in one byte-identity map.
import crypto from 'node:crypto';
import fs from 'node:fs';

import { checkContainedFile, checkRelativePath, normalizeLocalPath } from '../deck/contract.mjs';
import { imageHolders, imageInfo } from './media.mjs';
import { fetchBounded } from './net.mjs';

async function imageBytes(src, projectRoot, getRealRoot, offline) {
  if (src.startsWith('data:')) {
    const match = /^data:([^;,]+)?(;base64)?,(.*)$/s.exec(src);
    if (!match) throw new Error('invalid data URL image');
    return match[2] ? Buffer.from(match[3], 'base64') : Buffer.from(decodeURIComponent(match[3]));
  }
  if (/^https?:\/\//i.test(src)) {
    if (offline) throw new Error('offline export requires local media');
    return fetchBounded(src, { label: 'image' });
  }
  const relative = checkRelativePath(normalizeLocalPath(src), 'image');
  const realTarget = checkContainedFile(projectRoot, getRealRoot(), relative, 'image', `missing local image: ${src}`);
  return fs.readFileSync(realTarget);
}

/**
 * Returns WASM asset keys -> bytes, and populates `mediaByKey` with `{ key, bytes, info, remote }`
 * used later for native table image fills. Holders are remapped in place.
 */
export async function resolveImages(project, projectRoot, mediaByKey = new Map(), offline = false) {
  const images = {};
  const remapped = new Map();
  const byDigest = new Map();
  const sources = [...new Set([...imageHolders(project)].map((holder) => holder.src).filter(Boolean))];
  let realRoot;
  const getRealRoot = () => (realRoot ??= fs.realpathSync(projectRoot));
  const loaded = await Promise.all(sources.map(async (src) => {
    try {
      const bytes = await imageBytes(src, projectRoot, getRealRoot, offline);
      const info = imageInfo(bytes, src);
      const digest = crypto.createHash('sha256').update(bytes).digest('hex');
      return { src, bytes, info, digest, remote: /^https?:\/\//i.test(src) };
    } catch (error) {
      throw new Error(`image ${String(src).slice(0, 180)}: ${error.message}`);
    }
  }));

  let nextIndex = 0;
  for (const { src, bytes, info, digest, remote } of loaded) {
    let key = byDigest.get(digest);
    if (!key) {
      key = `wasm-assets/img-${nextIndex++}${info.extension}`;
      byDigest.set(digest, key);
      images[key] = new Uint8Array(bytes);
      mediaByKey.set(key, { key, bytes, info, remote });
    } else if (remote) {
      mediaByKey.get(key).remote = true;
    }
    remapped.set(src, key);
  }
  for (const holder of imageHolders(project)) {
    if (remapped.has(holder.src)) holder.src = remapped.get(holder.src);
  }
  return images;
}
