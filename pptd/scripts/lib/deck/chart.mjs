// One chart contract: native series validation and advanced-chart data shaping.
import { ADVANCED_CHART_TYPES, fail, isPlainObject } from './contract.mjs';

export { ADVANCED_CHART_TYPES };

export function isAdvancedChart(element) {
  return element.elementType === 'chart' && Array.isArray(element.series) &&
    element.series.some((series) => ADVANCED_CHART_TYPES.has(series?.type));
}

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

function seriesColumns(series, cols, label) {
  if (!isPlainObject(series.encode)) fail(`${label}.encode must be a mapping`);
  const optional = { candlestick: ['open'], waterfall: ['isTotal'] }[series.type] ?? [];
  return new Map([...CHART_CHANNELS[series.type], ...optional.filter((channel) => channel in series.encode)].map((channel) => {
    const name = series.encode[channel];
    if (channel === 'parent' && name === undefined) return [channel, -1];
    const index = cols.indexOf(name);
    if (index < 0) fail(`${label}.encode.${channel} references an unknown column: ${JSON.stringify(name)}`);
    return [channel, index];
  }));
}

function advancedRows(chart, data) {
  if (chart.series?.length !== 1 || !ADVANCED_CHART_TYPES.has(chart.series[0]?.type)) {
    fail('heatmap, treemap, sunburst and sankey require exactly one series');
  }
  const series = chart.series[0];
  const columns = seriesColumns(series, data.cols, 'series');
  return {
    series,
    rows: data.rows.map((row, rowIndex) => Object.fromEntries([...columns].map(([channel, index]) => {
      const value = index < 0 ? null : row[index];
      const label = `data.rows[${rowIndex}].${channel}`;
      if (channel === 'value' || channel === 'flow') {
        const number = numericCell(value, label);
        if (series.type !== 'heatmap' && number !== null && number < 0) fail(`${label} must not be negative`);
        return [channel, number];
      }
      if (channel === 'parent' && (value === null || value === '')) return [channel, null];
      if (!['number', 'string'].includes(typeof value) || !String(value).trim() || (typeof value === 'number' && !Number.isFinite(value))) {
        fail(`${label} must be a non-empty category`);
      }
      return [channel, String(value)];
    }))),
  };
}

function heatmapDomain(rows, scale = {}) {
  scale ??= {};
  if (!['linear', 'diverging'].includes(scale.type ?? 'linear')) {
    throw new Error('heatmap colorScale.type must be linear or diverging');
  }
  if (scale.domain !== undefined) {
    if (!Array.isArray(scale.domain) || scale.domain.length !== 2 ||
        !scale.domain.every(Number.isFinite) || scale.domain[0] >= scale.domain[1]) {
      throw new Error('heatmap colorScale.domain must be two increasing finite numbers');
    }
    return scale.domain;
  }
  let min = Infinity;
  let max = -Infinity;
  for (const { value } of rows) {
    if (value === null) continue;
    min = Math.min(min, value);
    max = Math.max(max, value);
  }
  if (!Number.isFinite(min)) return scale.type === 'diverging' ? [-1, 1] : [0, 1];
  if (scale.type === 'diverging') {
    const bound = Math.max(Math.abs(min), Math.abs(max)) || 1;
    return [-bound, bound];
  }
  return min === max ? [min, min + (Math.abs(min) * 0.01 || 1)] : [min, max];
}

function validateHeatmapSeries(series, rows) {
  const domain = heatmapDomain(rows, series.colorScale);
  const diverging = series.colorScale?.type === 'diverging';
  if (series.colorScheme !== undefined) {
    if (!Array.isArray(series.colorScheme) || (diverging ? series.colorScheme.length !== 3 : series.colorScheme.length < 2)) {
      throw new Error('heatmap colorScheme needs three diverging colors or at least two linear colors');
    }
  }
  const bar = series.colorbar ?? true;
  if (bar !== false && typeof bar === 'object' && bar !== null && bar.position !== undefined) {
    if (!['top', 'bottom', 'left', 'right'].includes(bar.position)) {
      throw new Error(`invalid colorbar position: ${bar.position}`);
    }
  }
  const occupied = new Set();
  for (const { x, y } of rows) {
    const key = JSON.stringify([x, y]);
    if (occupied.has(key)) throw new Error(`duplicate heatmap cell: ${key}`);
    occupied.add(key);
  }
  return domain;
}

function topologicalOrder(names, links, kind) {
  const degree = new Map(names.map((name) => [name, 0]));
  const outgoing = new Map(names.map((name) => [name, []]));
  for (const { source, target } of links) {
    outgoing.get(source).push(target);
    degree.set(target, degree.get(target) + 1);
  }
  const queue = names.filter((name) => degree.get(name) === 0);
  for (let index = 0; index < queue.length; index++) {
    for (const target of outgoing.get(queue[index])) {
      degree.set(target, degree.get(target) - 1);
      if (degree.get(target) === 0) queue.push(target);
    }
  }
  if (queue.length !== names.length) throw new Error(`${kind} contains a cycle`);
  return queue;
}

function hierarchyData(rows) {
  const nodes = new Map();
  const declared = new Set();
  const getNode = (name) => {
    if (!nodes.has(name)) nodes.set(name, { name, value: null, children: [] });
    return nodes.get(name);
  };
  const links = [];
  for (const { category, parent, value } of rows) {
    if (declared.has(category)) throw new Error(`duplicate hierarchy node: ${category}`);
    declared.add(category);
    const node = getNode(category);
    node.value = value;
    node.parent = parent;
    if (parent !== null) {
      getNode(parent).children.push(node);
      links.push({ source: parent, target: category });
    }
  }
  const order = topologicalOrder([...nodes.keys()], links, 'hierarchy');
  // Aggregate before pruning levels, so hidden descendants still contribute to area.
  for (const name of order.reverse()) {
    const node = nodes.get(name);
    if (node.value === null) {
      node.value = node.children.reduce((sum, child) => sum + child.value, 0);
    }
    if (!Number.isFinite(node.value)) throw new Error(`hierarchy total overflows: ${name}`);
  }
  return [...nodes.values()].filter((node) => node.parent == null);
}

function sankeyData(rows) {
  const names = new Set();
  const links = rows.map(({ source, target, flow }) => {
    names.add(source);
    names.add(target);
    return { source, target, value: flow ?? 0 };
  });
  const nodeNames = topologicalOrder([...names], links, 'sankey');
  const totals = new Map(nodeNames.map((name) => [name, { incoming: 0, outgoing: 0 }]));
  for (const link of links) {
    totals.get(link.source).outgoing += link.value;
    totals.get(link.target).incoming += link.value;
  }
  for (const [name, total] of totals) {
    if (!Number.isFinite(total.incoming) || !Number.isFinite(total.outgoing)) {
      throw new Error(`sankey total overflows: ${name}`);
    }
  }
  return { nodeNames, links };
}

/** Single canonical validation + data-shaping entry for advanced charts. */
export function prepareAdvancedChartData(chart, data = checkChartData(chart, 'chart')) {
  const { series, rows } = advancedRows(chart, data);
  if (series.type === 'heatmap') {
    return { series, rows, domain: validateHeatmapSeries(series, rows) };
  }
  if (series.type === 'sankey') {
    if (!['left', 'right', 'justify'].includes(series.nodeAlign ?? 'justify')) {
      throw new Error('sankey nodeAlign must be left, right or justify');
    }
    if (Array.isArray(series.fill) && !series.fill.length) {
      throw new Error('sankey fill must not be empty');
    }
    return { series, rows, ...sankeyData(rows) };
  }
  const limit = series.levels ?? Infinity;
  if (limit !== Infinity && (!Number.isInteger(limit) || limit <= 0)) {
    throw new Error('hierarchy levels must be a positive integer');
  }
  const fill = series.fill;
  if (Array.isArray(fill) && (!fill.length || fill.some((item) => Array.isArray(item) && !item.length))) {
    throw new Error('hierarchy fill arrays must not be empty');
  }
  if (series.type !== 'treemap' && Array.isArray(fill) && fill.some(Array.isArray)) {
    throw new Error('sunburst fill must be a color, gradient or flat array');
  }
  return { series, rows, roots: hierarchyData(rows) };
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
      if (value !== null && typeof value !== 'string' && typeof value !== 'number' && typeof value !== 'boolean') {
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
  if (!['number', 'string'].includes(typeof value) || (typeof value === 'string' && !value.trim()) || !Number.isFinite(Number(value))) {
    fail(`${label} must be a finite number, numeric string or null`);
  }
  return Number(value);
}

function inferColumnType(rows, columnIndex) {
  for (const row of rows) {
    const value = row[columnIndex];
    if (value === null) continue;
    if (typeof value === 'number') return 'value';
    if (typeof value === 'string') {
      return value.trim() && Number.isFinite(Number(value)) ? 'value' : 'category';
    }
  }
  return 'category';
}

/** Reject chart inputs the native writer would otherwise omit or silently replace. */
export function checkChart(chart, label) {
  const warnings = [];
  const { cols, rows } = checkChartData(chart, label);
  const seriesList = chart.series;
  if (!Array.isArray(seriesList) || !seriesList.length) fail(`${label}.series must be a non-empty array`);
  const types = seriesList.map((series) => {
    const kind = isPlainObject(series) ? series.type : undefined;
    if (typeof kind !== 'string' || !Object.hasOwn(CHART_CHANNELS, kind)) fail(`${label}.series type is unsupported: ${JSON.stringify(kind)}`);
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
  if (defaults.scatter?.marker === false) {
    fail(`${label}.seriesDefaults.scatter.marker scatter markers cannot be disabled`);
  }
  for (const [key, upperClosed] of [['barWidth', true], ['barGap', false], ['categoryGap', false]]) {
    if (!(key in chart)) continue;
    const value = chart[key];
    const minimum = key === 'barWidth' ? value > 0 : value >= 0;
    const maximum = upperClosed ? value <= 1 : value < 1;
    if (!Number.isFinite(value) || !minimum || !maximum) fail(`${label}.${key} is outside the documented ratio range`);
  }
  const stacks = new Map();
  let radarCategory = null;
  for (const [index, series] of seriesList.entries()) {
    const field = `${label}.series[${index}]`;
    const kind = types[index];
    const encode = series.encode;
    const filter = series.dataFilter;
    if (filter !== undefined && filter !== null && (
      !isPlainObject(filter) || !cols.includes(filter.col) || (typeof filter.value !== 'string' && typeof filter.value !== 'number'))) {
      fail(`${field}.dataFilter must reference a column and a string or numeric value`);
    }
    if (ADVANCED_CHART_TYPES.has(kind)) {
      try { prepareAdvancedChartData(chart, { cols, rows }); }
      catch (error) { fail(`${label}: ${error.message}`); }
      continue;
    }
    const columns = seriesColumns(series, cols, field);
    const numeric = new Set([...CHART_CHANNELS[kind]].filter((channel) => !['category', 'x'].includes(channel)));
    if (CARTESIAN.has(kind) || kind === 'waterfall') {
      const xAxis = checkAxis(chart, 'xAxis', series, field);
      const yAxis = checkAxis(chart, 'yAxis', series, field);
      const xType = xAxis.type ?? inferColumnType(rows, cols.indexOf(encode.x));
      const yType = yAxis.type ?? (kind === 'candlestick' ? 'value' : inferColumnType(rows, columns.get('y')));
      if (['scatter', 'bubble'].includes(kind) || xType === 'value' || yType === 'category') numeric.add('x');
      if (yType === 'category' && ['bar', 'line', 'area', 'waterfall'].includes(kind)) numeric.delete('y');
    }
    if ('open' in encode && kind === 'candlestick') numeric.add('open');
    for (const channel of numeric) {
      const column = columns.get(channel);
      for (const [rowIndex, row] of rows.entries()) {
        const value = numericCell(row[column], `${field}.data.rows[${rowIndex}].${channel}`);
        if (kind === 'pie' && value !== null && value < 0) {
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

