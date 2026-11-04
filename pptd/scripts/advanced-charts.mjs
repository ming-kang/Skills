import { ADVANCED_CHART_TYPES, readChartData, hierarchyData, sankeyData } from './chart-data.mjs';
import { chartStyle, lineStyle } from './chart-style.mjs';

// Matches the previous editor: same-colored hierarchy nodes need a separator to stay readable.
const DEFAULT_HIERARCHY_BORDER = { width: 1, color: '#FFFFFF' };
// Chromium resolves `dominant-baseline: central` to (ascent - descent) / 2 of the primary font;
// for Arial that is 0.347em. Office ignores the attribute, so the shift is baked into `y`.
const CENTRAL_BASELINE_EM = 0.35;
// Frame layers repeat the chart's animations; these effects would recolor a frame instead.
const UNMIRRORED_EFFECTS = new Set(['fill-color', 'color-pulse']);

function isAdvancedChart(element) {
  return element.elementType === 'chart' && Array.isArray(element.series) &&
    element.series.some((series) => ADVANCED_CHART_TYPES.has(series?.type));
}

function titleOption(chart, style) {
  if (chart.title === undefined) return undefined;
  const config = typeof chart.title === 'string' ? { text: chart.title } : chart.title;
  if (!config || typeof config.text !== 'string') throw new Error('chart title must contain text');
  return {
    text: config.text,
    left: 'center', top: 4,
    textStyle: { ...style.text(config, 16), fontWeight: 'normal' },
  };
}

function axisOption(config, categories, style) {
  const axis = (Array.isArray(config) ? config[0] : config) ?? {};
  const label = typeof axis.label === 'object' ? axis.label : {};
  const title = typeof axis.title === 'string' ? { text: axis.title } : axis.title;
  const line = (value) => ({
    show: value !== false,
    lineStyle: {
      color: style.color(value?.color ?? '#D1D5DB'),
      width: value?.width ?? 1,
      type: lineStyle(value?.style),
    },
  });
  const arrow = axis.axisLine?.arrow;
  return {
    type: 'category', data: categories,
    show: axis.show !== false, inverse: axis.reverse === true,
    name: title?.text,
    nameLocation: 'middle', nameGap: 30,
    nameTextStyle: style.text(title, 12),
    axisLabel: { ...style.text(label, 11), show: axis.label !== false },
    axisLine: {
      ...line(axis.axisLine),
      symbol: [arrow === 'start' || arrow === 'both' ? 'arrow' : 'none',
        arrow === true || arrow === 'end' || arrow === 'both' ? 'arrow' : 'none'],
    },
    axisTick: { show: false },
    splitLine: line(axis.gridLine),
    splitArea: { show: false },
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

function heatmapOption(chart, series, rows, style, top) {
  const xs = [...new Set(rows.map((row) => row.x))];
  const ys = [...new Set(rows.map((row) => row.y))];
  const xIndex = new Map(xs.map((value, index) => [value, index]));
  const yIndex = new Map(ys.map((value, index) => [value, index]));
  const domain = heatmapDomain(rows, series.colorScale);
  const diverging = series.colorScale?.type === 'diverging';
  const colors = series.colorScheme ?? (diverging
    ? [style.palette[1] ?? style.palette[0], '#FFFFFF', style.palette[0]]
    : ['#EFF6FF', style.palette[0]]);
  if (!Array.isArray(colors) || (diverging ? colors.length !== 3 : colors.length < 2)) {
    throw new Error('heatmap colorScheme needs three diverging colors or at least two linear colors');
  }
  const scale = colors.map(style.color);
  const occupied = new Set();
  const data = [];
  for (const { x, y, value } of rows) {
    const key = JSON.stringify([x, y]);
    if (occupied.has(key)) throw new Error(`duplicate heatmap cell: ${key}`);
    occupied.add(key);
    // Missing values are transparent, not zero-valued cells.
    if (value === null) continue;
    data.push({
      value: [xIndex.get(x), yIndex.get(y), value],
      label: { color: style.labelColor(series, style.scaleColor(scale, domain, value)) },
    });
  }
  const [min, max] = domain;
  const bar = series.colorbar ?? true;
  const show = bar !== false && bar.show !== false;
  const position = bar.position ?? 'right';
  const placements = {
    top: { top, left: 'center', orient: 'horizontal' },
    bottom: { bottom: 4, left: 'center', orient: 'horizontal' },
    left: { left: 4, top: 'middle', orient: 'vertical' },
    right: { right: 4, top: 'middle', orient: 'vertical' },
  };
  if (!Object.hasOwn(placements, position)) throw new Error(`invalid colorbar position: ${position}`);
  const grid = { top, left: chart.yAxis?.title ? 60 : 36, right: 16, bottom: 36, containLabel: true };
  if (show) grid[position] += ['left', 'right'].includes(position) ? 64 : 40;
  return {
    grid,
    xAxis: axisOption(chart.xAxis, xs, style),
    yAxis: axisOption(chart.yAxis, ys, style),
    visualMap: {
      type: 'continuous', min, max, show, calculable: false,
      text: [String(max), String(min)], dimension: 2,
      inRange: { color: scale },
      textStyle: style.text(typeof bar === 'object' ? bar : {}, 11),
      itemHeight: Math.min(120, chart.bounds[['left', 'right'].includes(position) ? 3 : 2] * 0.4),
      ...placements[position],
    },
    series: [{
      type: 'heatmap', data, progressive: 0,
      label: style.label(series, 'value', (params) => params.value[2]),
    }],
  };
}

function hierarchyOption(chart, series, rows, style, top) {
  const limit = series.levels ?? Infinity;
  if (limit !== Infinity && (!Number.isInteger(limit) || limit <= 0)) {
    throw new Error('hierarchy levels must be a positive integer');
  }
  const treemap = series.type === 'treemap';
  const fill = series.fill;
  if (Array.isArray(fill) && (!fill.length || fill.some((item) => Array.isArray(item) && !item.length))) {
    throw new Error('hierarchy fill arrays must not be empty');
  }
  if (!treemap && Array.isArray(fill) && fill.some(Array.isArray)) {
    throw new Error('sunburst fill must be a color, gradient or flat array');
  }
  const border = style.border(series.border === undefined ? DEFAULT_HIERARCHY_BORDER : series.border);
  // ECharts draws treemap borders as filled strips and ignores borderType. Dashed/dotted
  // treemap borders are drawn afterwards as one deduplicated grid (see treemapDashGrid).
  const dash = treemap && border.borderWidth > 0 && border.borderType !== 'solid'
    ? { width: border.borderWidth, color: border.borderColor, type: border.borderType }
    : undefined;
  const nodeBorder = dash ? { borderWidth: 0, borderColor: 'transparent' } : border;
  function nodeOption(node, rootIndex, depth) {
    let paint = Array.isArray(fill) ? fill[rootIndex % fill.length] : fill;
    let shadeDepth = treemap ? depth : 0;
    if (Array.isArray(paint)) {
      const explicitLevel = Math.min(depth, paint.length - 1);
      shadeDepth = depth - explicitLevel;
      paint = paint[explicitLevel];
    }
    const color = style.paint(paint, style.palette[rootIndex % style.palette.length], shadeDepth);
    return {
      name: node.name, value: node.value,
      itemStyle: { color, ...nodeBorder },
      label: { color: style.labelColor(series, color) },
      ...(depth + 1 < limit && node.children.length
        ? { children: node.children.map((child) => nodeOption(child, rootIndex, depth + 1)) }
        : {}),
    };
  }
  const data = hierarchyData(rows).map((node, index) => nodeOption(node, index, 0));
  const label = style.label(series, 'category');
  const option = {
    series: [{
      type: series.type, data, label,
      ...(treemap ? {
        top, left: 8, right: 8, bottom: 8,
        roam: false, nodeClick: false, sort: false,
        breadcrumb: { show: false }, upperLabel: { show: false },
        itemStyle: { borderWidth: 0, borderColor: 'transparent', gapWidth: 0 },
        visibleMin: 0, childrenVisibleMin: 0,
      } : {
        center: [chart.bounds[2] / 2, (chart.bounds[3] + top) / 2],
        radius: [0, Math.max(1, Math.min(chart.bounds[2] - 16, chart.bounds[3] - top - 16) / 2)],
        sort: null, nodeClick: false, stillShowZeroSum: false,
      }),
    }],
  };
  return { option, dash };
}

function sankeyOption(series, rows, style, top) {
  const { nodeNames, links } = sankeyData(rows);
  if (!['left', 'right', 'justify'].includes(series.nodeAlign ?? 'justify')) {
    throw new Error('sankey nodeAlign must be left, right or justify');
  }
  if (Array.isArray(series.fill) && !series.fill.length) throw new Error('sankey fill must not be empty');
  // Zero and null flows have no visible area; keep them out of the layout to avoid 0/0 scaling.
  const positiveLinks = links.filter((link) => link.value > 0);
  const visible = new Set(positiveLinks.flatMap((link) => [link.source, link.target]));
  const sources = new Set(positiveLinks.map((link) => link.source));
  const data = nodeNames.map((name, index) => {
    let fill = series.fill;
    if (Array.isArray(fill)) fill = fill[index % fill.length];
    else if (fill && typeof fill === 'object' && fill.type !== 'gradient') {
      fill = Object.hasOwn(fill, name) ? fill[name] : undefined;
    }
    return {
      name,
      itemStyle: { color: style.paint(fill, style.palette[index % style.palette.length]), ...style.border(series.border) },
      label: { position: sources.has(name) ? 'right' : 'left' },
    };
  }).filter((node) => visible.has(node.name));
  return {
    series: [{
      type: 'sankey', data, links: positiveLinks, nodeAlign: series.nodeAlign ?? 'justify',
      top, left: 16, right: 16, bottom: 12,
      label: style.label(series, 'value'),
      lineStyle: { color: 'source', opacity: 0.36, curveness: 0.5 },
    }],
  };
}

function chartOption(chart, theme, echarts) {
  const { series, rows } = readChartData(chart);
  const style = chartStyle(chart, theme, echarts.color);
  const title = titleOption(chart, style);
  const top = title?.text ? title.textStyle.fontSize * 1.6 + 12 : 12;
  let content;
  let dash;
  switch (series.type) {
    case 'heatmap': content = heatmapOption(chart, series, rows, style, top); break;
    case 'sankey': content = sankeyOption(series, rows, style, top); break;
    default: ({ option: content, dash } = hierarchyOption(chart, series, rows, style, top));
  }
  return {
    option: {
      // The chart frame (fill, border, shadow) is drawn by native shapes; see frameLayers.
      animation: false, textStyle: style.text(), color: style.palette.map(style.color),
      backgroundColor: 'transparent',
      title, legend: { show: false }, tooltip: { show: false },
      ...content,
    },
    dash: dash && { ...dash, color: echarts.color.parse(dash.color) },
  };
}

function round(value) {
  return Math.round(value * 100) / 100;
}

// One dashed path over every treemap node edge, with shared edges merged so that
// adjacent cells do not draw two out-of-phase dash patterns on the same line.
function treemapDashGrid(svg, dash) {
  const lines = { h: new Map(), v: new Map() };
  const add = (map, at, from, to) => {
    const key = round(at);
    if (!map.has(key)) map.set(key, []);
    map.get(key).push([round(from), round(to)]);
  };
  let rects = 0;
  // The treemap series is laid out with zero border/gap width, so node rectangles tile exactly.
  for (const [tag] of svg.matchAll(/<path\b[^>]*\becmeta_data_index="\d+"[^>]*>/g)) {
    const size = /\sd="M0 0l([\d.]+) 0l0 ([\d.]+)l-[\d.]+ 0Z"/.exec(tag);
    if (!size) continue;
    const offset = /\stransform="translate\(([-\d.e]+)[ ,]([-\d.e]+)\)"/.exec(tag);
    if (/\stransform="/.test(tag) && !offset) continue;
    const [x, y] = offset ? [Number(offset[1]), Number(offset[2])] : [0, 0];
    const [w, h] = [Number(size[1]), Number(size[2])];
    add(lines.h, y, x, x + w);
    add(lines.h, y + h, x, x + w);
    add(lines.v, x, y, y + h);
    add(lines.v, x + w, y, y + h);
    rects++;
  }
  if (!rects) throw new Error('treemap border adapter found no node rectangles in the ECharts SVG');
  const segments = [];
  for (const [horizontal, map] of [[true, lines.h], [false, lines.v]]) {
    for (const [at, spans] of map) {
      spans.sort((a, b) => a[0] - b[0]);
      let [start, end] = spans[0];
      const flush = () => segments.push(horizontal ? `M${start} ${at}L${end} ${at}` : `M${at} ${start}L${at} ${end}`);
      for (const [from, to] of spans.slice(1)) {
        if (from > end + 0.5) {
          flush();
          start = from;
        }
        end = Math.max(end, to);
      }
      flush();
    }
  }
  const [r, g, b, a] = dash.color;
  const pattern = dash.type === 'dashed' ? [4 * dash.width, 2 * dash.width] : [dash.width, dash.width];
  const path = `<path d="${segments.join('')}" fill="none" stroke="rgb(${r},${g},${b})" stroke-opacity="${a}" ` +
    `stroke-width="${dash.width}" stroke-dasharray="${pattern.join(',')}"/>`;
  return svg.replace(/<\/svg>\s*$/, `${path}</svg>`);
}

// zrender centers every text with dominant-baseline="central", which PowerPoint ignores:
// it puts the alphabetic baseline at the center and the glyphs render ~0.35em too high.
function officeTextBaselines(svg) {
  return svg.replace(/<text\b[^>]*>/g, (tag) => {
    if (!tag.includes(' dominant-baseline="central"')) return tag;
    const size = Number(/font-size:\s*([\d.]+)px/.exec(tag)?.[1] ?? 12);
    const shift = size * CENTRAL_BASELINE_EM;
    tag = tag.replace(' dominant-baseline="central"', '');
    const y = /\sy="([-\d.e]+)"/.exec(tag);
    if (y) return tag.replace(y[0], ` y="${round(Number(y[1]) + shift)}"`);
    return tag.replace(/>$/, ` y="${round(shift)}">`);
  });
}

function chartSvg(svg, chart, dash) {
  if (!/^<svg\b/.test(svg)) throw new Error('chart renderer did not return SVG');
  if (dash) svg = treemapDashGrid(svg, dash);
  svg = officeTextBaselines(svg);
  const source = Buffer.from(JSON.stringify(chart), 'utf8').toString('base64url');
  const metadata = `<metadata><pptd:source xmlns:pptd="https://pptd.local/ns/2026/pptd/schema" kind="chart" encoding="base64url">${source}</pptd:source></metadata>`;
  return svg.replace(/<svg\b[^>]*>/, (root) => root + metadata);
}

function defined(object) {
  return Object.fromEntries(Object.entries(object).filter(([, value]) => value !== undefined));
}

// The chart frame becomes native rectangles around a bare SVG picture. PowerPoint casts a
// picture's shadow from its alpha (every label and cell), and the writer splits picture
// borders into a separate, unanimated shape; plain shapes avoid both.
function frameLayers(chart, uniqueId) {
  const base = {
    elementType: 'shape', shapeName: 'rect', bounds: chart.bounds,
    rotation: chart.rotation, opacity: chart.opacity, flip: chart.flip,
  };
  const below = chart.fill
    ? defined({ ...base, elementId: uniqueId('background'), fill: chart.fill, shadow: chart.shadow })
    : undefined;
  // Without a fill, the shadow follows the frame line, as on an unfilled PowerPoint shape.
  const above = chart.border
    ? defined({ ...base, elementId: uniqueId('frame'), border: chart.border, shadow: below ? undefined : chart.shadow })
    : undefined;
  return { below, above };
}

export async function prepareAdvancedCharts(project, images) {
  if (!project.pages.some((page) => page.elements.some(isAdvancedChart))) return;
  // Only advanced charts load the bundled SSR renderer; native charts keep their WASM path.
  const echarts = await import('../assets/charts/echarts.mjs');
  for (const [pageIndex, page] of project.pages.entries()) {
    const elements = [];
    const elementIds = new Set(page.elements.map((element) => element.elementId));
    const layers = new Map();
    for (const [elementIndex, chart] of page.elements.entries()) {
      if (!isAdvancedChart(chart)) {
        elements.push(chart);
        continue;
      }
      let renderer;
      try {
        const [,, width, height] = chart.bounds ?? [];
        if (![width, height].every((value) => Number.isFinite(value) && value > 0)) {
          throw new Error('chart bounds must have positive finite width and height');
        }
        const { option, dash } = chartOption(chart, project.theme, echarts);
        renderer = echarts.init(null, null, { renderer: 'svg', ssr: true, width, height });
        renderer.setOption(option);
        const svg = chartSvg(renderer.renderToSVGString({ useViewBox: true }), chart, dash);
        const src = `wasm-assets/chart-${pageIndex + 1}-${elementIndex + 1}.svg`;
        images[src] = new TextEncoder().encode(svg);
        const { below, above } = frameLayers(chart, (suffix) => {
          let id = `${chart.elementId}-${suffix}`;
          for (let index = 1; elementIds.has(id); index++) id = `${chart.elementId}-${suffix}-${index}`;
          elementIds.add(id);
          return id;
        });
        // chartImages is PNG-only in this writer. A normal SVG image keeps the correct MIME type.
        elements.push(...[below, defined({
          elementId: chart.elementId, elementType: 'image', bounds: chart.bounds,
          src, fit: { mode: 'fill' },
          rotation: chart.rotation, opacity: chart.opacity, flip: chart.flip,
        }), above].filter(Boolean));
        const ids = [below, above].filter(Boolean).map((layer) => layer.elementId);
        if (ids.length) layers.set(chart.elementId, ids);
      } catch (error) {
        throw new Error(`${page.pagePath ?? `slide ${pageIndex + 1}`}: chart ${chart.elementId}: ${error.message ?? error}`, { cause: error });
      } finally {
        renderer?.dispose();
      }
    }
    page.elements = elements;
    if (layers.size && Array.isArray(page.animations)) {
      page.animations = page.animations.flatMap((animation) => {
        const ids = UNMIRRORED_EFFECTS.has(animation.effect) ? undefined : layers.get(animation.elementId);
        return [animation, ...(ids ?? []).map((elementId) => ({ ...animation, elementId, trigger: 'withPrevious' }))];
      });
    }
  }
}
