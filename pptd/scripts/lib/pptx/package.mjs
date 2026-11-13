// Single-pass OOXML ZIP package editing session with lazy XML DOM caching.
import { createXmlDocument, parseXml, serializeXml } from '../core/xml.mjs';
import { readZip, updateArchive } from './zip.mjs';

export class PptxPackage {
  constructor(archive) {
    this.archive = archive;
    this.updates = new Map();
    this.xmlDocs = new Map();
  }

  static open(bytes) {
    return new PptxPackage(readZip(bytes));
  }

  has(name) {
    return this.updates.has(name) || this.xmlDocs.has(name) || this.archive.has(name);
  }

  names() {
    const names = new Set(this.archive.names());
    for (const name of this.updates.keys()) names.add(name);
    for (const name of this.xmlDocs.keys()) names.add(name);
    return [...names];
  }

  readBytes(name) {
    if (this.updates.has(name)) return this.updates.get(name);
    return this.archive.read(name);
  }

  readXml(name) {
    if (this.xmlDocs.has(name)) return this.xmlDocs.get(name);
    const doc = parseXml(this.readBytes(name), name);
    this.xmlDocs.set(name, doc);
    return doc;
  }

  readOrCreateXml(name, ns, qualifiedName) {
    if (this.has(name)) return this.readXml(name);
    const doc = createXmlDocument(ns, qualifiedName);
    this.xmlDocs.set(name, doc);
    return doc;
  }

  writeXml(name, doc) {
    this.xmlDocs.set(name, doc);
  }

  writeBytes(name, data) {
    this.xmlDocs.delete(name);
    this.updates.set(name, data);
  }

  get dirty() {
    return this.updates.size > 0 || this.xmlDocs.size > 0;
  }

  toBuffer() {
    const updates = new Map(this.updates);
    for (const [name, doc] of this.xmlDocs.entries()) {
      updates.set(name, serializeXml(doc));
    }
    return updateArchive(this.archive, updates);
  }
}
