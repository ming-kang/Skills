// Byte identity and intrinsic dimensions: a URL or file suffix is only a source label.
import { DOMParser } from '../../../assets/vendor/xmldom.mjs';
import { fail } from '../deck/contract.mjs';

export const MIME_TYPES = {
  png: 'image/png',
  jpg: 'image/jpeg',
  gif: 'image/gif',
  svg: 'image/svg+xml',
};

const PNG_HEADER = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
const PNG_IEND = Buffer.from([73, 69, 78, 68, 174, 66, 96, 130]);
const JPEG_HEADER = Buffer.from([255, 216, 255]);
const JPEG_EOI = Buffer.from([255, 217]);
const SOF_MARKERS = new Set([0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf]);
const SVG_NS = 'http://www.w3.org/2000/svg';

function jpegSize(data) {
  let pos = 2;
  while (pos + 3 < data.length) {
    if (data[pos] !== 0xff) return null;
    while (pos < data.length && data[pos] === 0xff) pos += 1;
    if (pos >= data.length) return null;
    const marker = data[pos];
    pos += 1;
    if (marker === 0xd8 || marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) continue;
    if (marker === 0xd9 || marker === 0xda || pos + 2 > data.length) return null;
    const length = data.readUInt16BE(pos);
    if (length < 2 || pos + length > data.length) return null;
    if (SOF_MARKERS.has(marker) && length >= 7) {
      const height = data.readUInt16BE(pos + 3);
      const width = data.readUInt16BE(pos + 5);
      return [width, height];
    }
    pos += length;
  }
  return null;
}

function parseSvgSize(text) {
  let failed = false;
  const doc = new DOMParser({
    onError(level) {
      if (level !== 'warning') failed = true;
    },
  }).parseFromString(text, 'application/xml');
  const root = doc?.documentElement;
  if (failed || !root || root.localName !== 'svg' || (root.namespaceURI && root.namespaceURI !== SVG_NS)) {
    return null;
  }
  const dims = ['width', 'height'].map((attr) => {
    const raw = root.getAttribute(attr) ?? '';
    const match = /^([0-9]+(?:\.[0-9]+)?)(?:px|pt)?$/.exec(raw.trim());
    return match ? Number(match[1]) : null;
  });
  let [width, height] = dims;
  if (!width || !height) {
    const viewBox = (root.getAttribute('viewBox') ?? '').trim().split(/[\s,]+/);
    if (viewBox.length === 4) {
      const vw = Number(viewBox[2]);
      const vh = Number(viewBox[3]);
      if (Number.isFinite(vw) && vw > 0 && Number.isFinite(vh) && vh > 0) {
        width = vw;
        height = vh;
      }
    }
  }
  if (Number.isFinite(width) && width > 0 && Number.isFinite(height) && height > 0) {
    return { ext: 'svg', extension: '.svg', width, height };
  }
  return { ext: 'svg', extension: '.svg', width: null, height: null };
}

export function imageInfo(bytes, label = 'image') {
  const buf = Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes);
  if (buf.length >= 45 && buf.subarray(0, 8).equals(PNG_HEADER) && buf.subarray(12, 16).toString('ascii') === 'IHDR' && buf.includes(PNG_IEND)) {
    const width = buf.readUInt32BE(16);
    const height = buf.readUInt32BE(20);
    if (width > 0 && height > 0) return { ext: 'png', extension: '.png', width, height };
  } else if (buf.length >= 12 && buf.subarray(0, 3).equals(JPEG_HEADER) && buf.includes(JPEG_EOI)) {
    const size = jpegSize(buf);
    if (size && size[0] > 0 && size[1] > 0) return { ext: 'jpg', extension: '.jpg', width: size[0], height: size[1] };
  } else if (buf.length >= 14 && /^(GIF87a|GIF89a)$/.test(buf.subarray(0, 6).toString('ascii')) && buf.at(-1) === 59) {
    const width = buf.readUInt16LE(6);
    const height = buf.readUInt16LE(8);
    if (width > 0 && height > 0) return { ext: 'gif', extension: '.gif', width, height };
  } else {
    let text;
    try {
      text = new TextDecoder('utf-8', { fatal: true }).decode(buf).replace(/^\uFEFF/, '');
    } catch {
      text = null;
    }
    if (text !== null) {
      if (/<!\s*(DOCTYPE|ENTITY)\b/i.test(text)) fail(`${label}: SVG images must not contain DTD/entities`);
      if (/^\s*(?:<\?xml[^>]*>\s*)?(?:<!--[\s\S]*?-->\s*)*<svg(?:\s|>)/.test(text)) {
        const info = parseSvgSize(text);
        if (info) return info;
      }
    }
  }
  fail(`${label}: bytes are not a supported PNG/JPEG/GIF/SVG image`);
}

/** Every image holder, including table-cell and background image fills, not chart data. */
export function* imageHolders(value) {
  if (Array.isArray(value)) {
    for (const item of value) yield* imageHolders(item);
  } else if (value && typeof value === 'object') {
    if (value.elementType === 'image' || value.type === 'image') yield value;
    for (const [key, item] of Object.entries(value)) {
      if (key !== 'data') yield* imageHolders(item);
    }
  }
}
