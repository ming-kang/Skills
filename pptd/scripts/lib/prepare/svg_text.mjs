// Freeze labels from the pinned ECharts SVG renderer, not arbitrary SVG text layouts.
// ECharts emits standalone <text> with explicit px size/family, anchor and baseline;
// unexpected CSS/structure fails closed. Glyph coverage, shaping and metrics come
// from the selected original font bytes shared with the embedding pass.
import { create as createFont } from '../../../assets/vendor/fontkit.mjs';
import { parseCss } from '../core/css.mjs';
import { NS } from '../core/xml.mjs';
import { EAST_ASIAN, normalizeFontKey as key } from './font_data.mjs';

const { svg: SVG, xml: XML } = NS;
const SLOTS = new Set(['regular', 'bold', 'italic', 'boldItalic']);
const ROOT_ATTRS = new Set(['width', 'height', 'viewBox', 'version', 'baseProfile']);
const LABEL_ATTRS = new Set(['x', 'y', 'transform', 'style', 'text-anchor', 'dominant-baseline', 'fill', 'fill-opacity', 'xml:space', 'aria-label']);
const LABEL_CSS = new Set(['font-size', 'font-family', 'font-weight', 'font-style']);
const NUMBER = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i;
const graphemes = new Intl.Segmenter('und', { granularity: 'grapheme' });
const num = (value) => String(Object.is(value, -0) ? 0 : value);
const attributes = (node) => [...node.attributes];
const SIMPLE_SCRIPTS = [
  [/\p{Script=Latin}/u, 'latn'], [/\p{Script=Greek}/u, 'grek'], [/\p{Script=Cyrillic}/u, 'cyrl'],
  [/\p{Script=Han}/u, 'hani'], [/[\p{Script=Hiragana}\p{Script=Katakana}]/u, 'kana'],
  [/\p{Script=Hangul}/u, 'hang'], [/\p{Script=Bopomofo}/u, 'bopo'],
];
const scriptFor = (cluster) => SIMPLE_SCRIPTS.find(([pattern]) => pattern.test(cluster))?.[1];

function checkStylesheets(document) {
  // Generated classes belong to shapes only; text and the root may not carry class.
  for (const style of document.getElementsByTagNameNS(SVG, 'style')) {
    const rest = style.textContent.replace(/\/\*[\s\S]*?\*\//g, '').replace(/([^{}]+)\{[^{}]*\}/g, (_, selectors) => {
      for (const selector of selectors.split(',')) {
        if (!/^\.[\w-]+(?::hover)?$/.test(selector.trim())) {
          throw new Error(`stylesheet styling of outlined chart text is unsupported: ${selector.trim()}`);
        }
      }
      return '';
    });
    if (rest.trim()) throw new Error('unsupported chart SVG stylesheet syntax');
  }
}

function chartLabel(node, root) {
  if (node.parentNode !== root || [...node.childNodes].some((child) => ![3, 4, 8].includes(child.nodeType))) {
    throw new Error('chart labels must be standalone SVG text (no nested text/tspan/textPath)');
  }
  for (const attr of attributes(node)) {
    if (!LABEL_ATTRS.has(attr.name)) throw new Error(`unsupported chart text attribute: ${attr.name}`);
  }
  const css = parseCss(node.getAttribute('style') ?? '', { strict: true });
  for (const [property, value] of css) {
    if (!LABEL_CSS.has(property) || (['font-weight', 'font-style'].includes(property) && value !== 'normal')) {
      throw new Error(`unsupported chart text property ${property}=${value}`);
    }
  }
  const sizeText = css.get('font-size') ?? '';
  const size = Number(sizeText.slice(0, -2));
  if (!sizeText.endsWith('px') || !NUMBER.test(sizeText.slice(0, -2)) || !Number.isFinite(size) || size <= 0) {
    throw new Error(`chart text requires a positive px font-size: ${sizeText}`);
  }
  const family = css.get('font-family');
  if (!family?.trim() || /['"]/.test(family)) throw new Error('chart text requires explicit resolved font-family names');
  const names = family.split(',').map((name) => name.trim());
  if (names.some((name) => !name)) throw new Error(`empty chart font-family: ${family}`);
  const anchor = node.getAttribute('text-anchor') ?? 'start';
  if (!['start', 'middle', 'end'].includes(anchor)) throw new Error(`unsupported chart text anchor: ${anchor}`);
  const baseline = node.getAttribute('dominant-baseline');
  if (baseline !== null && baseline !== 'central') throw new Error(`unsupported chart text baseline: ${baseline}`);
  const position = (name) => {
    const raw = node.getAttribute(name) ?? '0';
    if (!NUMBER.test(raw) || !Number.isFinite(Number(raw))) throw new Error(`chart text ${name} must be a finite number: ${raw}`);
    return Number(raw);
  };
  const space = node.getAttributeNS(XML, 'space');
  if (space !== null && space !== 'preserve') throw new Error(`unsupported chart xml:space: ${space}`);
  let content = node.textContent;
  if (space === 'preserve') {
    if (/[\t\r\n]/.test(content)) throw new Error('multiline/tab-preserved chart labels require separate positioned text nodes');
  } else content = content.replace(/[\t\r\n ]+/g, ' ').trim();
  return { content, names, size, anchor, central: baseline === 'central', x: position('x'), y: position('y') };
}

function checkTextCharacters(text) {
  for (const char of text) {
    if (/[\u061c\u200e\u200f\u202a-\u202e\u2066-\u206f]/u.test(char) ||
        !/[\p{Script=Latin}\p{Script=Greek}\p{Script=Cyrillic}\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}\p{Script=Bopomofo}\p{Script=Common}\p{Script=Inherited}]/u.test(char)) {
      throw new Error(`SVG chart text needs unsupported bidi/complex-script itemization at U+${char.codePointAt(0).toString(16).toUpperCase()}`);
    }
  }
}

/** Descriptors: selected {family, slot, face, read(): original SFNT/TTC bytes}. */
export function createSvgFontOutliner(descriptors) {
  const families = new Map(), fonts = new Map(), containers = new WeakMap();
  for (const input of descriptors) {
    if (typeof input?.family !== 'string' || !input.family.trim() || !SLOTS.has(input.slot) || typeof input.read !== 'function' ||
        !Number.isInteger(input.face ?? 0) || (input.face ?? 0) < 0) {
      throw new TypeError('invalid SVG font descriptor: expected family, slot, face index and byte reader');
    }
    const name = key(input.family);
    if (!families.has(name)) families.set(name, new Map());
    const slots = families.get(name);
    if (slots.has(input.slot)) throw new Error(`duplicate SVG font descriptor: ${input.family} ${input.slot}`);
    slots.set(input.slot, { ...input, face: input.face ?? 0 });
  }

  function faceFor(name) {
    const slots = families.get(key(name));
    if (!slots) return undefined;
    const descriptor = slots.get('regular');
    if (!descriptor) throw new Error(`SVG font ${name} has no regular or usable regular face; refusing a wrong style`);
    if (!fonts.has(descriptor)) {
      try {
        const bytes = descriptor.read();
        if (!(bytes instanceof Uint8Array)) throw new Error('font reader returned no byte array');
        if (!containers.has(bytes)) containers.set(bytes, createFont(bytes));
        const container = containers.get(bytes);
        const font = container.type === 'TTC' ? container.fonts[descriptor.face] : descriptor.face === 0 ? container : undefined;
        if (!font || typeof font.layout !== 'function' || !Number.isFinite(font.unitsPerEm) || font.unitsPerEm <= 0 ||
            !Number.isFinite(font.ascent) || !Number.isFinite(font.descent)) throw new Error('invalid outline face or collection index');
        const tables = font.directory?.tables ?? {};
        if (!(tables.glyf || tables['CFF '] || tables.CFF2)) throw new Error('font has no scalable glyph outlines');
        if (['COLR', 'CPAL', 'sbix', 'CBDT', 'CBLC', 'EBDT', 'EBLC', 'SVG '].some((tag) => tables[tag])) {
          throw new Error('color/bitmap glyph fonts are unsupported by the monochrome SVG outliner');
        }
        fonts.set(descriptor, { descriptor, font });
      } catch (error) {
        throw new Error(`cannot outline SVG chart with ${descriptor.family} ${descriptor.slot} (face ${descriptor.face}): ${error.message}`, { cause: error });
      }
    }
    return fonts.get(descriptor);
  }

  return function outlineSvg(document) {
    const root = document?.documentElement;
    if (root?.localName !== 'svg' || root.namespaceURI !== SVG) throw new Error('chart outliner requires a namespaced SVG Document');
    for (const attr of attributes(root)) {
      if (!/^xmlns(?::|$)/.test(attr.name) && !ROOT_ATTRS.has(attr.name)) throw new Error(`unsupported chart SVG root attribute: ${attr.name}`);
    }
    checkStylesheets(document);
    for (const text of [...document.getElementsByTagNameNS(SVG, 'text')]) {
      try {
        const { content, names, size, anchor, central, x, y } = chartLabel(text, root);
        checkTextCharacters(content);
        const withCJK = families.has(key('Noto Sans SC')) && !names.some((name) => key(name) === key('Noto Sans SC'))
          ? [...names, 'Noto Sans SC'] : names;
        const runs = [];
        let primary;
        for (const { segment } of graphemes.segment(content)) {
          let selected;
          for (const name of EAST_ASIAN.test(segment) ? withCJK : names) {
            const face = faceFor(name);
            if (!face) continue;
            primary ??= face.font;
            if ([...segment].every((char) => /\p{Default_Ignorable_Code_Point}/u.test(char) || face.font.hasGlyphForCodePoint(char.codePointAt(0)))) {
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
          run.scale = size / run.face.font.unitsPerEm;
          if (!Number.isFinite(run.scale) || run.scale <= 0) throw new Error('invalid font outline scale');
          if (run.layout.direction !== 'ltr') throw new Error('RTL SVG glyph runs require unsupported bidi layout');
          if (run.layout.glyphs.length !== run.layout.positions.length) throw new Error('invalid fontkit glyph positioning');
          for (const pos of run.layout.positions) {
            if (!['xAdvance', 'yAdvance', 'xOffset', 'yOffset'].every((name) => Number.isFinite(pos[name])) || pos.yAdvance !== 0) {
              throw new Error('unsupported/non-finite horizontal glyph positioning');
            }
            advance += pos.xAdvance * run.scale;
          }
        }
        const originX = x - advance * (anchor === 'middle' ? 0.5 : anchor === 'end' ? 1 : 0);
        const baselineY = y + (primary && central ? (primary.ascent + primary.descent) * size / primary.unitsPerEm / 2 : 0);
        if (![advance, originX, baselineY].every(Number.isFinite)) throw new Error('non-finite SVG text advance/origin/baseline');

        const group = document.createElementNS(SVG, 'g');
        for (const attr of attributes(text)) {
          if (!['x', 'y', 'dominant-baseline'].includes(attr.name)) group.setAttributeNS(attr.namespaceURI, attr.name, attr.value);
        }
        group.setAttribute('data-pptd-text', content);
        group.setAttribute('data-pptd-advance', num(advance));
        group.setAttribute('data-pptd-origin', `${num(originX)} ${num(baselineY)}`);
        group.setAttribute('data-pptd-fonts', JSON.stringify([...new Set(runs.map(({ face }) => `${face.descriptor.family}/${face.descriptor.slot}`))]));
        if (!text.hasAttribute('aria-label')) group.setAttribute('aria-label', content);

        let pen = originX;
        const paths = [];
        for (const run of runs) {
          for (const [index, glyph] of run.layout.glyphs.entries()) {
            const pos = run.layout.positions[index];
            if (glyph.id === 0) throw new Error(`font ${run.face.font.familyName} produced a missing glyph during shaping`);
            const path = glyph.path;
            if (!path || path.commands.some((cmd) => cmd.args.some((value) => !Number.isFinite(value)))) throw new Error('invalid/non-vector glyph path');
            const transformed = path.transform(run.scale, 0, 0, -run.scale, pen + pos.xOffset * run.scale, baselineY - pos.yOffset * run.scale);
            if (transformed.commands.some((cmd) => cmd.args.some((value) => !Number.isFinite(value)))) throw new Error('non-finite transformed SVG glyph path');
            paths.push(transformed.toSVG());
            pen += pos.xAdvance * run.scale;
          }
        }
        if (paths.some(Boolean)) {
          const outline = document.createElementNS(SVG, 'path');
          outline.setAttribute('d', paths.join(''));
          group.appendChild(outline);
        }
        text.parentNode.replaceChild(group, text);
      } catch (error) {
        throw new Error(`cannot outline SVG text ${JSON.stringify(text.textContent.slice(0, 100))}: ${error.message}`, { cause: error });
      }
    }
    return document;
  };
}
