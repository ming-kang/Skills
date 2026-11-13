// The PPTD v2 element contract: shared types, every element type, tables, charts and
// animations. This is the only schema implementation; `references/pptd.md` documents it.

import { checkJsonValue, checkRelativePath, fail, isFiniteNumber, isPlainObject, checkBounds, requireString } from './contract.mjs';

export const ELEMENT_TYPES = new Set(['text', 'shape', 'line', 'image', 'icon', 'table', 'chart']);
export const IMAGE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.svg']);
export const ANIMATION_EFFECTS = new Set([
  'appear', 'fade-in', 'fly-in', 'zoom-in', 'wipe-in', 'float-in', 'peek-in', 'rise-in',
  'pulse', 'grow-shrink', 'spin', 'teeter', 'fill-color', 'transparency', 'color-pulse',
  'disappear', 'fade-out', 'fly-out', 'zoom-out', 'wipe-out', 'float-out', 'motion-path',
]);
const ALIGN_HORIZONTAL = new Set(['left', 'center', 'right', 'justify', 'distributed']);
const ALIGN_VERTICAL = new Set(['top', 'middle', 'bottom']);
const FILL_TYPES = new Set(['none', 'solid', 'gradient', 'image']);
const FIT_MODES = new Set(['fill', 'contain', 'cover']);
const TRIGGERS = new Set(['onClick', 'withPrevious', 'afterPrevious']);
const DIRECTIONS = new Set(['up', 'down', 'left', 'right']);
const EASINGS = new Set(['linear', 'ease-in', 'ease-out', 'ease-in-out']);
const CHART_CHANNELS = {
  bar: ['x', 'y'], line: ['x', 'y'], area: ['x', 'y'],
  scatter: ['x', 'y'], bubble: ['x', 'y', 'size'],
  candlestick: ['x', 'high', 'low', 'close'],
  pie: ['category', 'value'], radar: ['category', 'y'],
  waterfall: ['x', 'y'], heatmap: ['x', 'y', 'value'],
  treemap: ['category', 'value', 'parent'], sunburst: ['category', 'value', 'parent'],
  sankey: ['source', 'target', 'flow'],
};
const SINGLE_SERIES = new Set(['pie', 'waterfall', 'heatmap', 'treemap', 'sunburst', 'sankey']);
const CARTESIAN = new Set(['bar', 'line', 'area', 'scatter', 'bubble', 'candlestick']);
const CHART_DEFAULT_TYPES = new Set(['bar', 'line', 'area', 'scatter', 'bubble', 'candlestick', 'radar']);
const ADVANCED_CHART_TYPES = new Set(['heatmap', 'treemap', 'sunburst', 'sankey']);

function hexColor(value, label) {
  if (typeof value !== 'string' || !/^#?[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?$/.test(value)) {
    fail(`${label} must be a six/eight-digit HEX color`);
  }
}

// Color is HEX6, HEX8 or a `$token` theme reference; the token itself resolves later.
function checkColor(value, label) {
  if (typeof value === 'string') {
    if (value.startsWith('$')) {
      if (value.length < 2) fail(`${label} theme color reference must name a token`);
      return;
    }
    return hexColor(value, label);
  }
  if (isPlainObject(value)) {
    if (value.type !== 'gradient') fail(`${label}.type must be gradient for a gradient mapping`);
    if (!['linear', 'radial'].includes(value.gradientType)) fail(`${label}.gradientType must be linear or radial`);
    const stops = value.stops;
    if (!Array.isArray(stops) || stops.length < 2) fail(`${label}: a gradient requires at least two color stops`);
    for (const [index, stop] of stops.entries()) {
      if (!isPlainObject(stop) || !isFiniteNumber(stop.position) || stop.position < 0 || stop.position > 1) {
        fail(`${label}.stops[${index}] must have a position in [0, 1]`);
      }
      checkColor(stop.color, `${label}.stops[${index}].color`);
    }
    if (value.gradientType === 'linear' && value.angle !== undefined && (!isFiniteNumber(value.angle) || value.angle < 0 || value.angle >= 360)) {
      fail(`${label}.angle must be in [0, 360)`);
    }
    return;
  }
  fail(`${label} must be a HEX color, a $theme token or a gradient mapping`);
}

// Keys whose mapping value is a style object (possibly nested, e.g. a cell style).
const STYLE_KEYS = new Set([
  'content', 'background', 'fill', 'border', 'shadow', 'cropShape', 'dataLabels', 'label', 'axisLabel',
  'nameTextStyle', 'textStyle', 'style', 'cellStyle', 'firstRowStyle', 'lastRowStyle', 'firstColumnStyle',
  'lastColumnStyle', 'title', 'axisLine', 'gridLine', 'colorbar', 'seriesDefaults', 'tick', 'marker',
]);
/** Walk every mapping that can hold style properties, wherever it appears. */
function walkStyles(value, visit, inStyle = false) {
  if (Array.isArray(value)) {
    for (const item of value) walkStyles(item, visit, inStyle);
    return;
  }
  if (!isPlainObject(value)) return;
  if (inStyle) visit(value);
  for (const [key, item] of Object.entries(value)) {
    if (key === 'data') continue; // chart data is validated by the chart rules, not as styles
    if (STYLE_KEYS.has(key)) walkStyles(item, visit, true);
    else walkStyles(item, visit, inStyle);
  }
}

export function checkStyles(value, label) {
  walkStyles(value, (style) => {
    const field = label;
    for (const key of ['fontSize', 'lineHeight', 'lineHeightPx']) {
      if (key in style && (!isFiniteNumber(style[key]) || style[key] <= 0)) fail(`${field}.${key} must be positive and finite`);
    }
    if ('opacity' in style && (!isFiniteNumber(style.opacity) || style.opacity < 0 || style.opacity > 1)) {
      fail(`${field}.opacity must be in [0, 1]`);
    }
    if ('fontFamily' in style) {
      const family = style.fontFamily;
      const names = isPlainObject(family) && [...Object.keys(family)].every((key) => key === 'latin' || key === 'ea')
        ? Object.values(family)
        : [family];
      if (!names.length || !names.every((name) => typeof name === 'string' && name.trim())) {
        fail(`${field}.fontFamily must be a font name or a {latin, ea} font mapping`);
      }
    }
    if ('align' in style) {
      const align = style.align;
      if (!Array.isArray(align) || align.length !== 2 || !ALIGN_HORIZONTAL.has(align[0]) || !ALIGN_VERTICAL.has(align[1])) {
        fail(`${field}.align must contain horizontal and vertical alignment`);
      }
    }
    const crop = style.crop;
    if (crop !== undefined) {
      if (!isPlainObject(crop) || !Object.keys(crop).every((key) => ['left', 'right', 'top', 'bottom'].includes(key))) {
        fail(`${field}.crop must be an image crop mapping`);
      }
      if (!Object.values(crop).every(isFiniteNumber)) fail(`${field}.crop fractions must be finite numbers`);
      const total = (a, b) => (crop[a] ?? 0) + (crop[b] ?? 0);
      if (total('left', 'right') >= 1 || total('top', 'bottom') >= 1) {
        fail(`${field}.crop left + right and top + bottom must each be less than 1`);
      }
    }
    const fit = style.fit;
    if (fit !== undefined && (!isPlainObject(fit) || !FIT_MODES.has(fit.mode))) fail(`${field}.fit must have mode fill, contain or cover`);
    if (style.type === 'gradient') checkColor(style, field);
    if ('color' in style) checkColor(style.color, `${field}.color`);
  });
}

function checkFill(value, label) {
  if (typeof value === 'string') return checkColor(value, label);
  if (!isPlainObject(value)) fail(`${label} must be a color or a fill mapping`);
  if (!FILL_TYPES.has(value.type)) fail(`${label}.type must be none, solid, gradient or image`);
  if (value.type === 'gradient') checkColor(value, label);
  if (value.type === 'image') requireString(value.src, `${label}.src`);
  return value;
}

function checkBorder(value, label) {
  if (value === undefined || value === null) return;
  if (!isPlainObject(value)) fail(`${label} must be a border mapping`);
  if (value.width !== undefined && (!isFiniteNumber(value.width) || value.width < 0)) fail(`${label}.width must be non-negative and finite`);
  if (value.style !== undefined && !['solid', 'dash', 'dot'].includes(value.style)) fail(`${label}.style must be solid, dash or dot`);
}

function checkShadow(value, label) {
  if (value === undefined || value === null) return;
  if (!isPlainObject(value)) fail(`${label} must be a shadow mapping`);
  if (value.blur !== undefined && (!isFiniteNumber(value.blur) || value.blur < 0)) fail(`${label}.blur must be non-negative and finite`);
}

/** Shape and image-crop geometry: 177 preset names, or a custom SVG path with its viewBox. */
export function checkShape(shape, label, names) {
  if (!isPlainObject(shape)) fail(`${label} must be a shape mapping`);
  const name = shape.shapeName;
  if (name === 'custom') {
    if (typeof shape.path !== 'string' || !shape.path.trim()) fail(`${label}.path custom shapes require an SVG path`);
    const view = shape.viewBox;
    if (view !== undefined && (!Array.isArray(view) || view.length !== 2 || !view.every((item) => isFiniteNumber(item) && item > 0))) {
      fail(`${label}.viewBox must contain two positive finite dimensions`);
    }
    return;
  }
  if (typeof name !== 'string' || !names.has(name)) fail(`${label}.shapeName is an unknown shape: ${JSON.stringify(name)}`);
}

export function checkTableGrid(table, label) {
  const { columnWidths: widths, rowHeights: heights, rows } = table;
  for (const [key, weights] of [['columnWidths', widths], ['rowHeights', heights]]) {
    if (!Array.isArray(weights) || !weights.length || !weights.every((item) => isFiniteNumber(item) && item >= 0 && item <= 1)) {
      fail(`${label}.${key} must be ratios in [0, 1]`);
    }
    if (weights.reduce((sum, item) => sum + item, 0) !== 1) fail(`${label}.${key} must sum to 1`);
  }
  if (!Array.isArray(rows) || rows.length !== heights.length) fail(`${label}.rows must have one array per rowHeights entry`);
  const occupied = new Set();
  const cells = [];
  for (const [rowIndex, row] of rows.entries()) {
    if (!Array.isArray(row)) fail(`${label}.rows[${rowIndex}] must be an array`);
    let column = 0;
    for (const [cellIndex, cell] of row.entries()) {
      const field = `${label}.rows[${rowIndex}][${cellIndex}]`;
      if (!isPlainObject(cell)) fail(`${field} must be a cell mapping`);
      if ('text' in cell && typeof cell.text !== 'string') fail(`${field}.text must be a string`);
      while (occupied.has(`${rowIndex}:${column}`)) column += 1;
      const rowSpan = cell.rowSpan ?? 1;
      const colSpan = cell.colSpan ?? 1;
      for (const [name, span] of [['rowSpan', rowSpan], ['colSpan', colSpan]]) {
        if (!Number.isInteger(span) || span <= 0) fail(`${field}.${name} must be a positive integer`);
      }
      if (rowIndex + rowSpan > heights.length || column + colSpan > widths.length) fail(`${field} merged cell extends beyond the table grid`);
      const region = [];
      for (let r = rowIndex; r < rowIndex + rowSpan; r++) {
        for (let c = column; c < column + colSpan; c++) {
          if (occupied.has(`${r}:${c}`)) fail(`${field} merged cells overlap`);
          occupied.add(`${r}:${c}`);
          region.push([r, c]);
        }
      }
      cells.push({ row: rowIndex, column, rowSpan, colSpan, cell });
      column += colSpan;
    }
    if (widths.some((_, c) => !occupied.has(`${rowIndex}:${c}`))) {
      fail(`${label}.rows[${rowIndex}] does not fill the table grid; skip only occupied merged positions`);
    }
  }
  return cells;
}

function checkTableStyle(table, theme, label) {
  const reference = table.style;
  if (reference === undefined || reference === null) return {};
  const config = typeof reference === 'string' ? theme.tableStyles?.[reference.slice(1)] : reference;
  if (typeof reference === 'string' && (reference[0] !== '$' || config === undefined)) {
    fail(`${label}.style references an unknown table style: ${JSON.stringify(reference)}`);
  }
  if (!isPlainObject(config)) fail(`${label}.style must be a table style mapping`);
  for (const key of ['cellStyle', 'firstRowStyle', 'lastRowStyle', 'firstColumnStyle', 'lastColumnStyle']) {
    if (key in config && !isPlainObject(config[key])) fail(`${label}.style.${key} must be a mapping`);
  }
  const body = config.bodyStyles ?? [];
  if (!Array.isArray(body) || !body.every(isPlainObject)) fail(`${label}.style.bodyStyles must be an array of mappings`);
  if ('rowOverColumn' in config && typeof config.rowOverColumn !== 'boolean') fail(`${label}.style.rowOverColumn must be boolean`);
  return config;
}

export function textStyleReference(theme, reference, label) {
  if (reference === undefined || reference === null) return {};
  const config = typeof reference === 'string' ? theme.textStyles?.[reference.slice(1)] : reference;
  if (typeof reference === 'string' && (reference[0] !== '$' || config === undefined)) {
    fail(`${label} references an unknown text style: ${JSON.stringify(reference)}`);
  }
  if (!isPlainObject(config)) fail(`${label} must be a text style mapping`);
  return config;
}

/** Effective style of one table cell, applying the documented precedence chain. */
export function cellStyle(table, theme, row, column, cell) {
  const config = checkTableStyle(table, theme, `${table.elementId}`);
  const style = { ...config.cellStyle };
  const body = config.bodyStyles ?? [];
  if (body.length && row > 0 && row < table.rowHeights.length - 1) Object.assign(style, body[(row - 1) % body.length]);
  const rows = [];
  if (row === 0) rows.push(config.firstRowStyle);
  if (row === table.rowHeights.length - 1) rows.push(config.lastRowStyle);
  const columns = [];
  if (column === 0) columns.push(config.firstColumnStyle);
  if (column === table.columnWidths.length - 1) columns.push(config.lastColumnStyle);
  for (const part of config.rowOverColumn === false ? [...rows, ...columns] : [...columns, ...rows]) {
    Object.assign(style, part);
  }
  Object.assign(style, textStyleReference(theme, cell.textStyle, `${table.elementId}.textStyle`));
  return Object.assign(style, cell);
}

export function tableCells(table, theme, label) {
  return checkTableGrid(table, label).map(({ row, column, rowSpan, colSpan, cell }) => ({
    row, column, rowSpan, colSpan, style: cellStyle(table, theme, row, column, cell), cell,
  }));
}

function checkChartData(chart, label) {
  const data = chart.data;
  if (!isPlainObject(data)) fail(`${label}.data must be a mapping`);
  const { cols, rows } = data;
  if (!Array.isArray(cols) || !cols.length || !cols.every((col) => typeof col === 'string' && col.trim()) || new Set(cols).size !== cols.length) {
    fail(`${label}.data.cols must contain unique, non-empty column names`);
  }
  if (!Array.isArray(rows)) fail(`${label}.data.rows must be an array`);
  for (const [index, row] of rows.entries()) {
    if (!Array.isArray(row) || row.length !== cols.length) fail(`${label}.data.rows[${index}] must contain ${cols.length} cells`);
    for (const [column, value] of row.entries()) {
      if (value !== null && typeof value !== 'string' && typeof value !== 'number') {
        fail(`${label}.data.rows[${index}][${column}] must be a scalar or null`);
      }
      if (typeof value === 'number' && !Number.isFinite(value)) fail(`${label}.data.rows[${index}][${column}] must be finite`);
    }
  }
  return { cols, rows };
}

function checkAxis(chart, key, series, label) {
  const config = chart[key];
  const index = series[`${key}Index`] ?? 0;
  if (!Number.isInteger(index) || index < 0) fail(`${label}.${key}Index must be a non-negative integer`);
  // An omitted axis is an empty configuration; only an explicit array must cover the index.
  const axes = Array.isArray(config) ? config : [config ?? {}];
  if (index >= axes.length || !axes.every(isPlainObject)) fail(`${label}.${key}Index does not reference a valid ${key}`);
  const axis = axes[index];
  if ('type' in axis && !['category', 'value'].includes(axis.type)) fail(`${label}.${key}.type must be category or value`);
  return axis;
}

function numericCell(value, label) {
  if (value === null) return null;
  if (typeof value === 'boolean' || (typeof value !== 'number' && typeof value !== 'string')) {
    fail(`${label} must be a finite number, numeric string or null`);
  }
  const number = Number(value);
  if (!Number.isFinite(number)) fail(`${label} must be a finite number, numeric string or null`);
  return number;
}

/** Reject chart inputs the native writer would otherwise omit or silently replace. */
export function checkChart(chart, label) {
  const warnings = [];
  const { cols, rows } = checkChartData(chart, label);
  const seriesList = chart.series;
  if (!Array.isArray(seriesList) || !seriesList.length) fail(`${label}.series must be a non-empty array`);
  const types = seriesList.map((series) => {
    const kind = isPlainObject(series) ? series.type : undefined;
    if (typeof kind !== 'string' || !(kind in CHART_CHANNELS)) fail(`${label}.series type is unsupported: ${JSON.stringify(kind)}`);
    return kind;
  });
  const kinds = new Set(types);
  if (kinds.size && [...kinds].some((kind) => SINGLE_SERIES.has(kind)) && seriesList.length !== 1) {
    fail(`${label}.series pie, waterfall and advanced charts require exactly one series`);
  }
  if (kinds.has('radar') && kinds.size !== 1) fail(`${label}.series radar cannot mix with other chart types`);
  if (kinds.has('candlestick') && ![...kinds].every((kind) => ['candlestick', 'bar', 'line', 'area'].includes(kind))) {
    fail(`${label}.series candlestick may mix only with bar, line and area`);
  }
  const defaults = chart.seriesDefaults ?? {};
  if (!isPlainObject(defaults)) fail(`${label}.seriesDefaults must be a mapping`);
  for (const [kind, config] of Object.entries(defaults)) {
    if (!CHART_DEFAULT_TYPES.has(kind) || !isPlainObject(config) || 'type' in config || 'encode' in config) {
      fail(`${label}.seriesDefaults.${kind} must be supported style defaults without type or encode`);
    }
  }
  for (const [key, upperClosed] of [['barWidth', true], ['barGap', false], ['categoryGap', false]]) {
    if (!(key in chart)) continue;
    const value = chart[key];
    const minimum = key === 'barWidth' ? value > 0 : value >= 0;
    const maximum = upperClosed ? value <= 1 : value < 1;
    if (!isFiniteNumber(value) || !minimum || !maximum) fail(`${label}.${key} is outside the documented ratio range`);
  }
  const stacks = new Map();
  let radarCategory = null;
  for (const [index, series] of seriesList.entries()) {
    const field = `${label}.series[${index}]`;
    const kind = types[index];
    const encode = series.encode;
    if (!isPlainObject(encode)) fail(`${field}.encode must be a mapping`);
    const optional = { candlestick: ['open'], waterfall: ['isTotal'], treemap: ['parent'], sunburst: ['parent'] }[kind] ?? [];
    for (const channel of [...CHART_CHANNELS[kind], ...optional.filter((name) => name in encode)]) {
      if (!(channel in encode) || !cols.includes(encode[channel])) {
        fail(`${field}.encode.${channel} references an unknown column: ${JSON.stringify(encode[channel])}`);
      }
    }
    const filter = series.dataFilter;
    if (filter !== undefined && filter !== null && (
      !isPlainObject(filter) || !cols.includes(filter.col) || typeof filter.value !== 'string' && typeof filter.value !== 'number' || typeof filter.value === 'boolean')) {
      fail(`${field}.dataFilter must reference a column and a string or numeric value`);
    }
    let numeric = new Set([...CHART_CHANNELS[kind]].filter((channel) => !['category', 'parent', 'source', 'target', 'x'].includes(channel)));
    if (CARTESIAN.has(kind) || kind === 'waterfall') {
      const xAxis = checkAxis(chart, 'xAxis', series, field);
      const yAxis = checkAxis(chart, 'yAxis', series, field);
      if (['scatter', 'bubble'].includes(kind) || xAxis.type === 'value' || yAxis.type === 'category') numeric.add('x');
      if (yAxis.type === 'category' && ['bar', 'line', 'area', 'waterfall'].includes(kind)) numeric.delete('y');
    }
    if (kind === 'heatmap') numeric = new Set(['value']);
    if ('open' in encode && kind === 'candlestick') numeric.add('open');
    for (const channel of numeric) {
      const column = cols.indexOf(encode[channel]);
      for (const [rowIndex, row] of rows.entries()) {
        const value = numericCell(row[column], `${field}.data.rows[${rowIndex}].${channel}`);
        if (['pie', 'treemap', 'sunburst', 'sankey'].includes(kind) && value !== null && value < 0) {
          fail(`${field}.data.rows[${rowIndex}].${channel} must not be negative`);
        }
      }
    }
    if (kind === 'waterfall' && 'isTotal' in encode) {
      const totalColumn = cols.indexOf(encode.isTotal);
      const valueColumn = cols.indexOf(encode.y);
      let running = 0;
      for (const [rowIndex, row] of rows.entries()) {
        const total = row[totalColumn];
        if (total !== null && typeof total !== 'boolean') fail(`${field}.data.rows[${rowIndex}].isTotal must be boolean or null`);
        const value = numericCell(row[valueColumn], `${field}.data.rows[${rowIndex}].y`) ?? 0;
        if (total) {
          if (rowIndex && !Object.is(value, running)) warnings.push(`${field}.data.rows[${rowIndex}]: waterfall total differs from accumulated changes`);
          running = value;
        } else {
          running += value;
        }
      }
    }
    if (kind === 'radar') {
      if (radarCategory !== null && encode.category !== radarCategory) fail(`${field}.encode.category all radar series must share one category column`);
      radarCategory = encode.category;
    }
    const stack = series.stack ?? defaults[kind]?.stack;
    if (stack !== undefined && stack !== null) {
      const allowed = kind === 'area' ? ['value', 'percent', 'stream'] : ['value', 'percent'];
      if (!['bar', 'area'].includes(kind) || !allowed.includes(stack)) fail(`${field}.stack is not supported for this series type`);
      if (stacks.has(kind) && stacks.get(kind) !== stack) fail(`${field}.stack all stacked series of one type must use the same mode`);
      stacks.set(kind, stack);
    }
    if (kind === 'scatter' && series.marker === false) fail(`${field}.marker scatter markers cannot be disabled`);
  }
  return warnings;
}

function checkAnimations(page, label) {
  const animations = page.animations ?? [];
  if (!Array.isArray(animations)) fail(`${label}.animations must be an array`);
  const ids = new Set(page.elements.map((element) => element.elementId));
  for (const [index, animation] of animations.entries()) {
    const field = `${label}.animations[${index}]`;
    if (!isPlainObject(animation)) fail(`${field} must be a mapping`);
    if (typeof animation.elementId !== 'string' || !ids.has(animation.elementId)) {
      fail(`${field}.elementId references an unknown element: ${JSON.stringify(animation.elementId)}`);
    }
    if (typeof animation.effect !== 'string' || !ANIMATION_EFFECTS.has(animation.effect)) {
      fail(`${field}.effect is unsupported: ${JSON.stringify(animation.effect)}`);
    }
    if ('trigger' in animation && !TRIGGERS.has(animation.trigger)) fail(`${field}.trigger is not a supported value`);
    if ('direction' in animation && !DIRECTIONS.has(animation.direction)) fail(`${field}.direction is not a supported value`);
    if ('easing' in animation && !EASINGS.has(animation.easing)) fail(`${field}.easing is not a supported value`);
    if ('durationMs' in animation && (!isFiniteNumber(animation.durationMs) || animation.durationMs <= 0)) fail(`${field}.durationMs must be positive`);
    if ('delayMs' in animation && (!isFiniteNumber(animation.delayMs) || animation.delayMs < 0)) fail(`${field}.delayMs must be non-negative`);
    if ('repeat' in animation && (!Number.isInteger(animation.repeat) || animation.repeat <= 0)) fail(`${field}.repeat must be a positive integer`);
    if (['fill-color', 'color-pulse'].includes(animation.effect)) hexColor(animation.color, `${field}.color`);
    if (animation.effect === 'transparency' && (!isFiniteNumber(animation.amount) || animation.amount < 0 || animation.amount > 1)) {
      fail(`${field}.amount requires a target opacity in [0, 1]`);
    }
    if (animation.effect === 'motion-path') {
      const path = animation.path;
      if (typeof path !== 'string' || !/^\s*M\s*0[\s,]+0(?:\s|[LQCZ])/.test(path)) fail(`${field}.path motion paths must start with M 0 0`);
    }
    if (['float-in', 'float-out'].includes(animation.effect) && (animation.direction ?? 'up') !== 'up' && animation.direction !== 'down') {
      fail(`${field}.direction float animations support only up and down`);
    }
  }
}

function checkElement(element, index, pagePath, context) {
  const label = `${pagePath}: elements[${index}]`;
  if (!isPlainObject(element)) fail(`${label} must be a mapping`);
  const elementId = element.elementId;
  if (typeof elementId !== 'string' || !elementId.trim()) fail(`${label}.elementId must be a non-empty string`);
  if (context.seenIds.has(elementId)) fail(`${pagePath}: duplicate elementId: ${elementId}`);
  context.seenIds.add(elementId);
  const kind = element.elementType;
  if (typeof kind !== 'string' || !ELEMENT_TYPES.has(kind)) fail(`${label}.elementType is invalid: ${JSON.stringify(kind)}`);
  const field = `${label} (${elementId})`;
  const bounds = checkBounds(element.bounds, `${field}.bounds`);
  if (bounds[0] < 0 || bounds[1] < 0 || bounds[0] + bounds[2] > context.size[0] || bounds[1] + bounds[3] > context.size[1]) {
    context.warnings.push(`${field} extends beyond the slide canvas`);
  }
  checkStyles(element, field);
  if (element.rotation !== undefined && !isFiniteNumber(element.rotation)) fail(`${field}.rotation must be finite`);
  if (element.opacity !== undefined && (!isFiniteNumber(element.opacity) || element.opacity < 0 || element.opacity > 1)) {
    fail(`${field}.opacity must be in [0, 1]`);
  }
  checkBorder(element.border, `${field}.border`);
  checkShadow(element.shadow, `${field}.shadow`);
  if (element.fill !== undefined) checkFill(element.fill, `${field}.fill`);

  if (kind === 'text') {
    const content = element.content;
    if (!isPlainObject(content) || typeof content.text !== 'string') fail(`${field}.content.text must be a string for text elements`);
    textStyleReference(context.theme, content.style, `${field}.content.style`);
  }
  if (kind === 'table') {
    tableCells(element, context.theme, field);
  }
  if (kind === 'shape' || kind === 'image' && 'cropShape' in element) {
    checkShape(kind === 'shape' ? element : element.cropShape, field, context.shapeNames);
    if (kind === 'shape' && ('content' in element || 'text' in element)) fail(`${field} shapes do not embed text; add a separate text element`);
  }
  if (kind === 'icon') {
    if (typeof element.iconName !== 'string' || !context.iconNames.has(element.iconName)) {
      fail(`${field}.iconName is an unknown bundled Font Awesome Free icon: ${JSON.stringify(element.iconName)}`);
    }
  }
  if (kind === 'image') {
    const src = element.src;
    if (typeof src !== 'string' || !src.trim()) fail(`${field}.src image source must be a non-empty string`);
    if (/^https?:\/\//i.test(src) || src.startsWith('data:')) {
      // Remote and inline sources are resolved by the exporter; validation checks bytes later.
    } else {
      const relative = checkRelativePath(src.replace(/^file:\/+/, ''), `${field}.src`);
      // Local media is keyed by path so one file referenced twice is checked once.
      context.media.set(relative, { path: relative, label: field });
    }
  }
  if (kind === 'chart') context.warnings.push(...checkChart(element, field));
}

/** Validate one page and collect the local media it references. */
export function checkPage(page, pagePath, context) {
  if (!isPlainObject(page) || !Array.isArray(page.elements)) fail(`page elements must be an array: ${pagePath}`);
  if ('notes' in page && typeof page.notes !== 'string') fail(`${pagePath}.notes must be a string`);
  checkJsonValue(page, pagePath);
  checkStyles(page, pagePath);
  const pageContext = { ...context, seenIds: new Set() };
  for (const [index, element] of page.elements.entries()) checkElement(element, index, pagePath, pageContext);
  checkAnimations(page, pagePath);
}

export { ADVANCED_CHART_TYPES };
