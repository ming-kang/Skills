import fs from 'node:fs';
import path from 'node:path';
import { create as createFont } from '../../../assets/vendor/fontkit.mjs';
import { parseXml, serializeNode } from '../core/xml.mjs';
import { extractEotSfnt } from './font_data.mjs';
import { EAST_ASIAN, splitCss } from './fonts.mjs';

const SVG = 'http://www.w3.org/2000/svg';
const XML = 'http://www.w3.org/XML/1998/namespace';
const SLOTS = new Set(['regular', 'bold', 'italic', 'boldItalic']);
// Controlled, advance-preserving synthesis, not a replacement font or guessed metrics.
const SYNTHETIC_SLANT = Math.tan(12 * Math.PI / 180);
const SYNTHETIC_BOLD_EM = 0.03;
const graphemes = new Intl.Segmenter('und', { granularity: 'grapheme' });
const key = (name) => name.trim().toLowerCase().replace(/[\s_-]+/gu, '');
const num = (value) => String(Object.is(value, -0) ? 0 : value);
const children = (node) => Array.from(node.childNodes ?? []);
const attributes = (node) => Array.from(node.attributes ?? []);

const LENGTH_FACTORS = { px: 1, pt: 96 / 72, pc: 16, in: 96, cm: 96 / 2.54, mm: 96 / 25.4 };
const SIMPLE_SCRIPTS = [
  [/\p{Script=Latin}/u, 'latn'], [/\p{Script=Greek}/u, 'grek'], [/\p{Script=Cyrillic}/u, 'cyrl'],
  [/\p{Script=Han}/u, 'hani'], [/[\p{Script=Hiragana}\p{Script=Katakana}]/u, 'kana'],
  [/\p{Script=Hangul}/u, 'hang'], [/\p{Script=Bopomofo}/u, 'bopo'],
];
const scriptFor = (cluster) => SIMPLE_SCRIPTS.find(([pattern]) => pattern.test(cluster))?.[1];

// Properties ECharts SSR does not customize; fail closed if any non-default value appears.
const DEFAULT_ONLY = {
  font: ['initial'], 'font-stretch': ['normal', '100%'], 'font-variant': ['normal'],
  'font-variant-ligatures': ['normal'], 'font-variant-caps': ['normal'], 'font-variant-numeric': ['normal'],
  'font-variant-east-asian': ['normal'], 'font-variant-position': ['normal'],
  'font-feature-settings': ['normal'], 'font-variation-settings': ['normal'],
  'font-optical-sizing': ['auto'], 'font-kerning': ['auto', 'normal'], 'font-size-adjust': ['none'],
  'letter-spacing': ['normal', '0', '0px'], 'word-spacing': ['normal', '0', '0px'], kerning: ['auto'],
  'baseline-shift': ['baseline', '0', '0px', '0em', '0%'],
  direction: ['ltr'], 'unicode-bidi': ['normal'], 'writing-mode': ['horizontal-tb', 'lr', 'lr-tb'],
  'text-orientation': ['mixed'], 'text-decoration': ['none'], 'text-decoration-line': ['none'],
  'text-transform': ['none'], 'text-shadow': ['none'], 'line-height': ['normal'],
  'inline-size': ['auto'], 'text-indent': ['0', '0px'],
};
const SUPPORTED_PROPS = new Set(['font-family', 'font-size', 'font-weight', 'font-style', 'text-anchor', 'text-rendering']);
const ENUMS = {
  weight: ['normal', 'bold', '400', '700'],
  fontStyle: ['normal', 'italic', 'oblique'],
  anchor: ['start', 'middle', 'end'],
  baseline: ['auto', 'alphabetic', 'central', 'middle'],
  whiteSpace: ['normal', 'pre'],
};

function isRenderingContent(node) {
  for (let parent = node.parentNode; parent?.nodeType === 1; parent = parent.parentNode) {
    if (parent.namespaceURI === SVG && ['metadata', 'title', 'desc'].includes(parent.localName)) return false;
  }
  return true;
}

function inlineStyle(node) {
  const declarations = new Map();
  const value = node.getAttribute('style') ?? '';
  if (value.includes('/*')) throw new Error('comments in inline SVG CSS are unsupported');
  for (const part of splitCss(value, ';')) {
    if (!part.trim()) continue;
    const pieces = splitCss(part, ':');
    if (pieces.length !== 2 || !pieces[0].trim() || !pieces[1].trim()) {
      throw new Error(`unsupported inline SVG CSS declaration: ${part}`);
    }
    const property = pieces[0].trim().toLowerCase();
    const important = /\s*!important\s*$/i.test(pieces[1]);
    const text = pieces[1].replace(/\s*!important\s*$/i, '').trim();
    if (!declarations.get(property)?.important || important) declarations.set(property, { value: text, important });
  }
  return declarations;
}

function familyNames(value) {
  if (typeof value !== 'string' || !value.trim()) throw new Error('SVG text needs an explicit selected font-family');
  return splitCss(value, ',').map((part) => {
    let name = part.trim();
    if ((name[0] === '"' || name[0] === "'") && name.at(-1) === name[0]) name = name.slice(1, -1);
    else if (/['"]/.test(name)) throw new Error(`invalid SVG font-family: ${value}`);
    if (!name.trim()) throw new Error(`empty SVG font-family candidate: ${value}`);
    return name;
  });
}

function length(value, property, em, fontSize = false) {
  const match = /^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)(px|em|%|pt|pc|in|cm|mm)?$/i.exec(value.trim());
  if (!match || (!fontSize && match[2] && match[2].toLowerCase() !== 'px')) {
    throw new Error(`unsupported SVG ${property}: ${value}; positioning must be a single number or px length`);
  }
  const unit = (match[2] ?? 'px').toLowerCase();
  const factor = unit === 'em' ? em : unit === '%' ? em / 100 : LENGTH_FACTORS[unit] ?? 1;
  const result = Number(match[1]) * factor;
  if (!Number.isFinite(result) || (fontSize && result <= 0)) throw new Error(`invalid SVG ${property}: ${value}`);
  return result;
}

function textState(node, cache, styleCache) {
  if (cache.has(node)) return cache.get(node);
  const defaults = {
    family: undefined, size: 16, weight: 'normal', fontStyle: 'normal',
    anchor: 'start', baseline: 'auto', whiteSpace: 'normal', fill: 'black', stroke: 'none', fillOpacity: '1',
  };
  const parent = node.parentNode?.nodeType === 1 ? textState(node.parentNode, cache, styleCache) : defaults;
  const state = { ...parent };
  const styles = inlineStyle(node);
  styleCache.set(node, styles);
  const local = (name) => styles.get(name)?.value ?? (node.hasAttribute(name) ? node.getAttribute(name) : undefined);

  for (const attr of attributes(node)) {
    if (attr.namespaceURI === XML && attr.localName === 'space') {
      if (attr.value !== 'default' && attr.value !== 'preserve') throw new Error(`unsupported SVG xml:space: ${attr.value}`);
      state.whiteSpace = attr.value === 'preserve' ? 'pre' : 'normal';
    } else if (((attr.namespaceURI === XML && attr.localName === 'lang') || attr.name === 'lang') && attr.value.trim()) {
      throw new Error('language-specific SVG shaping is unsupported by this chart adapter');
    }
  }

  for (const prop of new Set([...Object.keys(DEFAULT_ONLY), ...styles.keys(), ...attributes(node).map((a) => a.name)])) {
    const val = local(prop);
    if (val === undefined) continue;
    const norm = val.trim().toLowerCase();
    if (Object.hasOwn(DEFAULT_ONLY, prop)) {
      if (prop === 'font' && norm !== 'initial' && norm !== 'inherit' && norm !== 'unset') {
        throw new Error('SVG font shorthand is unsupported; use font-family/font-size/font-weight/font-style');
      }
      if (!['inherit', 'unset', 'initial', ...DEFAULT_ONLY[prop]].includes(norm)) {
        throw new Error(`unsupported SVG text property ${prop}=${val}`);
      }
    } else if ((prop.startsWith('font-') || prop.startsWith('text-') || prop.startsWith('glyph-orientation-')) && !SUPPORTED_PROPS.has(prop)) {
      throw new Error(`unsupported SVG text property ${prop}=${val}`);
    }
  }

  const resolve = (val, prev, init) => (/^(inherit|unset)$/i.test(val) ? prev : /^initial$/i.test(val) ? init : val);
  const fam = local('font-family');
  if (fam !== undefined) state.family = resolve(fam.trim(), parent.family, 'sans-serif');
  const size = local('font-size');
  if (size !== undefined) {
    state.size = /^(inherit|unset)$/i.test(size) ? parent.size : /^initial$/i.test(size) ? 16 : length(size, 'font-size', parent.size, true);
  }
  for (const [prop, field] of [
    ['font-weight', 'weight'], ['font-style', 'fontStyle'], ['text-anchor', 'anchor'],
    ['dominant-baseline', 'baseline'], ['white-space', 'whiteSpace'],
    ['fill', 'fill'], ['stroke', 'stroke'], ['fill-opacity', 'fillOpacity'],
  ]) {
    const val = local(prop);
    if (val !== undefined) state[field] = resolve(val.trim(), parent[field], defaults[field]);
  }
  for (const field of Object.keys(ENUMS)) {
    state[field] = state[field].toLowerCase();
    if (!ENUMS[field].includes(state[field])) throw new Error(`unsupported SVG ${field}: ${state[field]}`);
  }
  const alignment = local('alignment-baseline');
  if (alignment !== undefined && !['auto', 'baseline', 'alphabetic', 'inherit', 'unset', 'initial'].includes(alignment.trim().toLowerCase())) {
    throw new Error(`unsupported SVG alignment-baseline: ${alignment}`);
  }
  if (node.localName === 'text' && alignment?.trim().toLowerCase() === 'alphabetic') state.baseline = 'alphabetic';
  cache.set(node, state);
  return state;
}

function checkStylesheets(document, texts) {
  const textClasses = new Set();
  for (const text of texts) {
    for (let node = text; node?.nodeType === 1; node = node.parentNode) {
      for (const name of (node.getAttribute('class') ?? '').split(/\s+/)) if (name) textClasses.add(name);
    }
  }
  for (const style of Array.from(document.getElementsByTagNameNS(SVG, 'style')).filter(isRenderingContent)) {
    const rest = style.textContent.replace(/\/\*[\s\S]*?\*\//g, '').replace(/([^{}]+)\{([^{}]*)\}/g, (_, selectors) => {
      for (const selector of selectors.split(',')) {
        const match = /^\.([\w-]+)(?::(?:hover|active|focus))?$/.exec(selector.trim());
        if (!match || textClasses.has(match[1])) throw new Error(`stylesheet styling of outlined SVG text is unsupported: ${selector.trim()}`);
      }
      return '';
    });
    if (rest.trim()) throw new Error('unsupported SVG stylesheet syntax');
  }
}

function checkTextCharacters(text) {
  for (const char of text) {
    if (/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u206f]/u.test(char) ||
        !/[\p{Script=Latin}\p{Script=Greek}\p{Script=Cyrillic}\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}\p{Script=Bopomofo}\p{Script=Common}\p{Script=Inherited}]/u.test(char)) {
      throw new Error(`SVG chart text needs unsupported bidi/complex-script itemization at U+${char.codePointAt(0).toString(16).toUpperCase()}`);
    }
  }
}

/**
 * Create a synchronous SVG-text-to-glyph-path adapter. Descriptors are selected
 * family/slot faces: { family, slot, path: absoluteFile, face: TTCIndex, eot }.
 */
export function createSvgFontOutliner(descriptors) {
  if (!Array.isArray(descriptors)) throw new TypeError('SVG font descriptors must be an array');
  const families = new Map(), fonts = new Map(), files = new Map();
  for (const input of descriptors) {
    if (!input || typeof input.family !== 'string' || !input.family.trim() || !SLOTS.has(input.slot) ||
        typeof input.path !== 'string' || !path.isAbsolute(input.path) ||
        (input.eot !== undefined && typeof input.eot !== 'boolean') ||
        !Number.isInteger(input.face ?? 0) || (input.face ?? 0) < 0) {
      throw new TypeError('invalid SVG font descriptor; expected family, slot, absolute path, non-negative face index and boolean eot');
    }
    const descriptor = { ...input, face: input.face ?? 0, eot: input.eot ?? false };
    const name = key(descriptor.family);
    if (!families.has(name)) families.set(name, new Map());
    const slots = families.get(name), previous = slots.get(descriptor.slot);
    if (previous && (previous.path !== descriptor.path || previous.face !== descriptor.face || previous.eot !== descriptor.eot)) {
      throw new Error(`conflicting SVG font descriptors for ${descriptor.family} ${descriptor.slot}`);
    }
    slots.set(descriptor.slot, descriptor);
  }

  function load(descriptor) {
    const fileKey = JSON.stringify([descriptor.path, descriptor.eot]);
    const faceKey = JSON.stringify([fileKey, descriptor.face]);
    if (!fonts.has(faceKey)) {
      try {
        if (!files.has(fileKey)) {
          const buffer = fs.readFileSync(descriptor.path);
          files.set(fileKey, descriptor.eot ? extractEotSfnt(buffer) : buffer);
        }
        const container = createFont(files.get(fileKey));
        const font = container.type === 'TTC' ? container.fonts[descriptor.face] : descriptor.face === 0 ? container : undefined;
        if (!font || typeof font.layout !== 'function' || !Number.isFinite(font.unitsPerEm) || font.unitsPerEm <= 0 ||
            !Number.isFinite(font.ascent) || !Number.isFinite(font.descent)) throw new Error('invalid outline face or collection index');
        const tables = font.directory?.tables ?? {};
        if (!(tables.glyf || tables['CFF '] || tables.CFF2)) throw new Error('font has no scalable glyph outlines');
        if (['COLR', 'CPAL', 'sbix', 'CBDT', 'CBLC', 'EBDT', 'EBLC', 'SVG '].some((tag) => tables[tag])) {
          throw new Error('color/bitmap glyph fonts are unsupported by the monochrome SVG outliner');
        }
        fonts.set(faceKey, font);
      } catch (error) {
        throw new Error(`cannot outline SVG chart with ${descriptor.family} ${descriptor.slot} (face ${descriptor.face}): ${error.message}`, { cause: error });
      }
    }
    return fonts.get(faceKey);
  }

  function faceFor(name, bold, italic) {
    const slots = families.get(key(name));
    if (!slots) return undefined;
    const requested = bold && italic ? 'boldItalic' : bold ? 'bold' : italic ? 'italic' : 'regular';
    const choices = requested === 'boldItalic' ? ['boldItalic', 'bold', 'italic', 'regular'] : [requested, 'regular'];
    const descriptor = choices.map((slot) => slots.get(slot)).find(Boolean);
    if (!descriptor) throw new Error(`SVG font ${name} has no ${requested} or usable regular face; refusing a wrong style`);
    return {
      descriptor,
      font: load(descriptor),
      syntheticBold: bold && !['bold', 'boldItalic'].includes(descriptor.slot),
      syntheticItalic: italic && !['italic', 'boldItalic'].includes(descriptor.slot),
    };
  }

  return function outlineSvg(input) {
    let document;
    const returnDocument = typeof input === 'object' && input !== null && input.documentElement;
    if (returnDocument) {
      document = input;
    } else if (typeof input === 'string') {
      if (/<!DOCTYPE|<!ENTITY|<\?xml-stylesheet\b/i.test(input)) throw new Error('DTD/entities/external stylesheets are unsupported in chart SVG');
      document = parseXml(input, 'chart SVG', { mime: 'image/svg+xml' });
    } else {
      throw new TypeError('SVG font outliner expects an SVG string or Document');
    }
    if (document.documentElement?.localName !== 'svg' || document.documentElement.namespaceURI !== SVG) {
      throw new Error('font outliner expects a namespaced SVG root');
    }
    const texts = Array.from(document.getElementsByTagNameNS(SVG, 'text')).filter(isRenderingContent);
    if (!texts.length) return input;
    checkStylesheets(document, texts);
    const stateCache = new WeakMap(), styleCache = new WeakMap();

    for (const text of texts) {
      try {
        if (children(text).some((node) => ![3, 4, 8].includes(node.nodeType))) {
          throw new Error('only plain SVG text nodes are supported (no tspan/textPath/nested markup)');
        }
        const state = textState(text, stateCache, styleCache);
        const styles = styleCache.get(text);
        for (const name of ['textLength', 'lengthAdjust', 'rotate', 'text-length', 'length-adjust']) {
          if (text.hasAttribute(name) || styles.has(name.toLowerCase())) {
            throw new Error(`unsupported SVG text positioning property/attribute: ${name}`);
          }
        }
        const position = (name) => length(styles.get(name)?.value ?? (text.hasAttribute(name) ? text.getAttribute(name) : '0'), name, state.size);
        const x = position('x') + position('dx'), y = position('y') + position('dy');
        let content = text.textContent;
        if (state.whiteSpace === 'pre') {
          if (/[\t\r\n]/.test(content)) throw new Error('multiline/tab-preserved SVG text is unsupported; SSR must emit separate positioned text nodes');
        } else content = content.replace(/[\t\r\n ]+/g, ' ').trim();
        checkTextCharacters(content);

        const names = familyNames(state.family);
        const bold = state.weight === 'bold' || state.weight === '700', italic = state.fontStyle !== 'normal';
        const candidates = new Map();
        const candidate = (name) => {
          if (!candidates.has(key(name))) candidates.set(key(name), faceFor(name, bold, italic));
          return candidates.get(key(name));
        };
        const runs = [];
        let primary;
        for (const { segment } of graphemes.segment(content)) {
          const available = [...names];
          if (EAST_ASIAN.test(segment) && families.has(key('Noto Sans SC')) && !available.some((name) => key(name) === key('Noto Sans SC'))) {
            available.push('Noto Sans SC');
          }
          let selected;
          for (const name of available) {
            const face = candidate(name);
            if (!face) continue;
            primary ??= face.font;
            if (Array.from(segment).every((char) => /\p{Default_Ignorable_Code_Point}/u.test(char) || face.font.hasGlyphForCodePoint(char.codePointAt(0)))) {
              selected = face;
              break;
            }
          }
          if (!selected) throw new Error(`no selected SVG font covers ${JSON.stringify(segment)} in ${names.join(', ')}; supply a covering face (Noto Sans SC for Chinese)`);
          const last = runs.at(-1), script = scriptFor(segment);
          if (last?.face === selected && (!script || !last.script || script === last.script)) {
            last.script ??= script;
            last.text += segment;
          } else runs.push({ face: selected, text: segment, script });
        }

        let advance = 0;
        for (const run of runs) {
          run.layout = run.face.font.layout(run.text, undefined, run.script);
          run.scale = state.size / run.face.font.unitsPerEm;
          if (!Number.isFinite(run.scale) || run.scale <= 0) throw new Error('invalid font outline scale');
          if (run.layout.direction !== 'ltr') throw new Error('RTL SVG glyph runs require unsupported bidi layout');
          if (run.layout.glyphs.length !== run.layout.positions.length) throw new Error('invalid fontkit glyph positioning');
          for (const pos of run.layout.positions) {
            if (!['xAdvance', 'yAdvance', 'xOffset', 'yOffset'].every((n) => Number.isFinite(pos[n])) || pos.yAdvance !== 0) {
              throw new Error('unsupported/non-finite horizontal glyph positioning');
            }
            advance += pos.xAdvance * run.scale;
          }
        }
        if (!Number.isFinite(advance)) throw new Error('non-finite SVG glyph advance');
        const originX = x - advance * (state.anchor === 'middle' ? 0.5 : state.anchor === 'end' ? 1 : 0);
        let baselineY = y;
        if (primary && state.baseline === 'central') baselineY += (primary.ascent + primary.descent) * state.size / primary.unitsPerEm / 2;
        if (primary && state.baseline === 'middle') {
          if (!Number.isFinite(primary.xHeight) || primary.xHeight <= 0) throw new Error('middle SVG baseline needs real font x-height metrics');
          baselineY += primary.xHeight * state.size / primary.unitsPerEm / 2;
        }
        if (![originX, baselineY].every(Number.isFinite)) throw new Error('non-finite SVG text origin/baseline');

        const group = document.createElementNS(SVG, 'g');
        for (const attr of attributes(text)) {
          if (!['x', 'y', 'dx', 'dy', 'dominant-baseline', 'alignment-baseline'].includes(attr.name)) {
            group.setAttributeNS(attr.namespaceURI, attr.name, attr.value);
          }
        }
        group.setAttribute('data-pptd-text', content);
        group.setAttribute('data-pptd-advance', num(advance));
        group.setAttribute('data-pptd-origin', `${num(originX)} ${num(baselineY)}`);
        const used = [...new Set(runs.map(({ face }) => `${face.descriptor.family}/${face.descriptor.slot}${face.syntheticBold ? '+synthetic-bold' : ''}${face.syntheticItalic ? '+synthetic-italic' : ''}`))];
        group.setAttribute('data-pptd-fonts', JSON.stringify(used));
        if (!text.hasAttribute('aria-label')) group.setAttribute('aria-label', content);

        let pen = originX;
        const outlines = [];
        for (const run of runs) {
          const { font, syntheticBold, syntheticItalic } = run.face;
          if (syntheticBold && state.stroke.trim().toLowerCase() !== 'none') {
            throw new Error('synthetic bold on stroked SVG text is unsupported; supply a real bold face');
          }
          const slant = syntheticItalic ? SYNTHETIC_SLANT : 0;
          for (let i = 0; i < run.layout.glyphs.length; i++) {
            const glyph = run.layout.glyphs[i], pos = run.layout.positions[i];
            if (glyph.id === 0) throw new Error(`font ${font.familyName} produced a missing glyph during shaping`);
            const glyphPath = glyph.path;
            if (!glyphPath || glyphPath.commands.some((cmd) => cmd.args.some((v) => !Number.isFinite(v)))) {
              throw new Error('invalid/non-vector glyph path');
            }
            const transformed = glyphPath.transform(
              run.scale, 0, slant * run.scale, -run.scale,
              pen + (pos.xOffset + slant * pos.yOffset) * run.scale,
              baselineY - pos.yOffset * run.scale,
            );
            if (transformed.commands.some((cmd) => cmd.args.some((v) => !Number.isFinite(v)))) {
              throw new Error('non-finite transformed SVG glyph path');
            }
            const data = transformed.toSVG();
            if (data) outlines.push({ data, syntheticBold });
            pen += pos.xAdvance * run.scale;
          }
        }
        if (/url\s*\(/i.test(state.fill) && outlines.some((o) => o.syntheticBold) && outlines.some((o) => !o.syntheticBold)) {
          throw new Error('mixed synthetic/real bold with an SVG paint server is unsupported; supply matching real faces');
        }
        for (const syntheticBold of [false, true]) {
          const data = outlines.filter((o) => o.syntheticBold === syntheticBold).map((o) => o.data).join('');
          if (!data) continue;
          const outline = document.createElementNS(SVG, 'path');
          outline.setAttribute('d', data);
          if (syntheticBold) {
            outline.setAttribute('stroke', state.fill);
            outline.setAttribute('stroke-width', num(state.size * SYNTHETIC_BOLD_EM));
            outline.setAttribute('stroke-opacity', state.fillOpacity);
            outline.setAttribute('stroke-linecap', 'round');
            outline.setAttribute('stroke-linejoin', 'round');
            outline.setAttribute('stroke-dasharray', 'none');
            outline.setAttribute('style', 'paint-order:stroke fill;');
          }
          group.appendChild(outline);
        }
        text.parentNode.replaceChild(group, text);
      } catch (error) {
        throw new Error(`cannot outline SVG text ${JSON.stringify(text.textContent.slice(0, 100))}: ${error.message}`, { cause: error });
      }
    }
    return returnDocument ? document : serializeNode(document);
  };
}
