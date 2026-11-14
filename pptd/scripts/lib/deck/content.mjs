// Per-deck content plan: expand table styles and parse text once, then share the
// holders, logical cell positions, DOM and formula tokens across export stages.
// The plan is separate from the plain-data deck passed to the WASM writer.
import { readRichText } from '../core/markup.mjs';
import { resolveStyle } from './style.mjs';
import { tableCells } from './table.mjs';

export function readContent(project) {
  const theme = project.theme ?? {};
  const texts = [], tables = [], formulas = [];
  const addText = (holder, style, location) => {
    const markup = readRichText(holder.text ?? '', location, { theme });
    texts.push({ holder, style, location, markup });
    for (const latex of markup.formulas) formulas.push({ latex, location });
  };
  for (const [pageIndex, page] of project.pages.entries()) {
    for (const element of page.elements) {
      const location = `${page.pagePath}: ${element.elementId}`;
      if (element.elementType === 'text') {
        const holder = element.content;
        const style = { ...resolveStyle(theme, 'textStyles', holder.style, `${location}.content.style`), ...holder };
        addText(holder, style, location);
      } else if (element.elementType === 'table') {
        const cells = tableCells(element, theme, location);
        tables.push({ table: element, cells, pageIndex, pagePath: page.pagePath });
        for (const { cell, style, label } of cells) addText(cell, style, label);
      }
    }
  }
  return { texts, tables, formulas };
}
