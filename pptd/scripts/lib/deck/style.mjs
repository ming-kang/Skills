// PPTD shared styles, fill/media references and named theme style resolution.
import { checkRelativePath, fail, isPlainObject, normalizeLocalPath, requireString } from './contract.mjs';
import { checkColorSpec as checkColor } from '../core/color.mjs';

const ALIGN_HORIZONTAL = new Set(['left', 'center', 'right', 'justify', 'distributed']);
const ALIGN_VERTICAL = new Set(['top', 'middle', 'bottom']);
const FILL_TYPES = new Set(['none', 'solid', 'gradient', 'image']);
const FIT_MODES = new Set(['fill', 'contain', 'cover']);

export { checkColor };

export function checkStyle(style, label, themeColors = null) {
  if (!isPlainObject(style)) return;
  for (const key of ['fontSize', 'lineHeight', 'lineHeightPx']) {
    if (key in style && style[key] !== undefined && (!Number.isFinite(style[key]) || style[key] <= 0)) {
      fail(`${label}.${key} must be positive and finite`);
    }
  }
  for (const key of ['letterSpacing', 'marginTop']) {
    if (key in style && style[key] !== undefined && !Number.isFinite(style[key])) {
      fail(`${label}.${key} must be a finite number`);
    }
  }
  if ('opacity' in style && style.opacity !== undefined && (!Number.isFinite(style.opacity) || style.opacity < 0 || style.opacity > 1)) {
    fail(`${label}.opacity must be in [0, 1]`);
  }
  if ('fontFamily' in style && style.fontFamily !== undefined) {
    const family = style.fontFamily;
    const names = isPlainObject(family) && [...Object.keys(family)].every((key) => key === 'latin' || key === 'ea')
      ? Object.values(family)
      : [family];
    if (!names.length || !names.every((name) => typeof name === 'string' && name.trim())) {
      fail(`${label}.fontFamily must be a font name or a {latin, ea} font mapping`);
    }
  }
  if ('align' in style && style.align !== undefined) {
    const align = style.align;
    if (!Array.isArray(align) || align.length !== 2 || !ALIGN_HORIZONTAL.has(align[0]) || !ALIGN_VERTICAL.has(align[1])) {
      fail(`${label}.align must contain horizontal and vertical alignment`);
    }
  }
  const crop = style.crop;
  if (crop !== undefined) {
    if (!isPlainObject(crop) || !Object.keys(crop).every((key) => ['left', 'right', 'top', 'bottom'].includes(key))) {
      fail(`${label}.crop must be an image crop mapping`);
    }
    if (!Object.values(crop).every(Number.isFinite)) fail(`${label}.crop fractions must be finite numbers`);
    const total = (a, b) => (crop[a] ?? 0) + (crop[b] ?? 0);
    if (total('left', 'right') >= 1 || total('top', 'bottom') >= 1) {
      fail(`${label}.crop left + right and top + bottom must each be less than 1`);
    }
  }
  const fit = style.fit;
  if (fit !== undefined && (!isPlainObject(fit) || !FIT_MODES.has(fit.mode))) fail(`${label}.fit must have mode fill, contain or cover`);
  if (style.type === 'gradient') checkColor(style, label, themeColors);
  if ('color' in style && style.color !== undefined) checkColor(style.color, `${label}.color`, themeColors);
  if ('backgroundColor' in style && style.backgroundColor !== undefined) checkColor(style.backgroundColor, `${label}.backgroundColor`, themeColors);
}

export function registerImageSource(src, label, context) {
  requireString(src, label);
  if (/^https?:\/\//i.test(src) || src.startsWith('data:')) return;
  const relative = checkRelativePath(normalizeLocalPath(src), label);
  if (context?.media && !context.media.has(relative)) {
    context.media.set(relative, { path: relative, label });
  }
}

export function checkFill(value, label, context = null) {
  const themeColors = context ? (context.theme?.colors ?? {}) : null;
  if (value === undefined || value === null) return value;
  if (typeof value === 'string') return checkColor(value, label, themeColors);
  if (!isPlainObject(value)) fail(`${label} must be a color or a fill mapping`);
  if (!FILL_TYPES.has(value.type)) fail(`${label}.type must be none, solid, gradient or image`);
  if (value.type === 'solid') checkColor(value.color, `${label}.color`, themeColors);
  if (value.type === 'gradient') checkColor(value, label, themeColors);
  if (value.type === 'image') {
    registerImageSource(value.src, `${label}.src`, context);
    checkStyle(value, label, themeColors);
  }
  return value;
}

export function checkBorder(value, label, context = null) {
  if (value === undefined || value === null) return;
  if (!isPlainObject(value)) fail(`${label} must be a border mapping`);
  if (value.width !== undefined && (!Number.isFinite(value.width) || value.width < 0)) fail(`${label}.width must be non-negative and finite`);
  if (value.style !== undefined && !['solid', 'dash', 'dot'].includes(value.style)) fail(`${label}.style must be solid, dash or dot`);
  if (value.color !== undefined) checkColor(value.color, `${label}.color`, context ? (context.theme?.colors ?? {}) : null);
}

export function checkBorderSpec(value, label, context = null) {
  if (value === undefined || value === null) return;
  if (Array.isArray(value)) {
    if (value.length !== 2 && value.length !== 4) {
      fail(`${label} border array must have 2 or 4 entries`);
    }
    for (const [index, side] of value.entries()) {
      if (side !== null) checkBorder(side, `${label}[${index}]`, context);
    }
    return;
  }
  checkBorder(value, label, context);
}

export function checkShadow(value, label, context = null) {
  if (value === undefined || value === null) return;
  if (!isPlainObject(value)) fail(`${label} must be a shadow mapping`);
  if (value.blur !== undefined && (!Number.isFinite(value.blur) || value.blur < 0)) fail(`${label}.blur must be non-negative and finite`);
  if (value.color !== undefined) checkColor(value.color, `${label}.color`, context ? (context.theme?.colors ?? {}) : null);
  if (value.offset !== undefined && (!Array.isArray(value.offset) || value.offset.length !== 2 || !value.offset.every(Number.isFinite))) {
    fail(`${label}.offset must be [x, y] with finite numbers`);
  }
}

/** Resolve either an inline style or a $name from one theme style collection. */
export function resolveStyle(theme, kind, reference, label) {
  if (reference === undefined || reference === null) return {};
  const config = typeof reference === 'string' ? theme[kind]?.[reference.slice(1)] : reference;
  const name = kind === 'textStyles' ? 'text' : 'table';
  if (typeof reference === 'string' && (reference[0] !== '$' || config === undefined)) {
    fail(`${label} references an unknown ${name} style: ${JSON.stringify(reference)}`);
  }
  if (!isPlainObject(config)) fail(`${label} must be a ${name} style mapping`);
  return config;
}
