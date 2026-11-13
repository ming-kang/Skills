import { katex } from '../../../assets/vendor/katex.mjs';
import { DOMImplementation, DOMParser, XMLSerializer } from '../../../assets/vendor/xmldom.mjs';

const M = 'http://schemas.openxmlformats.org/officeDocument/2006/math';
const A = 'http://schemas.openxmlformats.org/drawingml/2006/main';
const XML = 'http://www.w3.org/XML/1998/namespace';
const document = new DOMImplementation().createDocument('', 'root', null);
const serializer = new XMLSerializer();
const children = (node) => [...node.childNodes].filter((child) => child.nodeType === 1);
const first = (node) => children(node)[0];
function parse(text, mime = 'application/xml') {
  return new DOMParser({ onError: (level, message) => {
    if (level !== 'warning') throw new Error(`invalid math markup: ${message}`);
  } }).parseFromString(text, mime);
}
function element(name, nodes = [], attributes = {}, namespace = M) {
  const node = document.createElementNS(namespace, name);
  for (const [key, value] of Object.entries(attributes)) {
    if (value !== undefined) {
      node.setAttributeNS(key.startsWith('m:') ? M : key.startsWith('xml:') ? XML : null, key, String(value));
    }
  }
  for (const child of nodes.flat().filter(Boolean)) node.appendChild(child);
  return node;
}

const COLORS = { black: '000000', white: 'FFFFFF', red: 'FF0000', green: '008000', blue: '0000FF', yellow: 'FFFF00', orange: 'FFA500', purple: '800080', gray: '808080', grey: '808080', brown: 'A52A2A', cyan: '00FFFF', magenta: 'FF00FF', teal: '008080', navy: '000080', lime: '00FF00', maroon: '800000', olive: '808000', silver: 'C0C0C0' };
function colorFill(color, opacity = 1) {
  const text = COLORS[String(color).toLowerCase()] ?? String(color).replace(/^#/, '');
  if (!/^[\da-f]{6}(?:[\da-f]{2})?$/i.test(text)) throw new Error(`unsupported formula color: ${color}`);
  const amount = opacity * (text.length === 8 ? parseInt(text.slice(6), 16) / 255 : 1);
  const alpha = amount < 1 ? [element('a:alpha', [], { val: Math.round(amount * 100000) }, A)] : [];
  return element('a:solidFill', [element('a:srgbClr', alpha, { val: text.slice(0, 6) }, A)], {}, A);
}
function runProperties(style) {
  const attrs = { sz: style.fontSize === undefined ? undefined : Math.round(style.fontSize * 100), b: style.bold ? '1' : undefined, i: style.italic === undefined ? undefined : style.italic ? '1' : '0' };
  return element('a:rPr', style.color || style.opacity !== undefined ? [colorFill(style.color ?? '000000', style.opacity)] : [], attrs, A);
}
function styled(node, inherited) {
  const style = { ...inherited };
  if (node.localName === 'mi') style.italic = true;
  if (['mn', 'mo'].includes(node.localName)) style.italic = false;
  const variant = node.getAttribute('mathvariant');
  if (variant) {
    style.bold = variant.includes('bold');
    style.italic = variant.includes('italic');
    const scripts = { normal: 'roman', bold: 'roman', italic: 'roman', 'bold-italic': 'roman', script: 'script', 'bold-script': 'script', fraktur: 'fraktur', 'bold-fraktur': 'fraktur', 'double-struck': 'double-struck', 'sans-serif': 'sans-serif', 'bold-sans-serif': 'sans-serif', 'sans-serif-italic': 'sans-serif', 'sans-serif-bold-italic': 'sans-serif', monospace: 'monospace' };
    if (!scripts[variant]) throw new Error(`unsupported math variant: ${variant}`);
    style.script = scripts[variant];
  }
  if (node.hasAttribute('mathcolor')) style.color = node.getAttribute('mathcolor');
  if (node.hasAttribute('mathbackground')) throw new Error('formula background colors are not supported');
  const level = node.getAttribute('scriptlevel');
  if (level && level !== '0') throw new Error(`explicit math scriptlevel ${level} is not supported`);
  if (node.hasAttribute('displaystyle')) style.displayStyle = node.getAttribute('displaystyle') === 'true';
  const size = node.getAttribute('mathsize');
  if (size) {
    const match = /^(\d+(?:\.\d+)?)(px|em|%)$/.exec(size);
    if (!match) throw new Error(`unsupported formula size: ${size}`);
    style.fontSize = Number(match[1]) * (match[2] === 'px' ? 1 : (inherited.fontSize ?? 18) / (match[2] === '%' ? 100 : 1));
  }
  return style;
}
function run(text, style) {
  const properties = style.script ? [element('m:rPr', [element('m:scr', [], { 'm:val': style.script })])] : [];
  const value = element('m:t', [], /\s/.test(text) ? { 'xml:space': 'preserve' } : {});
  value.appendChild(document.createTextNode(text));
  return element('m:r', [...properties, runProperties(style), value]);
}

function isFenceMo(node) {
  return node?.localName === 'mo' && node.getAttribute('fence') === 'true' && node.getAttribute('stretchy') !== 'false';
}

function compile(node, inherited = {}) {
  const tag = node.localName;
  const style = styled(node, inherited);
  const items = children(node);
  const sequence = () => items.flatMap((child) => compile(child, style));
  const arity = (count) => { if (items.length !== count) throw new Error(`${tag} requires ${count} children`); };
  const property = (name, extras = []) => element(`${name}Pr`, [...extras, element('m:ctrlPr', [runProperties(style)])]);
  const expression = (name, child) => element(name, compile(child, style));
  if (['mi', 'mn', 'mo', 'mtext'].includes(tag)) return [run(node.textContent, style)];
  if (tag === 'mpadded') return sequence();
  if (tag === 'mspace') {
    const match = /^(-?\d+(?:\.\d+)?)(em|px)$/.exec(node.getAttribute('width') || '0em');
    if (!match || Number(match[1]) < 0) throw new Error('negative or unsupported formula spacing');
    const size = Number(match[1]) * (match[2] === 'em' ? (style.fontSize ?? 18) : 1);
    if (!size) return [];
    // A hidden em-space has the requested advance without inflating equation height.
    return [element('m:phant', [element('m:phantPr', [element('m:show', [], { 'm:val': '0' }), element('m:zeroAsc', [], { 'm:val': '1' }), element('m:zeroDesc', [], { 'm:val': '1' })]), element('m:e', [run('\u2003', { ...style, fontSize: size })])])];
  }
  if (['mrow', 'mstyle'].includes(tag)) {
    const pairs = { '(': ')', '[': ']', '{': '}', '|': '|', '⟨': '⟩' };
    const bothFences = items.length >= 3 && isFenceMo(items[0]) && isFenceMo(items.at(-1));
    const symmetricPair = items.length >= 3 && items[0].localName === 'mo' && items.at(-1).localName === 'mo' && pairs[items[0].textContent] === items.at(-1).textContent && items[0].getAttribute('stretchy') !== 'false';
    if (bothFences || symmetricPair) {
      return [element('m:d', [property('m:d', [element('m:begChr', [], { 'm:val': items[0].textContent }), element('m:endChr', [], { 'm:val': items.at(-1).textContent })]), element('m:e', items.slice(1, -1).flatMap((child) => compile(child, style)))])];
    }
    if (items.length >= 2 && isFenceMo(items[0]) && items.at(-1).localName !== 'mo') {
      return [element('m:d', [property('m:d', [element('m:begChr', [], { 'm:val': items[0].textContent }), element('m:endChr', [], { 'm:val': '' })]), element('m:e', items.slice(1).flatMap((child) => compile(child, style)))])];
    }
    if (items.length >= 2 && isFenceMo(items.at(-1)) && items[0].localName !== 'mo') {
      return [element('m:d', [property('m:d', [element('m:begChr', [], { 'm:val': '' }), element('m:endChr', [], { 'm:val': items.at(-1).textContent })]), element('m:e', items.slice(0, -1).flatMap((child) => compile(child, style)))])];
    }
    return sequence();
  }
  const scripts = { msup: ['m:sSup', 'm:e', 'm:sup'], msub: ['m:sSub', 'm:e', 'm:sub'], msubsup: ['m:sSubSup', 'm:e', 'm:sub', 'm:sup'] };
  if (scripts[tag]) {
    const [name, ...parts] = scripts[tag]; arity(parts.length);
    return [element(name, [property(name), ...parts.map((part, index) => expression(part, items[index]))])];
  }
  if (tag === 'mfrac') {
    arity(2);
    const fractionStyle = { ...style, fontSize: (style.fontSize ?? 18) * (style.displayStyle ? 1 : 0.7) };
    return [element('m:f', [property('m:f', [element('m:type', [], { 'm:val': node.getAttribute('linethickness') === '0px' ? 'noBar' : 'bar' })]), element('m:num', compile(items[0], fractionStyle)), element('m:den', compile(items[1], fractionStyle))])];
  }
  if (tag === 'msqrt' || tag === 'mroot') {
    if (tag === 'mroot') arity(2);
    if (!items.length) throw new Error('empty radical');
    return [element('m:rad', [property('m:rad', [element('m:degHide', [], { 'm:val': tag === 'msqrt' ? '1' : '0' })]), tag === 'mroot' ? expression('m:deg', items[1]) : element('m:deg'), element('m:e', tag === 'mroot' ? compile(items[0], style) : sequence())])];
  }
  if (tag === 'mover' || tag === 'munder') {
    arity(2);
    const accent = node.getAttribute(tag === 'mover' ? 'accent' : 'accentunder') === 'true';
    if (accent) {
      const mark = items[1].textContent;
      if (['¯', '‾', '_', '―'].includes(mark)) {
        return [element('m:bar', [property('m:bar', [element('m:pos', [], { 'm:val': tag === 'mover' ? 'top' : 'bot' })]), expression('m:e', items[0])])];
      }
      if (tag === 'munder') throw new Error(`unsupported under-accent: ${mark}`);
      const marks = { '^': '\u0302', '~': '\u0303', '˜': '\u0303', '˙': '\u0307', '¨': '\u0308', 'ˇ': '\u030C', '´': '\u0301', '`': '\u0300', '→': '\u20D7' };
      return [element('m:acc', [property('m:acc', [element('m:chr', [], { 'm:val': marks[mark] ?? mark })]), expression('m:e', items[0])])];
    }
    const name = tag === 'mover' ? 'm:limUpp' : 'm:limLow';
    return [element(name, [property(name), expression('m:e', items[0]), expression('m:lim', items[1])])];
  }
  if (tag === 'munderover') {
    arity(3);
    const upper = element('m:limUpp', [property('m:limUpp'), expression('m:e', items[0]), expression('m:lim', items[2])]);
    return [element('m:limLow', [property('m:limLow'), element('m:e', [upper]), expression('m:lim', items[1])])];
  }
  if (tag === 'mtable') {
    for (const attribute of ['columnlines', 'rowlines']) {
      if (node.hasAttribute(attribute) && /(?:solid|dashed)/.test(node.getAttribute(attribute))) throw new Error(`ruled formula arrays (${attribute}) are not supported by editable Office Math`);
    }
    if (!items.length || items.some((row) => row.localName !== 'mtr')) throw new Error('invalid formula matrix');
    const columns = children(items[0]).length;
    if (!columns || items.some((row) => children(row).length !== columns || children(row).some((cell) => cell.localName !== 'mtd'))) throw new Error('formula matrices must be rectangular');
    const alignments = (node.getAttribute('columnalign') || 'center').split(/\s+/);
    const definitions = Array.from({ length: columns }, (_, index) => element('m:mc', [element('m:mcPr', [element('m:count', [], { 'm:val': '1' }), element('m:mcJc', [], { 'm:val': alignments[index] ?? alignments.at(-1) })])]));
    return [element('m:m', [property('m:m', [element('m:mcs', definitions)]), ...items.map((row) => element('m:mr', children(row).map((cell) => element('m:e', children(cell).flatMap((child) => compile(child, style))))))])];
  }
  if (tag === 'mfenced') {
    const separators = node.getAttribute('separators') || ',';
    const contents = items.flatMap((child, index) => [...(index ? [run(separators[Math.min(index - 1, separators.length - 1)], style)] : []), ...compile(child, style)]);
    return [element('m:d', [property('m:d', [element('m:begChr', [], { 'm:val': node.getAttribute('open') || '(' }), element('m:endChr', [], { 'm:val': node.getAttribute('close') || ')' })]), element('m:e', contents)])];
  }
  throw new Error(`unsupported formula construct: <${tag}>`);
}
export function latexToOmml(latex, style = {}) {
  const rendered = katex.renderToString(latex, { output: 'mathml', displayMode: false, throwOnError: true, trust: false, strict: 'error', maxExpand: 1000 });
  const parsed = parse(rendered);
  const math = parsed.getElementsByTagName('math')[0];
  const semantics = math?.getElementsByTagName('semantics')[0];
  const tree = first(semantics ?? math);
  if (!tree) throw new Error('formula has no MathML presentation tree');
  const nodes = compile(tree, { color: style.color ?? undefined, fontSize: style.fontSize ?? undefined, bold: style.bold, opacity: style.opacity ?? undefined });
  if (!nodes.length) throw new Error('formula produced no Office Math content');
  return serializer.serializeToString(element('m:oMath', nodes));
}

function normalizeLegacy(text, location) {
  if (!text.includes('data-math')) return text;
  const parsed = parse(`<body>${text}</body>`, 'text/html');
  for (const node of [...parsed.getElementsByTagName('span')]) {
    if (!node.hasAttribute('data-math-node') && !node.hasAttribute('data-math')) continue;
    const tex = node.getAttribute('data-tex');
    if (!tex?.trim()) throw new Error(`${location}: legacy math span has no data-tex`);
    node.removeAttribute('data-math-node'); node.removeAttribute('data-math'); node.removeAttribute('data-tex');
    while (node.firstChild) node.removeChild(node.firstChild);
    node.appendChild(parsed.createTextNode(`\\(${tex}\\)`));
  }
  return [...parsed.documentElement.childNodes].map((node) => serializer.serializeToString(node)).join('');
}
function inspectText(holder, location, mutate = true) {
  if (typeof holder.text !== 'string') return [];
  const textWithMath = normalizeLegacy(holder.text, location);
  if (mutate) holder.text = textWithMath;
  if (!/\\[()]/.test(textWithMath)) return [];
  const normalized = textWithMath.replace(/\\\(([\s\S]*?)\\\)/g, (whole, latex) => {
    if (/<\/?(?:p|span|strong|em|u|s|sup|sub|a|ul|ol|li|br)\b[^>]*>/i.test(latex)) throw new Error(`${location}: rich-text tags are not allowed inside formulas`);
    return `\\(${latex.replace(/&(?!(?:#\d+|#x[\da-f]+|[a-z][\w]*);)/gi, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}\\)`;
  });
  const richText = /<\/?(?:p|span|strong|em|u|s|sup|sub|a|ul|ol|li|br)\b[^>]*>/i.test(textWithMath.replace(/\\\([\s\S]*?\\\)/g, ''));
  const parsed = parse(richText ? `<body>${normalized}</body>` : '<body/>', richText ? 'text/html' : 'application/xml');
  if (!richText) parsed.documentElement.appendChild(parsed.createTextNode(textWithMath));
  const formulas = [];
  const visit = (node) => {
    if (node.nodeType === 3) {
      const text = node.textContent;
      let position = 0;
      while (position < text.length) {
        const start = text.indexOf('\\(', position);
        const closing = text.indexOf('\\)', position);
        if (closing >= 0 && (start < 0 || closing < start)) throw new Error(`${location}: unmatched formula closing delimiter`);
        if (start < 0) break;
        const end = text.indexOf('\\)', start + 2);
        if (end < 0) throw new Error(`${location}: unclosed formula or a tag splitting its delimiters`);
        const nested = text.indexOf('\\(', start + 2);
        if (nested >= 0 && nested < end) throw new Error(`${location}: nested formula delimiters`);
        const latex = text.slice(start + 2, end).trim();
        if (!latex) throw new Error(`${location}: empty formula`);
        try { latexToOmml(latex); } catch (error) { throw new Error(`${location}: formula ${JSON.stringify(latex)}: ${error.message}`); }
        formulas.push({ latex, location }); position = end + 2;
      }
    }
    for (const child of [...node.childNodes]) visit(child);
  };
  visit(parsed);
  if (mutate && richText) holder.text = normalized;
  return formulas;
}

export function validateFormulas(pages) {
  let count = 0;
  for (const page of pages) {
    for (const item of page.elements) {
      const location = `${page.pagePath}: ${item.elementId}`;
      if (item.elementType === 'text') count += inspectText(item.content, location, false).length;
      if (item.elementType === 'table') {
        item.rows.forEach((row, r) => row.forEach((cell, c) => {
          count += inspectText(cell, `${location}.rows[${r}][${c}]`, false).length;
        }));
      }
    }
  }
  return count;
}

export function exportWithMath(write, project, options, signature) {
  const expected = [];
  for (const page of project.pages) {
    for (const item of page.elements) {
      const location = `${page.pagePath}: ${item.elementId}`;
      if (item.elementType === 'text') expected.push(...inspectText(item.content, location));
      if (item.elementType === 'table') item.rows.forEach((row, r) => row.forEach((cell, c) => expected.push(...inspectText(cell, `${location}.rows[${r}][${c}]`))));
    }
  }
  const queues = new Map();
  for (const item of expected) {
    if (!queues.has(item.latex)) queues.set(item.latex, []);
    queues.get(item.latex).push(item);
  }
  let calls = 0;
  const failures = [];
  const bytes = write(project, { ...options, mathLoader: (latex, style) => {
    const normalized = latex.trim();
    const queue = queues.get(normalized);
    const match = queue?.length ? queue.shift() : undefined;
    calls += 1;
    if (!match) { failures.push(`writer requested an unexpected formula: ${JSON.stringify(latex)}`); return null; }
    try { return latexToOmml(normalized, style); }
    catch (error) { failures.push(`${match.location}: ${error.message}`); return null; }
  } }, typeof signature === 'function' ? signature(JSON.stringify(project)) : signature);
  // The writer swallows callback errors and invokes its incomplete native fallback.
  if (failures.length) throw new Error(failures.join('\n'));
  if (calls !== expected.length) throw new Error(`formula conversion count mismatch: expected ${expected.length}, got ${calls}`);
  return { bytes, formulas: calls };
}
