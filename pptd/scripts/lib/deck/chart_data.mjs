// Validate and shape the four chart types that the WASM writer cannot emit natively.
import { ADVANCED_CHART_TYPES } from './contract.mjs';

export { ADVANCED_CHART_TYPES };

const CHANNELS = {
  heatmap: ['x', 'y', 'value'],
  treemap: ['category', 'value', 'parent'],
  sunburst: ['category', 'value', 'parent'],
  sankey: ['source', 'target', 'flow'],
};

function numericValue(value, label) {
  if (value === null) return null;
  if (
    !['number', 'string'].includes(typeof value) ||
    (typeof value === 'string' && !value.trim()) ||
    !Number.isFinite(Number(value))
  ) {
    throw new Error(`${label} must be a finite number or null`);
  }
  return Number(value);
}

function readChartData(chart) {
  if (chart.series.length !== 1) {
    throw new Error('heatmap, treemap, sunburst and sankey require exactly one series');
  }
  const series = chart.series[0];
  const { cols, rows } = chart.data ?? {};
  if (
    !Array.isArray(cols) || !cols.length ||
    cols.some((name) => typeof name !== 'string' || !name.trim()) ||
    new Set(cols).size !== cols.length
  ) {
    throw new Error('data.cols must contain unique, non-empty column names');
  }
  if (!Array.isArray(rows)) throw new Error('data.rows must be an array');
  const columns = CHANNELS[series.type].map((channel) => {
    const name = series.encode?.[channel];
    if (channel === 'parent' && name === undefined) return [channel, -1];
    const index = cols.indexOf(name);
    if (index < 0) throw new Error(`encode.${channel} references an unknown column: ${name}`);
    return [channel, index];
  });
  return {
    series,
    rows: rows.map((row, rowIndex) => {
      if (!Array.isArray(row) || row.length !== cols.length) {
        throw new Error(`data.rows[${rowIndex}] must have ${cols.length} cells`);
      }
      return Object.fromEntries(columns.map(([channel, index]) => {
        const value = index < 0 ? null : row[index];
        const label = `data.rows[${rowIndex}].${channel}`;
        if (channel === 'value' || channel === 'flow') {
          const number = numericValue(value, label);
          if (series.type !== 'heatmap' && number !== null && number < 0) {
            throw new Error(`${label} must not be negative`);
          }
          return [channel, number];
        }
        if (channel === 'parent' && (value === null || value === '')) return [channel, null];
        if (
          !['number', 'string'].includes(typeof value) ||
          !String(value).trim() ||
          (typeof value === 'number' && !Number.isFinite(value))
        ) {
          throw new Error(`${label} must be a non-empty category`);
        }
        return [channel, String(value)];
      }));
    }),
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
export function prepareAdvancedChartData(chart) {
  const { series, rows } = readChartData(chart);
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
