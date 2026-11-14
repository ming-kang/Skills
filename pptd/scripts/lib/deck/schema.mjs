// Page/element geometry and animation validation. Shared styles, tables and charts
// each have one contract used by both validation and export preparation.

import {
  checkBounds,
  fail,
  isPlainObject,
  requireString,
} from './contract.mjs';
import { iconDefinition } from '../core/catalog.mjs';
import { checkHexColor } from '../core/color.mjs';
import { walkObjects } from '../core/walk.mjs';
import { checkChart } from './chart.mjs';
import { checkBorder, checkFill, checkShadow, checkStyle, registerImageSource, resolveStyle } from './style.mjs';
import { tableCells } from './table.mjs';

export const ELEMENT_TYPES = new Set(['text', 'shape', 'line', 'image', 'icon', 'table', 'chart']);
export const ANIMATION_EFFECTS = new Set([
  'appear', 'fade-in', 'fly-in', 'zoom-in', 'wipe-in', 'float-in', 'peek-in', 'rise-in',
  'pulse', 'grow-shrink', 'spin', 'teeter', 'fill-color', 'transparency', 'color-pulse',
  'disappear', 'fade-out', 'fly-out', 'zoom-out', 'wipe-out', 'float-out', 'motion-path',
]);
const TRIGGERS = new Set(['onClick', 'withPrevious', 'afterPrevious']);
const DIRECTIONS = new Set(['up', 'down', 'left', 'right']);
const EASINGS = new Set(['linear', 'ease-in', 'ease-out', 'ease-in-out']);
const LINE_CURVES = new Set(['sharp', 'round', 'smooth']);
const ARROW_TYPES = new Set(['arrow', 'stealth', 'diamond', 'oval']);
/** Shape and image-crop geometry: 177 preset names, or a custom SVG path with its viewBox. */
export function checkShape(shape, label, shapes) {
  if (!isPlainObject(shape)) fail(`${label} must be a shape mapping`);
  const name = shape.shapeName;
  if (name === 'custom') {
    if (typeof shape.path !== 'string' || !shape.path.trim()) fail(`${label}.path custom shapes require an SVG path`);
    const view = shape.viewBox;
    if (view !== undefined) {
      if (!Array.isArray(view) || view.length !== 2 || !view.every((item) => Number.isFinite(item) && item > 0)) {
        fail(`${label}.viewBox must contain two positive finite dimensions`);
      }
    } else if (shape.path.includes(';')) {
      const separator = shape.path.indexOf(';');
      const dims = shape.path.slice(0, separator).split(',').map(Number);
      if (dims.length !== 2 || !dims.every((item) => Number.isFinite(item) && item > 0) || !shape.path.slice(separator + 1).trim()) {
        fail(`${label}.path viewBox prefix must be "width,height;path" with positive dimensions`);
      }
    }
    return;
  }
  if (typeof name !== 'string' || !Object.hasOwn(shapes, name)) fail(`${label}.shapeName is an unknown shape: ${JSON.stringify(name)}`);
  if (shape.adjustments !== undefined) {
    if (!Array.isArray(shape.adjustments) || !shape.adjustments.every(Number.isFinite)) {
      fail(`${label}.adjustments must be an array of finite numbers`);
    }
    const meta = shapes[name];
    if (meta && typeof meta.adjustments === 'number' && shape.adjustments.length !== meta.adjustments) {
      fail(`${label}.adjustments for ${name} requires ${meta.adjustments} parameter(s), got ${shape.adjustments.length}`);
    }
  }
}

function checkLine(line, label) {
  const view = line.viewBox;
  if (!Array.isArray(view) || view.length !== 2 || !view.every((item) => Number.isFinite(item) && item > 0)) {
    fail(`${label}.viewBox must contain two positive finite dimensions`);
  }
  const points = requireString(line.points, `${label}.points`).trim().split(/\s+/);
  if (points.length < 2) fail(`${label}.points must contain at least 2 coordinate pairs`);
  for (const [index, pair] of points.entries()) {
    const coords = pair.split(',');
    if (coords.length !== 2 || coords.some((part) => !part.trim() || !Number.isFinite(Number(part)))) {
      fail(`${label}.points[${index}] must be an x,y coordinate pair`);
    }
  }
  if (line.curve !== undefined && !LINE_CURVES.has(line.curve)) {
    fail(`${label}.curve must be sharp, round or smooth`);
  }
  if (line.arrow !== undefined) {
    if (!Array.isArray(line.arrow) || line.arrow.length !== 2 || !line.arrow.every((a) => a === null || ARROW_TYPES.has(a))) {
      fail(`${label}.arrow must be a two-element array of arrow types or null`);
    }
  }
}

function checkAnimations(page, label) {
  const animations = page.animations ?? [];
  if (!Array.isArray(animations)) fail(`${label}.animations must be an array`);
  const ids = new Set(page.elements.map((element) => element.elementId));
  for (const [index, animation] of animations.entries()) {
    const field = `${label}.animations[${index}]`;
    if (!isPlainObject(animation)) fail(`${field} must be a mapping`);
    if (typeof animation.elementId !== 'string' || !ids.has(animation.elementId)) {
      fail(`${field}.elementId references an unknown element: ${JSON.stringify(animation.elementId)}`);
    }
    if (typeof animation.effect !== 'string' || !ANIMATION_EFFECTS.has(animation.effect)) {
      fail(`${field}.effect is unsupported: ${JSON.stringify(animation.effect)}`);
    }
    if ('trigger' in animation && !TRIGGERS.has(animation.trigger)) fail(`${field}.trigger is not a supported value`);
    if ('direction' in animation && !DIRECTIONS.has(animation.direction)) fail(`${field}.direction is not a supported value`);
    if ('easing' in animation && !EASINGS.has(animation.easing)) fail(`${field}.easing is not a supported value`);
    if ('durationMs' in animation && (!Number.isFinite(animation.durationMs) || animation.durationMs <= 0)) fail(`${field}.durationMs must be positive`);
    if ('delayMs' in animation && (!Number.isFinite(animation.delayMs) || animation.delayMs < 0)) fail(`${field}.delayMs must be non-negative`);
    if ('repeat' in animation && (!Number.isInteger(animation.repeat) || animation.repeat <= 0)) fail(`${field}.repeat must be a positive integer`);
    if (['fill-color', 'color-pulse'].includes(animation.effect)) checkHexColor(animation.color, `${field}.color`);
    if (animation.effect === 'transparency' && (!Number.isFinite(animation.amount) || animation.amount < 0 || animation.amount > 1)) {
      fail(`${field}.amount requires a target opacity in [0, 1]`);
    }
    if (animation.effect === 'motion-path') {
      const path = animation.path;
      if (typeof path !== 'string' || !/^\s*M\s*0[\s,]+0(?:\s|[LQCZ])/.test(path)) fail(`${field}.path motion paths must start with M 0 0`);
    }
    if (['float-in', 'float-out'].includes(animation.effect) && (animation.direction ?? 'up') !== 'up' && animation.direction !== 'down') {
      fail(`${field}.direction float animations support only up and down`);
    }
  }
}

function checkElement(element, index, pagePath, context) {
  const label = `${pagePath}: elements[${index}]`;
  if (!isPlainObject(element)) fail(`${label} must be a mapping`);
  const elementId = element.elementId;
  if (typeof elementId !== 'string' || !elementId.trim()) fail(`${label}.elementId must be a non-empty string`);
  if (context.seenIds.has(elementId)) fail(`${pagePath}: duplicate elementId: ${elementId}`);
  context.seenIds.add(elementId);
  const kind = element.elementType;
  if (typeof kind !== 'string' || !ELEMENT_TYPES.has(kind)) fail(`${label}.elementType is invalid: ${JSON.stringify(kind)}`);
  const field = `${label} (${elementId})`;
  const bounds = checkBounds(element.bounds, `${field}.bounds`);
  if (bounds[0] < 0 || bounds[1] < 0 || bounds[0] + bounds[2] > context.size[0] || bounds[1] + bounds[3] > context.size[1]) {
    context.warnings.push(`${field} extends beyond the slide canvas`);
  }
  if (element.rotation !== undefined && !Number.isFinite(element.rotation)) fail(`${field}.rotation must be finite`);
  if (element.opacity !== undefined && (!Number.isFinite(element.opacity) || element.opacity < 0 || element.opacity > 1)) {
    fail(`${field}.opacity must be in [0, 1]`);
  }
  checkBorder(element.border, `${field}.border`, context);
  checkShadow(element.shadow, `${field}.shadow`, context);
  if (element.fill !== undefined) checkFill(element.fill, `${field}.fill`, context);

  const themeColors = context.theme?.colors ?? {};
  if (kind === 'text') {
    const content = element.content;
    if (!isPlainObject(content) || typeof content.text !== 'string') fail(`${field}.content.text must be a string for text elements`);
    checkStyle(content, `${field}.content`, themeColors);
    resolveStyle(context.theme, 'textStyles', content.style, `${field}.content.style`);
  }
  if (kind === 'line') {
    checkLine(element, field);
  }
  if (kind === 'table') {
    tableCells(element, context.theme, field, context);
  }
  if (kind === 'shape' || (kind === 'image' && 'cropShape' in element)) {
    checkShape(kind === 'shape' ? element : element.cropShape, field, context.shapes);
    if (kind === 'shape' && ('content' in element || 'text' in element)) fail(`${field} shapes do not embed text; add a separate text element`);
  }
  if (kind === 'icon') {
    if (typeof element.iconName !== 'string' || !iconDefinition(element.iconName)) {
      fail(`${field}.iconName is an unknown bundled Font Awesome Free icon: ${JSON.stringify(element.iconName)}`);
    }
  }
  if (kind === 'image') {
    checkStyle(element, field, themeColors);
    registerImageSource(element.src, `${field}.src`, context);
  }
  if (kind === 'chart') {
    for (const [style, label] of walkObjects(element, field)) checkStyle(style, label, themeColors);
    context.warnings.push(...checkChart(element, field));
  }
}

/** Validate one page and collect the local media it references. */
export function checkPage(page, pagePath, context) {
  if (!isPlainObject(page) || !Array.isArray(page.elements)) fail(`page elements must be an array: ${pagePath}`);
  if ('notes' in page && typeof page.notes !== 'string') fail(`${pagePath}.notes must be a string`);
  if ('background' in page && page.background !== undefined) {
    checkFill(page.background, `${pagePath}.background`, context);
  }
  const pageContext = { ...context, seenIds: new Set() };
  for (const [index, element] of page.elements.entries()) checkElement(element, index, pagePath, pageContext);
  checkAnimations(page, pagePath);
}
