// Shared invariants for every deck value that can reach OOXML, plus path containment,
// element normalization and the JSON/YAML boundary.

import fs from 'node:fs';
import path from 'node:path';

import { checkXmlString } from '../core/xml.mjs';

export const ADVANCED_CHART_TYPES = new Set(['heatmap', 'treemap', 'sunburst', 'sankey']);

export function fail(message) {
  throw new Error(message);
}

export function isPlainObject(value) {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** Every string that can reach OOXML, and the JSON boundary itself. */
export function checkJsonValue(value, label) {
  if (typeof value === 'string') {
    checkXmlString(value, label);
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
  if (!Array.isArray(value) || value.length !== 4 || !value.every(Number.isFinite)) {
    fail(`${label} must be [x, y, width, height] with finite numbers`);
  }
  if (value[2] <= 0 || value[3] <= 0) fail(`${label} width and height must be positive`);
  return value;
}

/** Strip relative `file://` prefix without masking absolute `file:///...` paths. */
export function normalizeLocalPath(value) {
  return String(value).replace(/^file:\/\//i, '');
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

/** Verify a project-relative path exists as a real regular file without symlink escape. */
export function checkContainedFile(root, realRoot, relative, label, missingMessage = null) {
  const resolved = path.join(root, relative);
  if (!fs.existsSync(resolved) || !fs.statSync(resolved).isFile()) {
    fail(missingMessage ?? `${label}: missing local file: ${relative}`);
  }
  const rootPrefix = realRoot.endsWith(path.sep) ? realRoot : realRoot + path.sep;
  const realTarget = fs.realpathSync(resolved);
  if (realTarget !== realRoot && !realTarget.startsWith(rootPrefix)) {
    fail(`${label} escapes the PPTD directory: ${relative}`);
  }
  return realTarget;
}

export function requireString(value, label) {
  if (typeof value !== 'string' || !value.trim()) fail(`${label} must be a non-empty string`);
  return value;
}

/** The writer's custom-shape path may carry a `width,height;` prefix instead of a viewBox. */
function normalizeCustomShape(shape, size) {
  if (shape?.shapeName !== 'custom' || !shape.path || shape.viewBox) return shape;
  const separator = String(shape.path).indexOf(';');
  if (separator >= 0) {
    const [width, height] = String(shape.path).slice(0, separator).split(',').map(Number);
    return { ...shape, viewBox: [width, height], path: String(shape.path).slice(separator + 1) };
  }
  return { ...shape, viewBox: size };
}

export function normalizeElement(element) {
  const size = [element.bounds?.[2], element.bounds?.[3]];
  if (element.elementType === 'shape') return normalizeCustomShape(element, size);
  if (element.elementType === 'image' && element.cropShape) {
    return { ...element, cropShape: normalizeCustomShape(element.cropShape, size) };
  }
  return element;
}
