// OOXML slide transition patching and full PPTX package integrity verification.
import path from 'node:path';
import { DOMParser } from '../../../assets/vendor/xmldom.mjs';
import { imageInfo } from '../prepare/media.mjs';
import { readZip, updateZip } from './zip.mjs';

export const PPTX_CONTENT_TYPE =
  'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml';
const FADE_TRANSITION_XML = '<p:transition spd="fast" advClick="1"><p:fade/></p:transition>';
const SLIDE_NAME_PATTERN = /^ppt\/slides\/slide\d+\.xml$/;
const R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';
const MIME = { png: 'image/png', jpg: 'image/jpeg', gif: 'image/gif', svg: 'image/svg+xml' };
const XML_FORBIDDEN = /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/;

function parseXml(buffer, label) {
  const text = Buffer.isBuffer(buffer) ? buffer.toString('utf8') : String(buffer);
  if (XML_FORBIDDEN.test(text)) throw new Error(`invalid XML part ${label}: forbidden control character`);
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

function childElements(node) {
  const out = [];
  for (let child = node.firstChild; child; child = child.nextSibling) {
    if (child.nodeType === 1) out.push(child);
  }
  return out;
}

export function replaceTransition(slideXml, transition) {
  let text = Buffer.isBuffer(slideXml) ? slideXml.toString('utf8') : String(slideXml);
  text = text.replace(/<p:transition\b[^>]*(?:\/>|>[\s\S]*?<\/p:transition>)/g, '');
  if (transition === 'none') return Buffer.from(text, 'utf8');

  const colorMap = /<p:clrMapOvr\b[^>]*(?:\/>|>[\s\S]*?<\/p:clrMapOvr>)/.exec(text);
  const commonSlide = /<p:cSld\b[^>]*(?:\/>|>[\s\S]*?<\/p:cSld>)/.exec(text);
  const anchor = colorMap ?? commonSlide;
  if (!anchor) throw new Error('slide XML has no cSld/clrMapOvr insertion anchor');
  const position = anchor.index + anchor[0].length;
  return Buffer.from(text.slice(0, position) + FADE_TRANSITION_XML + text.slice(position), 'utf8');
}

export function slideTransitionFacts(slideXml) {
  let doc;
  try {
    doc = parseXml(slideXml, 'slide XML');
  } catch (error) {
    throw new Error(`invalid slide XML: ${error.message}`);
  }
  const children = childElements(doc.documentElement);
  const names = children.map((node) => node.localName);
  const transitionIndexes = [];
  for (let i = 0; i < names.length; i++) {
    if (names[i] === 'transition') transitionIndexes.push(i);
  }
  const hasDirectFade = transitionIndexes.length > 0 &&
    childElements(children[transitionIndexes[0]]).some((node) => node.localName === 'fade');
  return { names, transitionIndexes, hasDirectFade };
}

export function validateTransitionOrder(facts, transition) {
  if (transition === 'none') {
    if (facts.transitionIndexes.length) throw new Error('transition=none left a root-level transition');
    return;
  }
  if (facts.transitionIndexes.length !== 1 || !facts.hasDirectFade) {
    throw new Error('slide does not contain exactly one root-level fade transition');
  }
  const index = facts.transitionIndexes[0];
  for (const before of ['cSld', 'clrMapOvr']) {
    const pos = facts.names.indexOf(before);
    if (pos >= 0 && pos > index) throw new Error(`${before} appears after transition`);
  }
  for (const after of ['timing', 'extLst']) {
    const pos = facts.names.indexOf(after);
    if (pos >= 0 && pos < index) throw new Error(`${after} appears before transition`);
  }
}

export function patchTransitions(pptxBuffer, transition) {
  const archive = readZip(pptxBuffer);
  const updates = new Map();
  let slideCount = 0;
  for (const name of archive.names()) {
    if (SLIDE_NAME_PATTERN.test(name)) {
      updates.set(name, replaceTransition(archive.read(name), transition));
      slideCount += 1;
    }
  }
  if (slideCount === 0) throw new Error('exported PPTX contains no slide XML');
  return { buffer: updateZip(pptxBuffer, updates), slideCount };
}

function verifyXmlRelationships(node, owner, relationships) {
  if (node.nodeType !== 1) return;
  const attrs = node.attributes;
  if (attrs) {
    for (let i = 0; i < attrs.length; i++) {
      const attr = attrs[i];
      if (attr.namespaceURI === R_NS && (attr.localName === 'id' || attr.localName === 'embed' || attr.localName === 'link')) {
        const ids = relationships.get(owner);
        if (!ids || !ids.has(attr.value)) {
          throw new Error(`${owner}: missing relationship ${attr.value}`);
        }
      }
    }
  }
  for (let child = node.firstChild; child; child = child.nextSibling) {
    if (child.nodeType === 1) verifyXmlRelationships(child, owner, relationships);
  }
}

function verifyParts(archive) {
  const names = new Set(archive.names());
  const xml = new Map();
  for (const name of [...names].sort()) {
    if (name.endsWith('.xml') || name.endsWith('.rels')) {
      xml.set(name, parseXml(archive.read(name), name));
    }
  }
  const typesDoc = xml.get('[Content_Types].xml');
  if (!typesDoc) throw new Error('PPTX is missing [Content_Types].xml');
  const defaults = new Map();
  const overrides = new Map();
  for (const item of childElements(typesDoc.documentElement)) {
    if (item.localName === 'Default') {
      defaults.set(item.getAttribute('Extension'), item.getAttribute('ContentType'));
    } else if (item.localName === 'Override') {
      const partName = decodeURIComponent(item.getAttribute('PartName') ?? '').replace(/^\/+/, '');
      overrides.set(partName, item.getAttribute('ContentType'));
    }
  }
  for (const name of names) {
    if (name === '[Content_Types].xml') continue;
    const ext = name.includes('.') ? name.split('.').at(-1) : '';
    if (!overrides.has(name) && !defaults.has(ext)) {
      throw new Error(`PPTX part has no declared content type: ${name}`);
    }
  }
  for (const part of overrides.keys()) {
    if (!names.has(part)) throw new Error(`PPTX content type references a missing part: ${part}`);
  }

  const relationships = new Map();
  for (const [name, doc] of xml.entries()) {
    if (!name.endsWith('.rels')) continue;
    let owner = '';
    let base = '';
    if (name !== '_rels/.rels') {
      const dir = path.posix.dirname(name);
      base = path.posix.dirname(dir);
      if (base === '.') base = '';
      owner = base ? `${base}/${path.posix.basename(name).slice(0, -5)}` : path.posix.basename(name).slice(0, -5);
    }
    const ids = new Set();
    for (const rel of childElements(doc.documentElement)) {
      const id = rel.getAttribute('Id');
      const target = rel.getAttribute('Target');
      if (!id || ids.has(id) || !target) throw new Error(`invalid or duplicate relationship in ${name}`);
      ids.add(id);
      if (rel.getAttribute('TargetMode') === 'External') continue;
      const rawPath = decodeURIComponent(target.split('#')[0]);
      const joined = rawPath.startsWith('/') ? rawPath.replace(/^\/+/, '') : (base ? `${base}/${rawPath}` : rawPath);
      const resolved = path.posix.normalize(joined).replace(/^\/+/, '');
      if (!names.has(resolved)) {
        throw new Error(`${name}: relationship ${id} targets missing part ${resolved}`);
      }
    }
    relationships.set(owner, ids);
  }

  for (const [name, doc] of xml.entries()) {
    if (name.endsWith('.rels')) continue;
    verifyXmlRelationships(doc.documentElement, name, relationships);
  }

  for (const name of names) {
    if (!name.startsWith('ppt/media/')) continue;
    const info = imageInfo(archive.read(name), name);
    const ext = name.includes('.') ? name.split('.').at(-1) : '';
    const declared = overrides.get(name) ?? defaults.get(ext);
    if (declared !== MIME[info.ext]) {
      throw new Error(`${name}: media bytes do not match declared content type ${declared}`);
    }
  }
  return xml.size;
}

export function verifyOutput(pptxBuffer, transition, expectedSlides = null) {
  const archive = readZip(pptxBuffer);
  if (!archive.has('ppt/presentation.xml')) {
    throw new Error('output is not a valid PPTX ZIP: missing ppt/presentation.xml');
  }
  if (!archive.has('[Content_Types].xml') || !archive.read('[Content_Types].xml').includes(PPTX_CONTENT_TYPE)) {
    throw new Error('output is not a valid PPTX ZIP: missing main content type');
  }
  archive.verifyAll();
  const xmlParts = verifyParts(archive);
  const slideNames = archive.names().filter((name) => SLIDE_NAME_PATTERN.test(name));
  if (expectedSlides !== null && slideNames.length !== expectedSlides) {
    throw new Error(`PPTX slide count mismatch: expected ${expectedSlides}, got ${slideNames.length}`);
  }
  let fadeCount = 0;
  for (const name of slideNames) {
    const facts = slideTransitionFacts(archive.read(name));
    validateTransitionOrder(facts, transition);
    if (facts.hasDirectFade) fadeCount += 1;
  }
  if (transition === 'fade' && fadeCount !== slideNames.length) {
    throw new Error('fade transition was not written to every slide');
  }
  const fontParts = archive.names().filter((name) => name.startsWith('ppt/fonts/'));
  return {
    slides: slideNames.length,
    fadeTransitions: fadeCount,
    fontParts: fontParts.length,
    xmlParts,
    bytes: pptxBuffer.length,
  };
}
