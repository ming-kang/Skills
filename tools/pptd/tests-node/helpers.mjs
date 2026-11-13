import fs from 'node:fs';
import path from 'node:path';

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
