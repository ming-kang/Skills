// Prepare editable vector icons and resolve/deduplicate image assets to WASM asset keys.
import crypto from 'node:crypto';
import fs from 'node:fs';

import { iconDefinition } from '../core/catalog.mjs';
import { imageInfo } from '../core/media.mjs';
import { walkObjects } from '../core/walk.mjs';
import { fetchBounded } from '../core/net.mjs';
import { checkContainedFile, checkRelativePath, normalizeLocalPath } from '../deck/contract.mjs';

function resolveIcon(name) {
  if (typeof name !== 'string' || !/^(fas|far|fab):[a-z0-9][a-z0-9-]*$/.test(name)) {
    throw new Error('iconName must be a Font Awesome Free name such as fas:house, far:heart or fab:github');
  }
  const definition = iconDefinition(name);
  if (!definition) throw new Error(`unknown bundled Font Awesome Free icon: ${name}`);
  return definition;
}

export function prepareIcons(project) {
  let count = 0;
  for (const page of project.pages) {
    for (const element of page.elements) {
      if (element.elementType !== 'icon') continue;
      try {
        const { path, viewBox } = resolveIcon(element.iconName);
        Object.assign(element, { path, viewBox, fill: element.fill ?? { type: 'solid', color: '#000000' } });
        count += 1;
      } catch (error) {
        throw new Error(`${page.pagePath}: icon ${element.elementId}: ${error.message}`);
      }
    }
  }
  return count;
}

function* imageHolders(project) {
  for (const [value] of walkObjects(project)) {
    if (value.elementType === 'image' || value.type === 'image') yield value;
  }
}

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
 * Returns WASM asset keys -> bytes, and populates `mediaByKey` with `{ key, bytes, info, digest, remote }`
 * used later for native table image fills. Holders are remapped in place.
 */
export async function resolveImages(project, projectRoot, mediaByKey = new Map(), offline = false) {
  const images = {};
  const remapped = new Map();
  const byDigest = new Map();
  const holders = [...imageHolders(project)];
  const sources = [...new Set(holders.map((holder) => holder.src).filter(Boolean))];
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
      images[key] = new Uint8Array(bytes.buffer, bytes.byteOffset, bytes.byteLength);
      mediaByKey.set(key, { key, bytes, info, digest, remote });
    } else if (remote) {
      mediaByKey.get(key).remote = true;
    }
    remapped.set(src, key);
  }
  for (const holder of holders) {
    if (remapped.has(holder.src)) holder.src = remapped.get(holder.src);
  }
  return images;
}
