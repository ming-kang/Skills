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
import { HTML_ENTITIES } from '../../../assets/vendor/xmldom.mjs';
import { checkXmlString, parseXml, serializeNode } from './xml.mjs';

const BLOCKS = new Set(['p', 'ul', 'ol']);
const TAG = /<\/?(?:p|span|strong|em|b|i|u|s|sup|sub|a|ul|ol|li|br)(?:\s[^<>]*|\/)?>/i;
const MARKUP = new RegExp(`<!--[\\s\\S]*?-->|${TAG.source}|(<)`, 'gi');
const FORMULA = /\\\(([\s\S]*?)\\\)/g;

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
export function readRichText(text, label = 'rich text') {
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
  for (const span of [...root.getElementsByTagName('span')]) {
    if (!span.hasAttribute('data-math-node') && !span.hasAttribute('data-math')) continue;
    const latex = span.getAttribute('data-tex');
    if (!latex?.trim()) throw new Error(`${label}: legacy math span has no data-tex`);
    for (const attr of ['data-math-node', 'data-math', 'data-tex']) span.removeAttribute(attr);
    while (span.firstChild) span.removeChild(span.firstChild);
    span.appendChild(root.ownerDocument.createTextNode(`\\(${latex}\\)`));
  }
  checkXmlString(root.textContent, label);
  const formulas = readFormulas(root, label);
  wrapLooseLines(root);
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
