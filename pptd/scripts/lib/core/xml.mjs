// Shared XML DOM parsing, serialization, creation and traversal helpers.
import { DOMImplementation, DOMParser, XMLSerializer } from '../../../assets/vendor/xmldom.mjs';

const XML_FORBIDDEN = /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/;
const domImpl = new DOMImplementation();
const serializer = new XMLSerializer();

export function createXmlDocument(ns = '', qualifiedName = 'root') {
  return domImpl.createDocument(ns, qualifiedName, null);
}

export function parseXml(input, label = 'XML', { mime = 'application/xml' } = {}) {
  const text = Buffer.isBuffer(input) ? input.toString('utf8') : String(input);
  if (mime === 'application/xml' && XML_FORBIDDEN.test(text)) {
    throw new Error(`invalid XML part ${label}: forbidden control character`);
  }
  let failure = null;
  const doc = new DOMParser({
    onError(level, message) {
      if (level !== 'warning' && !failure) failure = message;
    },
  }).parseFromString(text, mime);
  if (failure || !doc?.documentElement) {
    throw new Error(`invalid ${mime === 'image/svg+xml' ? 'SVG' : 'XML'} part ${label}: ${failure ?? 'missing root element'}`);
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
