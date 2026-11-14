// One sparse table-grid expansion and style precedence chain for validation and export.
import { fail, isPlainObject } from './contract.mjs';
import { checkBorderSpec, checkFill, checkStyle, resolveStyle } from './style.mjs';

function checkCellStyle(style, label, context) {
  if (!isPlainObject(style)) fail(`${label} must be a mapping`);
  checkStyle(style, label, context?.theme?.colors ?? null);
  if (style.fill !== undefined) checkFill(style.fill, `${label}.fill`, context);
  if (style.border !== undefined) checkBorderSpec(style.border, `${label}.border`, context);
}

export function checkTableStyleConfig(config, label, context = null) {
  if (!isPlainObject(config)) fail(`${label} must be a table style mapping`);
  for (const key of ['cellStyle', 'firstRowStyle', 'lastRowStyle', 'firstColumnStyle', 'lastColumnStyle']) {
    if (config[key] !== undefined) checkCellStyle(config[key], `${label}.${key}`, context);
  }
  const body = config.bodyStyles ?? [];
  if (!Array.isArray(body)) fail(`${label}.bodyStyles must be an array of mappings`);
  for (const [index, style] of body.entries()) checkCellStyle(style, `${label}.bodyStyles[${index}]`, context);
  if ('rowOverColumn' in config && typeof config.rowOverColumn !== 'boolean') fail(`${label}.rowOverColumn must be boolean`);
  return config;
}

function cellStyle(table, theme, config, row, column, cell, label) {
  const body = config.bodyStyles ?? [];
  const rows = [row === 0 && config.firstRowStyle, row === table.rowHeights.length - 1 && config.lastRowStyle];
  const columns = [column === 0 && config.firstColumnStyle, column === table.columnWidths.length - 1 && config.lastColumnStyle];
  return Object.assign(
    {}, config.cellStyle,
    body.length && row > 0 && row < table.rowHeights.length - 1 ? body[(row - 1) % body.length] : undefined,
    ...(config.rowOverColumn === false ? [...rows, ...columns] : [...columns, ...rows]),
    resolveStyle(theme, 'textStyles', cell.textStyle, `${label}.textStyle`), cell,
  );
}

/** Cells retain their source holder, logical grid position, spans and effective style. */
export function tableCells(table, theme = {}, label = table.elementId, context = null) {
  const { columnWidths: widths, rowHeights: heights, rows } = table;
  for (const [key, weights] of [['columnWidths', widths], ['rowHeights', heights]]) {
    if (!Array.isArray(weights) || !weights.length || !weights.every((item) => Number.isFinite(item) && item >= 0 && item <= 1)) {
      fail(`${label}.${key} must be ratios in [0, 1]`);
    }
    if (Math.abs(weights.reduce((sum, item) => sum + item, 0) - 1) > 1e-6) fail(`${label}.${key} must sum to 1`);
  }
  if (!Array.isArray(rows) || rows.length !== heights.length) fail(`${label}.rows must have one array per rowHeights entry`);
  const config = checkTableStyleConfig(resolveStyle(theme, 'tableStyles', table.style, `${label}.style`), `${label}.style`, context);
  const occupied = new Set();
  const cells = [];
  for (const [row, entries] of rows.entries()) {
    if (!Array.isArray(entries)) fail(`${label}.rows[${row}] must be an array`);
    let column = 0;
    for (const [index, cell] of entries.entries()) {
      const field = `${label}.rows[${row}][${index}]`;
      if (!isPlainObject(cell)) fail(`${field} must be a cell mapping`);
      if ('text' in cell && typeof cell.text !== 'string') fail(`${field}.text must be a string`);
      checkCellStyle(cell, field, context);
      while (occupied.has(`${row}:${column}`)) column++;
      const rowSpan = cell.rowSpan ?? 1, colSpan = cell.colSpan ?? 1;
      for (const [name, span] of [['rowSpan', rowSpan], ['colSpan', colSpan]]) {
        if (!Number.isInteger(span) || span <= 0) fail(`${field}.${name} must be a positive integer`);
      }
      if (row + rowSpan > heights.length || column + colSpan > widths.length) fail(`${field} merged cell extends beyond the table grid`);
      for (let r = row; r < row + rowSpan; r++) {
        for (let c = column; c < column + colSpan; c++) {
          if (occupied.has(`${r}:${c}`)) fail(`${field} merged cells overlap`);
          occupied.add(`${r}:${c}`);
        }
      }
      cells.push({ row, column, rowSpan, colSpan, cell, label: field, style: cellStyle(table, theme, config, row, column, cell, field) });
      column += colSpan;
    }
    if (widths.some((_, column) => !occupied.has(`${row}:${column}`))) {
      fail(`${label}.rows[${row}] does not fill the table grid; skip only occupied merged positions`);
    }
  }
  return cells;
}
