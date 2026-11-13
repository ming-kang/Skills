// Shared XML DOM parsing, serialization and traversal helpers for OOXML patching & verification.
import { DOMParser, XMLSerializer } from '../../../assets/vendor/xmldom.mjs';

const XML_FORBIDDEN = /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/;
const serializer = new XMLSerializer();

export function parseXml(buffer, label = 'XML') {
  const text = Buffer.isBuffer(buffer) ? buffer.toString('utf8') : String(buffer);
  if (XML_FORBIDDEN.test(text)) {
    throw new Error(`invalid XML part ${label}: forbidden control character`);
  }
  let failure = null;
  const doc = new DOMParser({
    onError(level, message) {
      if (level !== 'warning' && !failure) failure = message;
    },
  }).parseFromString(text, 'application/xml');
  if (failure || !doc?.documentElement) {
    throw new Error(`invalid XML part ${label}: ${failure ?? 'missing root element'}`);
  }
  return doc;
}

export function serializeXml(doc) {
  let xml = serializer.serializeToString(doc);
  if (!xml.startsWith('<?xml')) {
    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + xml;
  }
  return Buffer.from(xml, 'utf8');
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
