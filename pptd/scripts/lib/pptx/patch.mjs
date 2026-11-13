// OOXML postprocessing for capabilities the WASM writer cannot express natively:
// grouped RIBBI font bindings and native table/cell image fills.
import crypto from 'node:crypto';
import { DOMImplementation, DOMParser, XMLSerializer } from '../../../assets/vendor/xmldom.mjs';
import { tableCells } from '../deck/schema.mjs';
import { readZip, updateZip } from './zip.mjs';

const P = 'http://schemas.openxmlformats.org/presentationml/2006/main';
const A = 'http://schemas.openxmlformats.org/drawingml/2006/main';
const R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';
const REL = 'http://schemas.openxmlformats.org/package/2006/relationships';
const CT = 'http://schemas.openxmlformats.org/package/2006/content-types';

const MIME = { png: 'image/png', jpg: 'image/jpeg', gif: 'image/gif', svg: 'image/svg+xml' };
const FILL_NAMES = new Set(['noFill', 'solidFill', 'gradFill', 'blipFill', 'pattFill', 'grpFill']);
const AFTER_FILL = new Set(['effectLst', 'effectDag', 'tableStyle', 'tableStyleId', 'extLst']);
const SLOTS = ['regular', 'bold', 'italic', 'boldItalic'];

const serializer = new XMLSerializer();

function parseXml(buffer, label = 'XML') {
  const text = Buffer.isBuffer(buffer) ? buffer.toString('utf8') : String(buffer);
  return new DOMParser({
    onError(level, message) {
      if (level !== 'warning') throw new Error(`invalid ${label}: ${message}`);
    },
  }).parseFromString(text, 'application/xml');
}

function serializeXml(doc) {
  let xml = serializer.serializeToString(doc);
  if (!xml.startsWith('<?xml')) {
    xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + xml;
  }
  return Buffer.from(xml, 'utf8');
}

function childElements(node, ns = null, localName = null) {
  const out = [];
  for (let child = node.firstChild; child; child = child.nextSibling) {
    if (child.nodeType !== 1) continue;
    if (ns && child.namespaceURI !== ns) continue;
    if (localName && child.localName !== localName) continue;
    out.push(child);
  }
  return out;
}

function firstChild(node, ns, localName) {
  return childElements(node, ns, localName)[0] ?? null;
}

export function patchFontBindings(pptxBuffer, bindings) {
  if (!bindings?.length) return pptxBuffer;
  const archive = readZip(pptxBuffer);
  const doc = parseXml(archive.read('ppt/presentation.xml'), 'ppt/presentation.xml');
  const root = doc.documentElement;
  const listing = firstChild(root, P, 'embeddedFontLst');
  const entries = listing ? childElements(listing) : [];
  if (entries.length !== bindings.length) {
    throw new Error('writer font-part count does not match the prepared font bindings');
  }

  const groups = new Map();
  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i];
    const binding = bindings[i];
    const { family, slot } = binding;
    if (!SLOTS.includes(slot)) throw new Error(`unsupported embedded font style: ${slot}`);
    const font = firstChild(entry, P, 'font');
    const link = firstChild(entry, P, 'regular');
    if (!font || !link) throw new Error('writer emitted an incomplete embedded font entry');

    let groupInfo = groups.get(family);
    if (!groupInfo) {
      const group = doc.createElementNS(P, 'p:embeddedFont');
      const fontNode = doc.createElementNS(P, 'p:font');
      fontNode.setAttribute('typeface', family);
      fontNode.setAttribute('charset', String(binding.charset));
      fontNode.setAttribute('pitchFamily', String(binding.pitchFamily));
      groupInfo = { group, fontNode, slots: new Map() };
      groups.set(family, groupInfo);
    }
    if (groupInfo.slots.has(slot)) throw new Error(`duplicate embedded font style: ${family} / ${slot}`);
    const slotNode = doc.createElementNS(P, `p:${slot}`);
    for (let a = 0; a < link.attributes.length; a++) {
      const attr = link.attributes[a];
      if (attr.namespaceURI) slotNode.setAttributeNS(attr.namespaceURI, attr.name, attr.value);
      else slotNode.setAttribute(attr.name, attr.value);
    }
    groupInfo.slots.set(slot, slotNode);
  }

  while (listing.firstChild) listing.removeChild(listing.firstChild);
  for (const { group, fontNode, slots } of groups.values()) {
    group.appendChild(fontNode);
    for (const slot of SLOTS) {
      const node = slots.get(slot);
      if (node) group.appendChild(node);
    }
    listing.appendChild(group);
  }
  root.setAttribute('embedTrueTypeFonts', '1');
  root.setAttribute('saveSubsetFonts', '0');

  return updateZip(pptxBuffer, { 'ppt/presentation.xml': serializeXml(doc) });
}

function replaceFill(doc, properties, fillNode) {
  const nodes = childElements(properties);
  const existing = nodes.filter((node) => FILL_NAMES.has(node.localName));
  const anchor = existing[0] ?? nodes.find((node) => AFTER_FILL.has(node.localName)) ?? null;
  properties.insertBefore(fillNode, anchor);
  for (const old of existing) properties.removeChild(old);
}

function buildImageFill(doc, fill, relationship, info, width, height) {
  const result = doc.createElementNS(A, 'a:blipFill');
  const blip = doc.createElementNS(A, 'a:blip');
  blip.setAttributeNS(R, 'r:embed', relationship);
  if ((fill.opacity ?? 1) < 1) {
    const alpha = doc.createElementNS(A, 'a:alphaModFix');
    alpha.setAttribute('amt', String(Math.round(fill.opacity * 100000)));
    blip.appendChild(alpha);
  }
  result.appendChild(blip);

  const crop = {
    l: fill.crop?.left ?? 0,
    t: fill.crop?.top ?? 0,
    r: fill.crop?.right ?? 0,
    b: fill.crop?.bottom ?? 0,
  };
  const mode = fill.fit?.mode ?? 'cover';
  const rect = {};
  if (width > 0 && height > 0 && mode !== 'fill') {
    if (info.width == null || info.height == null) {
      throw new Error('table image fills require intrinsic SVG dimensions or viewBox');
    }
    const remW = 1 - crop.l - crop.r;
    const remH = 1 - crop.t - crop.b;
    const aspect = (info.width * remW) / (info.height * remH);
    const target = width / height;
    if (mode === 'cover') {
      if (aspect > target) {
        const extra = (remW * (1 - target / aspect)) / 2;
        crop.l += extra;
        crop.r += extra;
      } else {
        const extra = (remH * (1 - aspect / target)) / 2;
        crop.t += extra;
        crop.b += extra;
      }
    } else if (mode === 'contain') {
      if (aspect > target) {
        rect.t = (1 - target / aspect) / 2;
        rect.b = rect.t;
      } else {
        rect.l = (1 - aspect / target) / 2;
        rect.r = rect.l;
      }
    }
  }
  if (Object.values(crop).some((v) => v !== 0)) {
    const srcRect = doc.createElementNS(A, 'a:srcRect');
    for (const [k, v] of Object.entries(crop)) srcRect.setAttribute(k, String(Math.round(v * 100000)));
    result.appendChild(srcRect);
  }
  const stretch = doc.createElementNS(A, 'a:stretch');
  const fillRect = doc.createElementNS(A, 'a:fillRect');
  for (const [k, v] of Object.entries(rect)) fillRect.setAttribute(k, String(Math.round(v * 100000)));
  stretch.appendChild(fillRect);
  result.appendChild(stretch);
  return result;
}

export function patchTableImages(pptxBuffer, project, mediaRecords) {
  const sources = new Map();
  for (const record of mediaRecords) {
    sources.set(record.source, record);
    sources.set(record.key, record);
  }
  const archive = readZip(pptxBuffer);
  const typesDoc = parseXml(archive.read('[Content_Types].xml'), '[Content_Types].xml');
  const extensions = new Set(
    childElements(typesDoc.documentElement, null, 'Default').map((el) => el.getAttribute('Extension')),
  );
  const known = new Map();
  for (const name of archive.names()) {
    if (name.startsWith('ppt/media/')) {
      const digest = crypto.createHash('sha256').update(archive.read(name)).digest('hex');
      known.set(digest, name);
    }
  }

  const updates = new Map();
  let count = 0;
  const theme = project.manifest.theme ?? {};

  for (let i = 0; i < project.pages.length; i++) {
    const page = project.pages[i];
    const pageIndex = i + 1;
    const slideName = `ppt/slides/slide${pageIndex}.xml`;
    const slideDoc = parseXml(archive.read(slideName), slideName);
    const relsName = `ppt/slides/_rels/slide${pageIndex}.xml.rels`;
    const relsDoc = archive.has(relsName)
      ? parseXml(archive.read(relsName), relsName)
      : new DOMImplementation().createDocument(REL, 'Relationships', null);
    let changed = false;

    const apply = (properties, fill, width, height) => {
      const record = sources.get(fill.src);
      if (!record) throw new Error(`${page.path}: table image was not resolved: ${fill.src}`);
      const data = Buffer.isBuffer(record.bytes) ? record.bytes : Buffer.from(record.bytes);
      const info = record.info;
      const digest = crypto.createHash('sha256').update(data).digest('hex');
      let target = known.get(digest);
      if (!target) {
        target = `ppt/media/pptd-table-${digest.slice(0, 24)}.${info.ext}`;
        known.set(digest, target);
        updates.set(target, data);
      }
      const existingIds = new Set(childElements(relsDoc.documentElement).map((el) => el.getAttribute('Id')));
      let idx = 1;
      while (existingIds.has(`rIdPptdTableImage${idx}`)) idx += 1;
      const relationship = `rIdPptdTableImage${idx}`;
      const relEl = relsDoc.createElementNS(REL, 'Relationship');
      relEl.setAttribute('Id', relationship);
      relEl.setAttribute('Type', `${R}/image`);
      relEl.setAttribute('Target', `../media/${target.split('/').at(-1)}`);
      relsDoc.documentElement.appendChild(relEl);

      if (!extensions.has(info.ext)) {
        const defEl = typesDoc.createElementNS(CT, 'Default');
        defEl.setAttribute('Extension', info.ext);
        defEl.setAttribute('ContentType', MIME[info.ext]);
        typesDoc.documentElement.appendChild(defEl);
        extensions.add(info.ext);
      }
      replaceFill(slideDoc, properties, buildImageFill(slideDoc, fill, relationship, info, width, height));
      count += 1;
      changed = true;
    };

    const frames = [...slideDoc.getElementsByTagNameNS(P, 'graphicFrame')];
    for (const table of page.data.elements) {
      if (table.elementType !== 'table') continue;
      const frame = frames.find((candidate) => {
        const nv = firstChild(candidate, P, 'nvGraphicFramePr');
        const cNvPr = nv ? firstChild(nv, P, 'cNvPr') : null;
        return cNvPr?.getAttribute('name') === table.elementId;
      });
      if (!frame) throw new Error(`${page.path}: writer omitted table ${table.elementId}`);
      const native = frame.getElementsByTagNameNS(A, 'tbl')[0];
      if (!native) throw new Error(`${page.path}: writer emitted no native table for ${table.elementId}`);
      const nativeRows = childElements(native, A, 'tr');
      const [, , width, height] = table.bounds;

      if (table.fill && typeof table.fill === 'object' && table.fill.type === 'image') {
        let tblPr = firstChild(native, A, 'tblPr');
        if (!tblPr) {
          tblPr = slideDoc.createElementNS(A, 'a:tblPr');
          native.insertBefore(tblPr, native.firstChild);
        }
        apply(tblPr, table.fill, width, height);
      }

      for (const cell of tableCells(table, theme, table.elementId)) {
        const fill = cell.style.fill;
        if (!fill || typeof fill !== 'object' || fill.type !== 'image') continue;
        const rowEl = nativeRows[cell.row];
        const colEl = childElements(rowEl, A, 'tc')[cell.column];
        let tcPr = firstChild(colEl, A, 'tcPr');
        if (!tcPr) {
          tcPr = slideDoc.createElementNS(A, 'a:tcPr');
          colEl.appendChild(tcPr);
        }
        const spanW = width * table.columnWidths.slice(cell.column, cell.column + cell.colSpan).reduce((s, v) => s + v, 0);
        const spanH = height * table.rowHeights.slice(cell.row, cell.row + cell.rowSpan).reduce((s, v) => s + v, 0);
        apply(tcPr, fill, spanW, spanH);
      }
    }

    if (changed) {
      updates.set(slideName, serializeXml(slideDoc));
      updates.set(relsName, serializeXml(relsDoc));
    }
  }

  if (count > 0) updates.set('[Content_Types].xml', serializeXml(typesDoc));
  return { buffer: updateZip(pptxBuffer, updates), count };
}
