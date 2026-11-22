import fs from 'node:fs';
import path from 'node:path';

import { parseXml, serializeXml } from '../../../pptd/scripts/lib/core/xml.mjs';
import { patchTransitions } from '../../../pptd/scripts/lib/pptx/patch.mjs';
import { readZip, updateArchive } from '../../../pptd/scripts/lib/pptx/zip.mjs';

export function updateZip(buffer, updates) {
  if (!updates || (updates instanceof Map ? updates.size === 0 : Object.keys(updates).length === 0)) {
    return Buffer.isBuffer(buffer) ? buffer : Buffer.from(buffer);
  }
  return updateArchive(readZip(buffer), updates);
}

/** Drive the real patchTransitions pass on a one-slide stub package. */
export function replaceTransition(slideXml, transition) {
  let result;
  patchTransitions({
    names: () => ['ppt/slides/slide1.xml'],
    readXml: () => parseXml(slideXml, 'slide XML'),
    writeXml: (name, doc) => { result = serializeXml(doc); },
  }, transition);
  return result;
}

export function makeDeck(root, { manifest, page } = {}) {
  fs.mkdirSync(path.join(root, 'pages'), { recursive: true });
  const manifestPath = path.join(root, 'deck.pptd');
  fs.writeFileSync(
    manifestPath,
    manifest ?? [
      'version: v2',
      'title: Validation fixture',
      'size: [960, 540]',
      'pages:',
      '  - pages/01.page',
      '',
    ].join('\n'),
    'utf8',
  );
  fs.writeFileSync(
    path.join(root, 'pages', '01.page'),
    page ?? [
      'elements:',
      '  - elementId: title',
      '    elementType: text',
      '    bounds: [100, 100, 400, 80]',
      '    content:',
      '      text: Hello',
      '',
    ].join('\n'),
    'utf8',
  );
  return manifestPath;
}
