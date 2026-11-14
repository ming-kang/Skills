// OOXML editing session: cached reads are not edits; written bytes and XML stay coherent.
import { createXmlDocument, parseXml, serializeXml } from '../core/xml.mjs';
import { readZip, updateArchive } from './zip.mjs';

export const SLIDE_PART = /^ppt\/slides\/slide\d+\.xml$/;

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
    return this.updates.has(name) || this.archive.has(name);
  }

  names() {
    return [...new Set([...this.archive.names(), ...this.updates.keys()])];
  }

  readBytes(name) {
    if (!this.updates.has(name)) return this.archive.read(name);
    const part = this.updates.get(name);
    return part.documentElement ? serializeXml(part) : part;
  }

  readXml(name) {
    if (!this.xmlDocs.has(name)) this.xmlDocs.set(name, parseXml(this.readBytes(name), name));
    return this.xmlDocs.get(name);
  }

  readOrCreateXml(name, ns, qualifiedName) {
    if (!this.has(name)) this.writeXml(name, createXmlDocument(ns, qualifiedName));
    return this.readXml(name);
  }

  writeXml(name, doc) {
    this.xmlDocs.set(name, doc);
    this.updates.set(name, doc);
  }

  writeBytes(name, data) {
    this.xmlDocs.delete(name);
    this.updates.set(name, data);
  }

  get dirty() {
    return this.updates.size > 0;
  }

  toBuffer() {
    if (!this.dirty) return this.archive.buffer;
    return updateArchive(this.archive, new Map([...this.updates.keys()].map((name) => [name, this.readBytes(name)])));
  }
}
