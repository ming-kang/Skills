// Font Awesome Free icons resolve offline to native vector paths; unknown names fail
// instead of becoming an ellipsis.
import fs from 'node:fs';

let catalog;
function iconCatalog() {
  catalog ??= JSON.parse(fs.readFileSync(new URL('../../../assets/icons/fontawesome.json', import.meta.url), 'utf8'));
  return catalog;
}

export function resolveIcon(name) {
  if (typeof name !== 'string' || !/^(fas|far|fab):[a-z0-9][a-z0-9-]*$/.test(name)) {
    throw new Error('iconName must be a Font Awesome Free name such as fas:house, far:heart or fab:github');
  }
  const { icons, aliases } = iconCatalog();
  const definition = icons[aliases[name] ?? name];
  if (!definition) throw new Error(`unknown bundled Font Awesome Free icon: ${name}`);
  return definition;
}

export function prepareIcons(project) {
  let count = 0;
  for (const page of project.pages) {
    for (const element of page.elements) {
      if (element.elementType !== 'icon') continue;
      try {
        const { path, viewBox } = resolveIcon(element.iconName);
        Object.assign(element, { path, viewBox, fill: element.fill ?? { type: 'solid', color: '#000000' } });
        count += 1;
      } catch (error) {
        throw new Error(`${page.pagePath}: icon ${element.elementId}: ${error.message}`);
      }
    }
  }
  return count;
}
