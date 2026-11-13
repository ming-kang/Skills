import fs from 'node:fs';
import path from 'node:path';
import { create as createFont } from '../../../assets/vendor/fontkit.mjs';
import { DOMParser, XMLSerializer } from '../../../assets/vendor/xmldom.mjs';

const SVG = 'http://www.w3.org/2000/svg';
const XML = 'http://www.w3.org/XML/1998/namespace';
const SLOTS = new Set(['regular', 'bold', 'italic', 'boldItalic']);
// Controlled, advance-preserving synthesis, not a replacement font or guessed metrics.
const SYNTHETIC_SLANT = Math.tan(12 * Math.PI / 180);
const SYNTHETIC_BOLD_EM = 0.03;
const graphemes = new Intl.Segmenter('und', { granularity: 'grapheme' });
const serializer = new XMLSerializer();
const key = (name) => name.trim().toLowerCase().replace(/[\s_-]+/gu, '');
const number = (value) => String(Object.is(value, -0) ? 0 : value);
const children = (node) => Array.from(node.childNodes ?? []);
const attributes = (node) => Array.from(node.attributes ?? []);
function isRenderingContent(node) {
  for (let parent = node.parentNode; parent?.nodeType === 1; parent = parent.parentNode) {
    if (parent.namespaceURI === SVG && ['metadata', 'title', 'desc'].includes(parent.localName)) return false;
  }
  return true;
}

// CSS token boundaries, including quoted family names and paint url(...) values.
function splitCss(value, delimiter) {
  const result = [];
  let start = 0, quote = '', depth = 0;
  for (let i = 0; i < value.length; i++) {
    const char = value[i];
    if (char === '\\') { i++; continue; }
    if (quote) { if (char === quote) quote = ''; continue; }
    if (char === '"' || char === "'") { quote = char; continue; }
    if (char === '(') depth++;
    else if (char === ')') depth--;
    else if (char === delimiter && depth === 0) { result.push(value.slice(start, i)); start = i + 1; }
    if (depth < 0) throw new Error('unbalanced inline SVG CSS');
  }
  if (quote || depth) throw new Error('unbalanced inline SVG CSS');
  result.push(value.slice(start));
  return result;
}

function inlineStyle(node) {
  const declarations = new Map();
  const value = node.getAttribute('style') ?? '';
  // SSR does not emit comments in declarations. Do not "repair" ambiguous CSS.
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
    name = name.replace(/\\([\da-f]{1,6})(?:\r\n|[ \t\r\n\f])?|\\([^\r\n\f])/gi, (_, hex, char) => {
      if (!hex) return char;
      const code = parseInt(hex, 16);
      return String.fromCodePoint(!code || code > 0x10ffff || (code >= 0xd800 && code <= 0xdfff) ? 0xfffd : code);
    });
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
  const factors = { px: 1, em, '%': em / 100, pt: 96 / 72, pc: 16, in: 96, cm: 96 / 2.54, mm: 96 / 25.4 };
  const result = Number(match[1]) * factors[unit];
  if (!Number.isFinite(result) || (fontSize && result <= 0)) throw new Error(`invalid SVG ${property}: ${value}`);
  return result;
}

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
const FONT_PROPERTIES = new Set(['font-family', 'font-size', 'font-weight', 'font-style']);
const TEXT_PROPERTIES = new Set(['text-anchor', 'text-rendering']);
const inheritedValue = (value, previous, initial) => /^(inherit|unset)$/i.test(value) ? previous : /^initial$/i.test(value) ? initial : value;

function textState(node, cache, styleCache) {
  if (cache.has(node)) return cache.get(node);
  const defaults = { family: undefined, size: 16, weight: 'normal', fontStyle: 'normal', anchor: 'start', baseline: 'auto', whiteSpace: 'normal', xmlSpace: 'default', fill: 'black', stroke: 'none', fillOpacity: '1' };
  const parent = node.parentNode?.nodeType === 1 ? textState(node.parentNode, cache, styleCache) : defaults;
  const state = { ...parent };
  const styles = inlineStyle(node);
  styleCache.set(node, styles);
  const local = (name) => styles.get(name)?.value ?? (node.hasAttribute(name) ? node.getAttribute(name) : undefined);
  for (const attribute of attributes(node)) {
    if (attribute.namespaceURI === XML && attribute.localName === 'space') {
      if (!['default', 'preserve'].includes(attribute.value)) throw new Error(`unsupported SVG xml:space: ${attribute.value}`);
      state.xmlSpace = attribute.value;
      state.whiteSpace = attribute.value === 'preserve' ? 'pre' : 'normal';
    }
    if ((attribute.namespaceURI === XML && attribute.localName === 'lang') || attribute.name === 'lang') {
      if (attribute.value.trim()) throw new Error('language-specific SVG shaping is unsupported by this chart adapter');
    }
  }
  const properties = new Set([...Object.keys(DEFAULT_ONLY), ...styles.keys(), ...attributes(node).map((attr) => attr.name)]);
  for (const property of properties) {
    const value = local(property);
    if (value === undefined) continue;
    const normalized = value.trim().toLowerCase();
    if (Object.hasOwn(DEFAULT_ONLY, property)) {
      if (!['inherit', 'unset', 'initial', ...DEFAULT_ONLY[property]].includes(normalized)) {
        throw new Error(`unsupported SVG text property ${property}=${value}`);
      }
      // An explicit font shorthand would reset inherited face/size/weight; do not ignore it.
      if (property === 'font') throw new Error('SVG font shorthand is unsupported; use font-family/font-size/font-weight/font-style');
    } else if ((property.startsWith('font-') && !FONT_PROPERTIES.has(property)) ||
               (property.startsWith('text-') && !TEXT_PROPERTIES.has(property)) ||
               property.startsWith('glyph-orientation-')) {
      throw new Error(`unsupported SVG text property ${property}=${value}`);
    }
  }
  const apply = (property, field, initial = defaults[field]) => {
    const value = local(property);
    if (value !== undefined) state[field] = inheritedValue(value.trim(), parent[field], initial);
  };
  apply('font-family', 'family', 'sans-serif');
  const size = local('font-size');
  if (size !== undefined) state.size = /^(inherit|unset)$/i.test(size) ? parent.size : /^initial$/i.test(size) ? 16 : length(size, 'font-size', parent.size, true);
  for (const [property, field] of [['font-weight', 'weight'], ['font-style', 'fontStyle'], ['text-anchor', 'anchor'], ['dominant-baseline', 'baseline'], ['white-space', 'whiteSpace'], ['fill', 'fill'], ['stroke', 'stroke'], ['fill-opacity', 'fillOpacity']]) apply(property, field);
  for (const field of ['weight', 'fontStyle', 'anchor', 'baseline', 'whiteSpace']) state[field] = state[field].toLowerCase();
  if (!['normal', 'bold', '400', '700'].includes(state.weight)) throw new Error(`SVG font-weight ${state.weight} cannot be represented by regular/bold face slots`);
  if (!['normal', 'italic', 'oblique'].includes(state.fontStyle)) throw new Error(`unsupported SVG font-style: ${state.fontStyle}`);
  if (!['start', 'middle', 'end'].includes(state.anchor)) throw new Error(`unsupported SVG text-anchor: ${state.anchor}`);
  if (!['auto', 'alphabetic', 'central', 'middle'].includes(state.baseline)) throw new Error(`unsupported SVG dominant-baseline: ${state.baseline}`);
  if (!['normal', 'pre'].includes(state.whiteSpace)) throw new Error(`unsupported SVG white-space: ${state.whiteSpace}`);
  const alignment = local('alignment-baseline');
  if (alignment !== undefined && !['auto', 'baseline', 'alphabetic', 'inherit', 'unset', 'initial'].includes(alignment.trim().toLowerCase())) {
    throw new Error(`unsupported SVG alignment-baseline: ${alignment}`);
  }
  // alignment-baseline is not inherited. Alphabetic on the text explicitly selects that baseline.
  if (node.localName === 'text' && alignment?.trim().toLowerCase() === 'alphabetic') state.baseline = 'alphabetic';
  cache.set(node, state);
  return state;
}

// No stylesheet font cascade is guessed. ECharts SSR's class-only hover rules target
// untouched chart paths, not text or its ancestors; retain those rules verbatim.
function checkStylesheets(document, texts) {
  const textClasses = new Set();
  for (const text of texts) {
    for (let node = text; node?.nodeType === 1; node = node.parentNode) {
      for (const name of (node.getAttribute('class') ?? '').split(/\s+/)) if (name) textClasses.add(name);
    }
  }
  for (const style of Array.from(document.getElementsByTagNameNS(SVG, 'style')).filter(isRenderingContent)) {
    let css = style.textContent.replace(/\/\*[\s\S]*?\*\//g, '');
    css = css.replace(/([^{}]+)\{([^{}]*)\}/g, (_, selectors) => {
      for (const selector of selectors.split(',')) {
        const match = /^\.([\w-]+)(?::(?:hover|active|focus))?$/.exec(selector.trim());
        if (!match || textClasses.has(match[1])) throw new Error(`stylesheet styling of outlined SVG text is unsupported: ${selector.trim()}`);
      }
      return '';
    });
    if (css.trim()) throw new Error('unsupported SVG stylesheet syntax');
  }
}

function eotSfnt(buffer) {
  if (buffer.length < 82 || buffer.readUInt16LE(34) !== 0x504c) throw new Error('invalid EOT header');
  const total = buffer.readUInt32LE(0), fontSize = buffer.readUInt32LE(4);
  const version = buffer.readUInt32LE(8), flags = buffer.readUInt32LE(12);
  if (flags & 4) throw new Error('compressed EOT fonts are unsupported for SVG chart outlines; supply an uncompressed TTF/OTF/EOT face');
  if (flags & 0x10000000) throw new Error('XOR-encrypted EOT fonts are unsupported for SVG chart outlines');
  if (total !== buffer.length || fontSize < 12 || total - fontSize < 82 || ![0x10000, 0x20001, 0x20002].includes(version)) {
    throw new Error('invalid EOT size/version');
  }
  // Uncompressed EOT stores its complete sfnt after the variable-length header/names.
  const sfnt = buffer.subarray(total - fontSize, total);
  if (!['\x00\x01\x00\x00', 'true', 'OTTO'].includes(sfnt.toString('latin1', 0, 4))) throw new Error('uncompressed EOT has no trailing sfnt');
  return sfnt;
}

function checkTextCharacters(text) {
  // Fontkit shapes a run, but does not perform paragraph bidi/script itemization.
  // Explicitly limit this adapter to horizontal simple-script/CJK chart labels.
  for (const char of text) {
    if (/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u206f]/u.test(char) ||
        !/[\p{Script=Latin}\p{Script=Greek}\p{Script=Cyrillic}\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}\p{Script=Bopomofo}\p{Script=Common}\p{Script=Inherited}]/u.test(char)) {
      throw new Error(`SVG chart text needs unsupported bidi/complex-script itemization at U+${char.codePointAt(0).toString(16).toUpperCase()}`);
    }
  }
}

const SIMPLE_SCRIPTS = [
  [/\p{Script=Latin}/u, 'latn'], [/\p{Script=Greek}/u, 'grek'], [/\p{Script=Cyrillic}/u, 'cyrl'],
  [/\p{Script=Han}/u, 'hani'], [/[\p{Script=Hiragana}\p{Script=Katakana}]/u, 'kana'],
  [/\p{Script=Hangul}/u, 'hang'], [/\p{Script=Bopomofo}/u, 'bopo'],
];
const scriptFor = (cluster) => SIMPLE_SCRIPTS.find(([pattern]) => pattern.test(cluster))?.[1];

/**
 * Create a synchronous SVG-text-to-glyph-path adapter. Descriptors are the selected
 * Windows family/slot faces: { family, slot, path: absoluteFile, face: TTCIndex, eot }.
 * Only referenced faces are read, and faces are cached for subsequent SVGs.
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
          files.set(fileKey, descriptor.eot ? eotSfnt(buffer) : buffer);
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
    return { descriptor, font: load(descriptor), syntheticBold: bold && !['bold', 'boldItalic'].includes(descriptor.slot), syntheticItalic: italic && !['italic', 'boldItalic'].includes(descriptor.slot) };
  }

  return function outlineSvg(svgString) {
    if (typeof svgString !== 'string') throw new TypeError('SVG font outliner expects a string');
    if (/<!DOCTYPE|<!ENTITY|<\?xml-stylesheet\b/i.test(svgString)) throw new Error('DTD/entities/external stylesheets are unsupported in chart SVG');
    const document = new DOMParser({ onError: (level, message) => { throw new Error(`invalid chart SVG (${level}): ${message}`); } }).parseFromString(svgString, 'image/svg+xml');
    if (document.documentElement?.localName !== 'svg' || document.documentElement.namespaceURI !== SVG) throw new Error('font outliner expects a namespaced SVG root');
    const texts = Array.from(document.getElementsByTagNameNS(SVG, 'text')).filter(isRenderingContent);
    if (!texts.length) return svgString;
    checkStylesheets(document, texts);
    const stateCache = new WeakMap(), styleCache = new WeakMap();
    for (const text of texts) {
      try {
        if (children(text).some((node) => ![3, 4, 8].includes(node.nodeType))) throw new Error('only plain SVG text nodes are supported (no tspan/textPath/nested markup)');
        for (const name of ['textLength', 'lengthAdjust', 'rotate']) {
          if (text.hasAttribute(name)) throw new Error(`unsupported SVG text positioning attribute: ${name}`);
        }
        const state = textState(text, stateCache, styleCache);
        const styles = styleCache.get(text);
        for (const name of ['textLength', 'lengthAdjust', 'rotate', 'text-length', 'length-adjust']) {
          if (styles.has(name.toLowerCase())) throw new Error(`unsupported SVG text positioning property: ${name}`);
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
          if (/[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}\p{Script=Bopomofo}\u3000-\u303f\uff00-\uffef]/u.test(segment) && families.has(key('Noto Sans SC')) && !available.some((name) => key(name) === key('Noto Sans SC'))) available.push('Noto Sans SC');
          let selected;
          for (const name of available) {
            const face = candidate(name);
            if (!face) continue;
            primary ??= face.font;
            if (Array.from(segment).every((char) => /\p{Default_Ignorable_Code_Point}/u.test(char) || face.font.hasGlyphForCodePoint(char.codePointAt(0)))) { selected = face; break; }
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
          for (const position of run.layout.positions) {
            if (!['xAdvance', 'yAdvance', 'xOffset', 'yOffset'].every((name) => Number.isFinite(position[name])) || position.yAdvance !== 0) throw new Error('unsupported/non-finite horizontal glyph positioning');
            advance += position.xAdvance * run.scale;
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
          if (!['x', 'y', 'dx', 'dy'].includes(attr.name)) group.setAttributeNS(attr.namespaceURI, attr.name, attr.value);
        }
        group.setAttribute('data-pptd-text', content);
        group.setAttribute('data-pptd-advance', number(advance));
        group.setAttribute('data-pptd-origin', `${number(originX)} ${number(baselineY)}`);
        const used = [...new Set(runs.map(({ face }) => `${face.descriptor.family}/${face.descriptor.slot}${face.syntheticBold ? '+synthetic-bold' : ''}${face.syntheticItalic ? '+synthetic-italic' : ''}`))];
        group.setAttribute('data-pptd-fonts', JSON.stringify(used));
        if (!text.hasAttribute('aria-label')) group.setAttribute('aria-label', content);
        let pen = originX;
        const outlines = [];
        for (const run of runs) {
          const { font, syntheticBold, syntheticItalic } = run.face;
          if (syntheticBold && state.stroke.trim().toLowerCase() !== 'none') throw new Error('synthetic bold on stroked SVG text is unsupported; supply a real bold face');
          const slant = syntheticItalic ? SYNTHETIC_SLANT : 0;
          for (let i = 0; i < run.layout.glyphs.length; i++) {
            const glyph = run.layout.glyphs[i], position = run.layout.positions[i];
            if (glyph.id === 0) throw new Error(`font ${font.familyName} produced a missing glyph during shaping`);
            const glyphPath = glyph.path;
            if (!glyphPath || glyphPath.commands.some((command) => command.args.some((value) => !Number.isFinite(value)))) throw new Error('invalid/non-vector glyph path');
            const transformed = glyphPath.transform(run.scale, 0, slant * run.scale, -run.scale,
              pen + (position.xOffset + slant * position.yOffset) * run.scale,
              baselineY - position.yOffset * run.scale);
            if (transformed.commands.some((command) => command.args.some((value) => !Number.isFinite(value)))) throw new Error('non-finite transformed SVG glyph path');
            const data = transformed.toSVG();
            if (data) outlines.push({ data, syntheticBold });
            pen += position.xAdvance * run.scale;
          }
        }
        if (/url\s*\(/i.test(state.fill) && outlines.some((item) => item.syntheticBold) && outlines.some((item) => !item.syntheticBold)) {
          throw new Error('mixed synthetic/real bold with an SVG paint server is unsupported; supply matching real faces');
        }
        // One path per synthetic-paint class keeps stroke widths in SVG user units,
        // and keeps ordinary mixed-font text's objectBoundingBox paints on one outline.
        for (const syntheticBold of [false, true]) {
          const data = outlines.filter((outline) => outline.syntheticBold === syntheticBold).map((outline) => outline.data).join('');
          if (!data) continue;
          const outline = document.createElementNS(SVG, 'path');
          outline.setAttribute('d', data);
          if (syntheticBold) {
            outline.setAttribute('stroke', state.fill);
            outline.setAttribute('stroke-width', number(state.size * SYNTHETIC_BOLD_EM));
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
    return serializer.serializeToString(document);
  };
}
