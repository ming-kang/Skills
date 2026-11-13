#!/usr/bin/env node
// Build pptd/assets/shapes.json from the documented OOXML shape table in references/shapes.md.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const INPUT = path.join(ROOT, 'pptd', 'references', 'shapes.md');
const OUTPUT = path.join(ROOT, 'pptd', 'assets', 'shapes.json');

export function parseShapesMarkdown(text) {
  const shapes = {};
  for (const line of text.split(/\r?\n/)) {
    if (!line.startsWith('|')) continue;
    const cols = line.split('|').slice(1, -1).map((cell) => cell.trim());
    if (cols.length < 2) continue;
    const [name, , params, defaults] = cols;
    if (!name || name === 'shapeName' || /^-+$/.test(name)) continue;
    if (!/^[A-Za-z][A-Za-z0-9]*$/.test(name)) {
      throw new Error(`unexpected shape name in shapes.md: ${name}`);
    }
    if (Object.hasOwn(shapes, name)) {
      throw new Error(`duplicate shape name in shapes.md: ${name}`);
    }
    let adjustments = 0;
    if (defaults && defaults !== '-') {
      const parsed = JSON.parse(defaults);
      if (!Array.isArray(parsed) || !parsed.every((n) => typeof n === 'number' && Number.isFinite(n))) {
        throw new Error(`invalid default adjustments for ${name}: ${defaults}`);
      }
      adjustments = parsed.length;
    } else if (params && params !== '-' && !defaults) {
      throw new Error(`missing default adjustments for ${name}: ${params}`);
    }
    shapes[name] = { adjustments };
  }
  if (Object.keys(shapes).length !== 177) {
    throw new Error(`expected 177 shapes, found ${Object.keys(shapes).length}`);
  }
  return shapes;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const shapes = parseShapesMarkdown(fs.readFileSync(INPUT, 'utf8'));
  fs.mkdirSync(path.dirname(OUTPUT), { recursive: true });
  fs.writeFileSync(OUTPUT, JSON.stringify(shapes, null, 2) + '\n', 'utf8');
  console.log(`Built ${Object.keys(shapes).length} shapes into ${path.relative(ROOT, OUTPUT)}`);
}
