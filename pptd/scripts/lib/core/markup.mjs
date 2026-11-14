// The one text grammar shared by validation, fonts and formulas.
//
// `text` is rich text: the documented tags are markup, HTML entities are decoded, and
// anything else is literal. Top-level content outside a block is one paragraph per
// line, which is all that the "plain text" shorthand is.
//
// The writer cannot be trusted with that grammar: it deletes anything tag-like
// (`p<0.05`, `List<T>`), entities it does not know (`&nbsp;`) and text beside a block,
// and ignores inline tags outside one. The content pass parses this once and keeps
// the DOM for fonts and formula conversion; the writer gets well-formed blocks.
//
// Inline CSS is a closed contract rather than a browser dialect: the writer silently
// ignores declarations it cannot express (`letter-spacing`, `text-decoration`, …), so
// they fail here instead of vanishing, and `$theme` colors are resolved to HEX before
// serialization because the writer only understands theme tokens in element fields.
import { HTML_ENTITIES } from '../../../assets/vendor/xmldom.mjs';
import { parseCss } from './css.mjs';
import { resolveThemeColor } from './color.mjs';
import { checkXmlString, parseXml, serializeNode } from './xml.mjs';

const BLOCKS = new Set(['p', 'ul', 'ol']);
const INLINE = new Set(['span', 'strong', 'em', 'b', 'i', 'u', 's', 'sup', 'sub', 'a']);
const BLOCK_OWNERS = new Set(['p', 'li']);
const TAG = /<\/?(?:p|span|strong|em|b|i|u|s|sup|sub|a|ul|ol|li|br)(?:\s[^<>]*|\/)?>/i;
const MARKUP = new RegExp(`<!--[\\s\\S]*?-->|${TAG.source}|(<)`, 'gi');
const FORMULA = /\\\(([\s\S]*?)\\\)/g;

/** Inline CSS the private writer can express, per element. */
const RUN_CSS = new Set(['color', 'font-size', 'font-weight', 'font-style', 'font-variant', 'background-color', 'font-family']);
const PARAGRAPH_CSS = new Set(['text-align', 'line-height', 'margin-top', 'margin-left', 'margin-right']);
const ALIGNMENTS = new Set(['left', 'center', 'right', 'justify', 'distributed']);
const FONT_STYLES = new Set(['normal', 'italic', 'oblique']);
const FONT_VARIANTS = new Set(['normal', 'small-caps']);
const FONT_WEIGHTS = new Set(['normal', 'bold', 'bolder', 'lighter']);
const HEX_COLOR = /^#?[0-9a-f]{6}(?:[0-9a-f]{2})?$/i;
const LENGTH = /^[+-]?\d+(?:\.\d+)?px$/;
const NUMBER = /^[+-]?\d+(?:\.\d+)?$/;
const HREF_SCHEME = /^(?:https?:\/\/|mailto:)/i;
/** CSS marker keywords the writer renders as literal text; map them to real glyphs. */
const LIST_GLYPHS = new Map([['disc', '\u2022'], ['circle', '\u25e6'], ['square', '\u25aa']]);

/** Keep character references and known named entities; any other `&` is literal. */
function escapeAmpersands(text) {
  return text.replace(/&(?:(#\d+|#x[\da-f]+|[a-z]\w*);)?/gi, (match, entity) => (
    entity && (entity[0] === '#' || Object.hasOwn(HTML_ENTITIES, entity)) ? match : `&amp;${match.slice(1)}`));
}

/** Wrap loose top-level lines in paragraphs; blank lines around blocks are only formatting. */
function wrapLooseLines(root) {
  const doc = root.ownerDocument;
  const blank = (line) => line.every((node) => node.nodeType === 8 || (node.nodeType === 3 && !node.data.trim()));
  let lines = [[]], afterBlock = false;
  const flush = (before) => {
    while (lines.length && blank(lines.at(-1))) lines.pop();
    while (afterBlock && lines.length && blank(lines[0])) lines.shift();
    for (const line of lines) {
      const paragraph = root.insertBefore(doc.createElementNS(root.namespaceURI, 'p'), before);
      for (const node of line) paragraph.appendChild(node);
    }
    lines = [[]];
  };
  for (const node of [...root.childNodes]) {
    if (node.nodeType === 1 && BLOCKS.has(node.localName.toLowerCase())) {
      flush(node);
      afterBlock = true;
      continue;
    }
    root.removeChild(node);
    if (node.nodeType !== 3) lines.at(-1).push(node);
    else for (const [index, line] of looseLines(node.data).entries()) {
      if (index) lines.push([]);
      lines.at(-1).push(doc.createTextNode(line));
    }
  }
  flush(null);
}

/** A newline inside a complete formula is LaTeX whitespace, not a new paragraph. */
function looseLines(text) {
  const lines = [];
  let start = 0;
  for (const match of text.matchAll(/\\\([\s\S]*?\\\)|\n/g)) {
    if (match[0] !== '\n') continue;
    lines.push(text.slice(start, match.index));
    start = match.index + 1;
  }
  return [...lines, text.slice(start)];
}

export function* textNodes(node) {
  if (node.nodeType === 3 || node.nodeType === 4) yield node;
  else if (node.nodeType === 1 || node.nodeType === 9) {
    for (let child = node.firstChild; child; child = child.nextSibling) yield* textNodes(child);
  }
}

function* elements(node) {
  for (let child = node.firstChild; child; child = child.nextSibling) {
    if (child.nodeType !== 1) continue;
    yield child;
    yield* elements(child);
  }
}

const localName = (node) => node.localName.toLowerCase();
const isTag = (node, name) => node.nodeType === 1 && localName(node) === name;
/** HTML parsing keeps the author's letter case, and the writer is case-sensitive. */
const tagsNamed = (root, name) => [...elements(root)].filter((node) => localName(node) === name);
const writeStyle = (node, css) => node.setAttribute('style', [...css].map(([key, value]) => `${key}:${value}`).join(';'));

/**
 * Fold tag and attribute case the way a browser does. Without this the writer silently
 * drops `<UL><LI>` bullets and `STYLE=`/`COLOR:` declarations, because its own parser
 * only understands lowercase names.
 */
function foldHtmlCase(parent) {
  const doc = parent.ownerDocument;
  for (let child = parent.firstChild; child;) {
    const next = child.nextSibling;
    if (child.nodeType === 1) {
      const lower = child.localName.toLowerCase();
      let node = child;
      if (lower !== child.localName) {
        node = doc.createElementNS(child.namespaceURI, lower);
        for (const attr of [...child.attributes]) node.setAttribute(attr.name.toLowerCase(), attr.value);
        while (child.firstChild) node.appendChild(child.firstChild);
        parent.replaceChild(node, child);
      } else {
        for (const attr of [...child.attributes]) {
          const name = attr.name.toLowerCase();
          if (name !== attr.name) {
            child.removeAttribute(attr.name);
            child.setAttribute(name, attr.value);
          }
        }
      }
      foldHtmlCase(node);
    }
    child = next;
  }
}

function checkCssValue(property, value, label) {
  const invalid = (expected) => {
    throw new Error(`${label}: CSS ${property} must be ${expected}, got ${JSON.stringify(value)}`);
  };
  switch (property) {
    case 'text-align': if (!ALIGNMENTS.has(value)) invalid('left, center, right, justify or distributed'); return;
    case 'line-height': if (!NUMBER.test(value) && !LENGTH.test(value)) invalid('a unitless multiple or a px length'); return;
    case 'margin-top':
    case 'margin-left':
    case 'margin-right': if (!LENGTH.test(value)) invalid('a px length'); return;
    case 'font-size': if (!LENGTH.test(value)) invalid('a px length'); return;
    case 'font-weight': if (!FONT_WEIGHTS.has(value) && !NUMBER.test(value)) invalid('normal, bold, bolder, lighter or a number'); return;
    case 'font-style': if (!FONT_STYLES.has(value)) invalid('normal, italic or oblique'); return;
    case 'font-variant': if (!FONT_VARIANTS.has(value)) invalid('normal or small-caps'); return;
    case 'font-family': if (!value.trim()) invalid('a font family name'); return;
    default: return;
  }
}

/** `$theme` colors only exist in element fields, so resolve them before serialization. */
function resolveCssColors(css, themeColors, label) {
  let resolved = false;
  for (const property of ['color', 'background-color']) {
    if (!css.has(property)) continue;
    const value = css.get(property).trim();
    if (!value.startsWith('$')) {
      if (!HEX_COLOR.test(value)) {
        throw new Error(`${label}: CSS ${property} must be a HEX6/HEX8 color or a $theme token, got ${JSON.stringify(value)}`);
      }
      continue;
    }
    const color = resolveThemeColor(value, themeColors, `${label}: CSS ${property}`);
    if (!HEX_COLOR.test(color)) throw new Error(`${label}: theme color ${value} is not a HEX6/HEX8 color`);
    css.set(property, color.startsWith('#') ? color : `#${color}`);
    resolved = true;
  }
  return resolved;
}

/** The writer writes `list-style-type` straight into `<a:buChar char>` for `<ul>`. */
function normalizeListStyleType(css, ordered, label) {
  if (!css.has('list-style-type')) return false;
  if (ordered) {
    throw new Error(`${label}: <ol> always exports arabicPeriod numbering; remove list-style-type, or use <ul> for a custom marker`);
  }
  const quoted = css.get('list-style-type').trim().replace(/^(['"])([\s\S]*)\1$/, '$2');
  const glyph = LIST_GLYPHS.get(quoted) ?? quoted;
  if ([...glyph].length !== 1) {
    throw new Error(`${label}: list-style-type must be disc, circle, square or a single marker glyph, got ${JSON.stringify(quoted)}`);
  }
  css.set('list-style-type', glyph);
  return true;
}

function checkRichCss(node, themeColors, label) {
  if (!node.hasAttribute('style')) return;
  const tag = localName(node);
  const allowed = new Set(RUN_CSS);
  if (tag !== 'span') for (const property of PARAGRAPH_CSS) allowed.add(property);
  if (tag === 'li') allowed.add('list-style-type');
  const css = parseCss(node.getAttribute('style'));
  for (const [property] of css) {
    if (!allowed.has(property)) {
      throw new Error(`${label}: <${tag}> style does not support ${JSON.stringify(property)}; supported: ${[...allowed].sort().join(', ')}`);
    }
    checkCssValue(property, css.get(property), label);
  }
  const changed = resolveCssColors(css, themeColors, label)
    || (tag === 'li' && normalizeListStyleType(css, isTag(node.parentNode, 'ol'), label));
  if (changed) writeStyle(node, css);
}

function checkHrefs(root, label) {
  for (const anchor of tagsNamed(root, 'a')) {
    const href = anchor.getAttribute('href');
    if (href !== null && !HREF_SCHEME.test(href.trim())) {
      throw new Error(`${label}: <a href> must be an https://, http:// or mailto: URL, got ${JSON.stringify(href)}`);
    }
  }
}

/** Split one node's content at `<br>` boundaries, cloning inline ancestors per segment. */
function breakSegments(node) {
  const segments = [[]];
  for (const child of [...node.childNodes]) {
    if (isTag(child, 'br')) {
      segments.push([]);
      continue;
    }
    if (child.nodeType === 1 && INLINE.has(localName(child))) {
      breakSegments(child).forEach((nodes, index) => {
        if (index) segments.push([]);
        const clone = child.cloneNode(false);
        for (const inner of nodes) clone.appendChild(inner);
        segments.at(-1).push(clone);
      });
      continue;
    }
    segments.at(-1).push(child.cloneNode(true));
  }
  return segments;
}

/** The nearest `<p>`/`<li>` that owns a `<br>`, so nested breaks split the right block. */
function nearestBlock(node) {
  for (let current = node.parentNode; current; current = current.parentNode) {
    if (current.nodeType === 1 && BLOCK_OWNERS.has(localName(current))) return current;
  }
  return null;
}

/**
 * The writer has no `<a:br/>`, so a `<br>` would join both sides into one run. Split the
 * owning block instead: identical paragraph properties render as consecutive lines.
 */
function splitLineBreaks(root, label) {
  const owners = new Map();
  for (const br of tagsNamed(root, 'br')) {
    const block = nearestBlock(br);
    if (block && !owners.has(block)) owners.set(block, block);
  }
  for (const [block] of owners) {
    const parent = block.parentNode;
    if (!parent) continue;
    if (localName(block) === 'li') {
      throw new Error(`${label}: <br> inside a list item cannot be exported; use separate <li> items or <p> blocks`);
    }
    for (const nodes of breakSegments(block)) {
      const clone = block.cloneNode(false);
      for (const node of nodes) clone.appendChild(node);
      parent.insertBefore(clone, block);
    }
    parent.removeChild(block);
  }
}

function readFormulas(root, label) {
  const formulas = [];
  for (const node of textNodes(root)) {
    const text = node.textContent;
    let position = 0;
    while (position < text.length) {
      const start = text.indexOf('\\(', position), closing = text.indexOf('\\)', position);
      if (closing >= 0 && (start < 0 || closing < start)) throw new Error(`${label}: unmatched formula closing delimiter`);
      if (start < 0) break;
      const end = text.indexOf('\\)', start + 2);
      if (end < 0) throw new Error(`${label}: unclosed formula or a tag splitting its delimiters`);
      const nested = text.indexOf('\\(', start + 2);
      if (nested >= 0 && nested < end) throw new Error(`${label}: nested formula delimiters`);
      const latex = text.slice(start + 2, end).trim();
      if (!latex) throw new Error(`${label}: empty formula`);
      formulas.push(latex);
      position = end + 2;
    }
  }
  return formulas;
}

/** Canonical block DOM, formula tokens, and serialization for the writer. */
export function readRichText(text, label = 'rich text', { theme = {} } = {}) {
  const themeColors = theme.colors ?? {};
  const html = text
    // LaTeX comparisons and alignment ampersands are never markup.
    .replace(FORMULA, (_, latex) => {
      // KaTeX would read `<strong>` as two comparisons and typeset nonsense.
      if (TAG.test(latex)) throw new Error(`${label}: rich-text tags are not allowed inside formulas`);
      return `\\(${latex.replace(/</g, '&lt;').replace(/>/g, '&gt;')}\\)`;
    })
    .replace(MARKUP, (match, literal) => (literal ? '&lt;' : match));
  let root;
  try {
    root = parseXml(`<body>${escapeAmpersands(html)}</body>`, label, { mime: 'text/html' }).documentElement;
  } catch (error) {
    throw new Error(`${error.message}; close every tag, quote attribute values, and write a literal < or & as &lt; or &amp;`, { cause: error });
  }
  foldHtmlCase(root);
  for (const span of tagsNamed(root, 'span')) {
    if (!span.hasAttribute('data-math-node') && !span.hasAttribute('data-math')) continue;
    const latex = span.getAttribute('data-tex');
    if (!latex?.trim()) throw new Error(`${label}: legacy math span has no data-tex`);
    for (const attr of ['data-math-node', 'data-math', 'data-tex']) span.removeAttribute(attr);
    while (span.firstChild) span.removeChild(span.firstChild);
    span.appendChild(root.ownerDocument.createTextNode(`\\(${latex}\\)`));
  }
  for (const node of elements(root)) checkRichCss(node, themeColors, label);
  checkHrefs(root, label);
  checkXmlString(root.textContent, label);
  const formulas = readFormulas(root, label);
  wrapLooseLines(root);
  splitLineBreaks(root, label);
  return {
    root,
    formulas,
    serialize() {
      // Serialize inside <body> so children do not each redeclare its namespace.
      const body = serializeNode(root);
      return root.firstChild ? body.slice(body.indexOf('>') + 1, body.lastIndexOf('</')) : '';
    },
  };
}
