// Shared invariants for every deck value that can reach OOXML, plus the JSON/YAML
// boundary. Python and Node both consume this module's output, so the rules live here once.

const XML_FORBIDDEN = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\ud800-\udfff\ufffe\uffff]/;

export class DeckError extends Error {}

export function fail(message) {
  throw new DeckError(message);
}

export function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

export function isPlainObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** Every string that can reach OOXML, and the JSON boundary itself. */
export function checkJsonValue(value, label) {
  if (typeof value === 'string') {
    const match = XML_FORBIDDEN.exec(value);
    if (match) fail(`${label} contains an XML-forbidden character U+${match[0].codePointAt(0).toString(16).toUpperCase().padStart(4, '0')}`);
    return;
  }
  if (Array.isArray(value)) {
    for (let index = 0; index < value.length; index++) checkJsonValue(value[index], `${label}[${index}]`);
    return;
  }
  if (isPlainObject(value)) {
    for (const [key, item] of Object.entries(value)) {
      if (key.startsWith('__proto__') || key.startsWith('constructor') || key.startsWith('prototype')) {
        fail(`${label}: mapping key ${JSON.stringify(key)} is not allowed`);
      }
      checkJsonValue(item, `${label}.${key}`);
    }
    return;
  }
  if (value === null || typeof value === 'boolean' || typeof value === 'number') {
    if (typeof value === 'number' && !Number.isFinite(value)) fail(`${label} must be a finite number`);
    return;
  }
  fail(`${label} must be a JSON-compatible scalar; quote dates and other YAML strings`);
}

/** [x, y, width, height] with positive finite width and height. */
export function checkBounds(value, label) {
  if (!Array.isArray(value) || value.length !== 4 || !value.every(isFiniteNumber)) {
    fail(`${label} must be [x, y, width, height] with finite numbers`);
  }
  if (value[2] <= 0 || value[3] <= 0) fail(`${label} width and height must be positive`);
  return value;
}

/** Project paths stay inside the manifest directory and stay relative. */
export function checkRelativePath(value, label) {
  if (typeof value !== 'string' || !value.trim()) fail(`${label} must be a non-empty relative path`);
  const normalized = value.replaceAll('\\', '/');
  if (normalized.startsWith('/') || /^[A-Za-z]:/.test(normalized)) fail(`${label} must be relative: ${value}`);
  const parts = [];
  for (const part of normalized.split('/')) {
    if (part === '' || part === '.') continue;
    if (part === '..') fail(`${label} escapes the PPTD directory: ${value}`);
    parts.push(part);
  }
  if (!parts.length) fail(`${label} must name a file inside the PPTD directory`);
  return parts.join('/');
}

export function requireString(value, label) {
  if (typeof value !== 'string' || !value.trim()) fail(`${label} must be a non-empty string`);
  return value;
}
