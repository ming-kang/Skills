// Shared XML DOM parsing, serialization, creation and traversal helpers.
import { DOMImplementation, DOMParser, XMLSerializer } from '../../../assets/vendor/xmldom.mjs';

export const NS = Object.freeze({
  presentation: 'http://schemas.openxmlformats.org/presentationml/2006/main',
  drawing: 'http://schemas.openxmlformats.org/drawingml/2006/main',
  relationships: 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
  packageRelationships: 'http://schemas.openxmlformats.org/package/2006/relationships',
  contentTypes: 'http://schemas.openxmlformats.org/package/2006/content-types',
  math: 'http://schemas.openxmlformats.org/officeDocument/2006/math',
  svg: 'http://www.w3.org/2000/svg',
  xml: 'http://www.w3.org/XML/1998/namespace',
  pptd: 'https://pptd.local/ns/2026/pptd/schema',
});

const XML_FORBIDDEN = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\ud800-\udfff\ufffe\uffff]/u;
const domImpl = new DOMImplementation();
const serializer = new XMLSerializer();

export function checkXmlString(value, label) {
  const match = XML_FORBIDDEN.exec(value);
  if (match) throw new Error(`${label} contains an XML-forbidden character U+${match[0].codePointAt(0).toString(16).toUpperCase().padStart(4, '0')}`);
}

export function createXmlDocument(ns = '', qualifiedName = 'root') {
  return domImpl.createDocument(ns, qualifiedName, null);
}

export function parseXml(input, label = 'XML', { mime = 'application/xml' } = {}) {
  const text = Buffer.isBuffer(input) ? input.toString('utf8') : String(input);
  if (mime !== 'text/html') checkXmlString(text, `invalid XML part ${label}:`);
  let failure = null, doc;
  try {
    doc = new DOMParser({
      onError(level, message) {
        if (level !== 'warning') failure ??= message;
      },
    }).parseFromString(text, mime);
  } catch (error) {
    // Fatal parser errors are thrown rather than reported; give both one message shape.
    failure ??= error.message;
  }
  if (failure || !doc?.documentElement) {
    const kind = { 'image/svg+xml': 'SVG part', 'text/html': 'rich text' }[mime] ?? 'XML part';
    throw new Error(`invalid ${kind} ${label}: ${failure ?? 'missing root element'}`);
  }
  return doc;
}

export function serializeXml(doc, { declaration = true } = {}) {
  let xml = serializer.serializeToString(doc);
  if (declaration && !xml.startsWith('<?xml')) {
    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + xml;
  }
  return declaration ? Buffer.from(xml, 'utf8') : xml;
}

export function serializeNode(node) {
  return serializer.serializeToString(node);
}

export function childElements(node, ns = null, localName = null) {
  const out = [];
  for (let child = node.firstChild; child; child = child.nextSibling) {
    if (child.nodeType !== 1) continue;
    if (ns && child.namespaceURI !== ns) continue;
    if (localName && child.localName !== localName) continue;
    out.push(child);
  }
  return out;
}

export function firstChild(node, ns, localName) {
  return childElements(node, ns, localName)[0] ?? null;
}

export function createElement(doc, ns, qualifiedName, attrs = {}, children = []) {
  const node = doc.createElementNS(ns, qualifiedName);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null) continue;
    if (typeof value === 'object' && 'ns' in value) {
      node.setAttributeNS(value.ns, key, String(value.value));
    } else {
      node.setAttribute(key, String(value));
    }
  }
  for (const child of children.flat().filter(Boolean)) {
    node.appendChild(child);
  }
  return node;
}
