// Share lazily loaded skill catalogs between validation and preparation.
import fs from 'node:fs';

const catalogs = new Map();
export function readCatalog(relative) {
  if (!catalogs.has(relative)) {
    catalogs.set(relative, JSON.parse(fs.readFileSync(new URL(`../../../assets/${relative}`, import.meta.url), 'utf8')));
  }
  return catalogs.get(relative);
}

export function iconDefinition(name) {
  const { icons, aliases } = readCatalog('icons/fontawesome.json');
  const canonical = Object.hasOwn(aliases, name) ? aliases[name] : name;
  return Object.hasOwn(icons, canonical) ? icons[canonical] : null;
}
