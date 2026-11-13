// Read-only OOXML slide transition checks and full PPTX package integrity verification.
import path from 'node:path';
import { imageInfo, MIME_TYPES } from '../core/media.mjs';
import { childElements, firstChild, parseXml } from '../core/xml.mjs';
import { readZip } from './zip.mjs';

export const PPTX_CONTENT_TYPE =
  'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml';
const SLIDE_NAME_PATTERN = /^ppt\/slides\/slide\d+\.xml$/;
const P_NS = 'http://schemas.openxmlformats.org/presentationml/2006/main';
const R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';

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

function decodeTarget(target, relsName) {
  try {
    return decodeURIComponent(target.split('#')[0]);
  } catch {
    throw new Error(`${relsName}: malformed URI target ${target}`);
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
      defaults.set((item.getAttribute('Extension') ?? '').toLowerCase(), item.getAttribute('ContentType'));
    } else if (item.localName === 'Override') {
      const partName = decodeTarget(item.getAttribute('PartName') ?? '', '[Content_Types].xml').replace(/^\/+/, '');
      overrides.set(partName, item.getAttribute('ContentType'));
    }
  }
  for (const name of names) {
    if (name === '[Content_Types].xml') continue;
    const ext = name.includes('.') ? name.split('.').at(-1).toLowerCase() : '';
    if (!overrides.has(name) && !defaults.has(ext)) {
      throw new Error(`PPTX part has no declared content type: ${name}`);
    }
  }
  for (const part of overrides.keys()) {
    if (!names.has(part)) throw new Error(`PPTX content type references a missing part: ${part}`);
  }

  const relationships = new Map();
  const relTargets = new Map();
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
    const targets = new Map();
    for (const rel of childElements(doc.documentElement)) {
      const id = rel.getAttribute('Id');
      const target = rel.getAttribute('Target');
      if (!id || ids.has(id) || !target) throw new Error(`invalid or duplicate relationship in ${name}`);
      ids.add(id);
      if (rel.getAttribute('TargetMode') === 'External') continue;
      const rawPath = decodeTarget(target, name);
      const joined = rawPath.startsWith('/') ? rawPath.replace(/^\/+/, '') : (base ? `${base}/${rawPath}` : rawPath);
      const resolved = path.posix.normalize(joined).replace(/^\/+/, '');
      if (!names.has(resolved)) {
        throw new Error(`${name}: relationship ${id} targets missing part ${resolved}`);
      }
      targets.set(id, resolved);
    }
    relationships.set(owner, ids);
    relTargets.set(owner, targets);
  }

  for (const [name, doc] of xml.entries()) {
    if (name.endsWith('.rels')) continue;
    verifyXmlRelationships(doc.documentElement, name, relationships);
  }

  // Verify presentation.xml sldIdLst covers every slide part when sldIdLst is present.
  const presDoc = xml.get('ppt/presentation.xml');
  const sldIdLst = presDoc ? firstChild(presDoc.documentElement, P_NS, 'sldIdLst') : null;
  if (sldIdLst) {
    const presTargets = relTargets.get('ppt/presentation.xml') ?? new Map();
    const linkedSlides = new Set();
    for (const sldId of childElements(sldIdLst, P_NS, 'sldId')) {
      const rId = sldId.getAttributeNS(R_NS, 'id');
      const target = presTargets.get(rId);
      if (!target || !SLIDE_NAME_PATTERN.test(target)) {
        throw new Error(`ppt/presentation.xml: sldId ${rId} does not resolve to a slide part`);
      }
      linkedSlides.add(target);
    }
    for (const name of names) {
      if (SLIDE_NAME_PATTERN.test(name) && !linkedSlides.has(name)) {
        throw new Error(`PPTX contains an unlinked slide part: ${name}`);
      }
    }
  }

  for (const name of names) {
    if (!name.startsWith('ppt/media/')) continue;
    const info = imageInfo(archive.read(name), name);
    const ext = name.includes('.') ? name.split('.').at(-1).toLowerCase() : '';
    const declared = overrides.get(name) ?? defaults.get(ext);
    if (declared !== MIME_TYPES[info.ext]) {
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
