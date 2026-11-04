import assert from 'node:assert/strict';
import test from 'node:test';

import { prepareAdvancedCharts } from '../../../pptd/scripts/advanced-charts.mjs';

const HIERARCHY = {
  cols: ['node', 'parent', 'value'],
  rows: [['A', null, null], ['A1', 'A', 3], ['A2', 'A', 1], ['B', null, 2]],
};

function treemap(extra = {}, series = {}) {
  return {
    elementId: 'chart', elementType: 'chart', bounds: [40, 40, 400, 300], data: HIERARCHY,
    series: [{ type: 'treemap', encode: { category: 'node', parent: 'parent', value: 'value' }, ...series }],
    ...extra,
  };
}

async function prepare(elements, { animations, theme } = {}) {
  const page = { pagePath: 'pages/01.page', elements, ...(animations && { animations }) };
  const project = { theme: theme ?? { colors: { text: '#1F2937', bg: '#FFFFFF' } }, pages: [page] };
  const images = {};
  await prepareAdvancedCharts(project, images);
  const svgs = Object.values(images).map((bytes) => new TextDecoder().decode(bytes));
  return { page, svgs };
}

test('chart text carries an explicit baseline instead of dominant-baseline', async () => {
  const { svgs: [svg] } = await prepare([treemap({ title: 'Revenue' }, { dataLabels: { show: true } })]);
  const texts = svg.match(/<text\b[^>]*>/g);
  assert.ok(texts.length >= 3);
  assert.doesNotMatch(svg, /dominant-baseline/);
  // PowerPoint ignores dominant-baseline="central"; the 0.35em shift is baked into y.
  const title = texts.find((tag) => tag.includes('font-size:16px'));
  assert.match(title, /\sy="13\.6"/);
  for (const tag of texts) assert.match(tag, /\sy="[-\d.]+"/);
});

test('the chart frame becomes native shapes around a bare picture', async () => {
  const chart = treemap({
    fill: { type: 'solid', color: '#F8FAFC' },
    border: { color: '#CBD5E1', width: 1 },
    shadow: { blur: 4, color: '#00000022', offset: [1, 2] },
  });
  const { page, svgs: [svg] } = await prepare([chart], {
    animations: [
      { elementId: 'chart', effect: 'fade-in', delayMs: 200 },
      { elementId: 'chart', effect: 'fill-color', color: '#FF0000' },
    ],
  });
  const [background, picture, frame] = page.elements;
  assert.deepEqual(page.elements.map((element) => element.elementId), ['chart-background', 'chart', 'chart-frame']);
  assert.deepEqual(background.fill, chart.fill);
  assert.deepEqual(background.shadow, chart.shadow);
  assert.equal(background.border, undefined);
  assert.equal(picture.elementType, 'image');
  assert.equal(picture.border, undefined);
  assert.equal(picture.shadow, undefined);
  assert.deepEqual(frame.border, chart.border);
  assert.equal(frame.fill, undefined);
  assert.equal(frame.shadow, undefined);
  // The picture itself stays transparent; the fill is the native background shape.
  assert.doesNotMatch(svg, /rgb\(248,250,252\)/);
  assert.deepEqual(page.animations, [
    { elementId: 'chart', effect: 'fade-in', delayMs: 200 },
    { elementId: 'chart-background', effect: 'fade-in', delayMs: 200, trigger: 'withPrevious' },
    { elementId: 'chart-frame', effect: 'fade-in', delayMs: 200, trigger: 'withPrevious' },
    { elementId: 'chart', effect: 'fill-color', color: '#FF0000' },
  ]);
});

test('an unfilled frame keeps the shadow on its line and image fills carry no border', async () => {
  const outlined = treemap({ border: { color: '#000000', width: 1 }, shadow: { blur: 2, color: '#000000' } });
  const { page } = await prepare([outlined]);
  assert.deepEqual(page.elements.map((element) => element.elementId), ['chart', 'chart-frame']);
  assert.deepEqual(page.elements[1].shadow, outlined.shadow);

  const imageFill = treemap({ elementId: 'pictured', fill: { type: 'image', src: 'wasm-assets/img-0.png' } });
  const { page: filled } = await prepare([imageFill, { elementId: 'pictured-background', elementType: 'text' }]);
  const background = filled.elements.find((element) => element.fill?.type === 'image');
  assert.equal(background.elementId, 'pictured-background-1');
  assert.equal(Object.hasOwn(background, 'border'), false);
});

test('series colors use the native chart cycle, not every theme token', async () => {
  const sankey = {
    elementId: 'flow', elementType: 'chart', bounds: [0, 0, 600, 300],
    data: { cols: ['s', 't', 'f'], rows: [['a', 'b', 6], ['a', 'c', 4], ['b', 'd', 6], ['c', 'd', 4]] },
    series: [{ type: 'sankey', encode: { source: 's', target: 't', flow: 'f' } }],
  };
  const { svgs: [svg] } = await prepare([sankey]);
  for (const rgb of ['23,131,255', '104,184,168', '201,168,106', '140,132,201']) {
    assert.match(svg, new RegExp(`fill="rgb\\(${rgb}\\)"`));
  }
  assert.doesNotMatch(svg, /fill="rgb\((31,41,55|255,255,255)\)"/);
});

test('hierarchy nodes are separated by default and labels contrast with their fill', async () => {
  const sunburst = treemap({}, { type: 'sunburst', dataLabels: { show: true } });
  const { svgs: [tree] } = await prepare([treemap({}, { dataLabels: { show: true } })]);
  const { svgs: [sun] } = await prepare([sunburst]);
  // Default 1px white separators: treemap border strips, sunburst sector strokes.
  assert.match(tree, /fill="rgb\(255,255,255\)"/);
  assert.match(sun, /stroke="rgb\(255,255,255\)"/);
  const labelFill = (svg, text) => new RegExp(`<text\\b[^>]*fill="([^"]+)"[^>]*>${text}<`).exec(svg)?.[1];
  assert.equal(labelFill(tree, 'A1'), '#FFFFFF');
  assert.equal(labelFill(tree, 'B'), 'rgb(31,41,55)');
  assert.equal(labelFill(sun, 'A'), '#FFFFFF');

  const explicit = treemap({}, { dataLabels: { show: true, color: '#FF0000' } });
  const { svgs: [red] } = await prepare([explicit]);
  assert.equal(labelFill(red, 'A1'), 'rgb(255,0,0)');
});

test('dashed treemap borders are one deduplicated grid', async () => {
  const chart = treemap({}, { border: { style: 'dash', width: 2, color: '#47556980' } });
  const { svgs: [svg] } = await prepare([chart]);
  const dashed = svg.match(/<path\b[^>]*stroke-dasharray[^>]*>/g);
  assert.equal(dashed.length, 1);
  assert.match(dashed[0], /stroke="rgb\(71,85,105\)" stroke-opacity="0\.50\d*" stroke-width="2" stroke-dasharray="8,4"/);
  const segments = dashed[0].match(/M[^ML"]+L[^M"]+/g);
  assert.equal(new Set(segments).size, segments.length);
  // Outer rectangle, the A|B boundary, and the A1|A2 boundary.
  assert.equal(segments.length, 6);
});

test('heatmap cells pick label colors from the color scale', async () => {
  const heatmap = {
    elementId: 'heat', elementType: 'chart', bounds: [0, 0, 400, 300],
    data: { cols: ['x', 'y', 'v'], rows: [['Mon', 'AM', 0], ['Tue', 'AM', 10], ['Mon', 'PM', null]] },
    series: [{ type: 'heatmap', encode: { x: 'x', y: 'y', value: 'v' }, dataLabels: { show: true }, colorbar: false }],
  };
  const { svgs: [svg] } = await prepare([heatmap]);
  assert.match(svg, /<text\b[^>]*fill="rgb\(31,41,55\)"[^>]*>0</);
  assert.match(svg, /<text\b[^>]*fill="#FFFFFF"[^>]*>10</);
});

test('the SVG keeps the source chart and native charts pass through', async () => {
  const chart = treemap();
  const bar = {
    elementId: 'bar', elementType: 'chart', bounds: [0, 0, 100, 100],
    data: { cols: ['x', 'y'], rows: [['a', 1]] }, series: [{ type: 'bar', encode: { x: 'x', y: 'y' } }],
  };
  const source = structuredClone(chart);
  const { page, svgs: [svg] } = await prepare([chart, bar]);
  const encoded = /<pptd:source[^>]*>([^<]+)</.exec(svg)[1];
  assert.deepEqual(JSON.parse(Buffer.from(encoded, 'base64url').toString('utf8')), source);
  assert.equal(page.elements.at(-1), bar);
});

test('invalid advanced chart data names the page and chart', async () => {
  const cyclic = {
    elementId: 'loop', elementType: 'chart', bounds: [0, 0, 400, 300],
    data: { cols: ['s', 't', 'f'], rows: [['a', 'b', 1], ['b', 'a', 1]] },
    series: [{ type: 'sankey', encode: { source: 's', target: 't', flow: 'f' } }],
  };
  await assert.rejects(prepare([cyclic]), /^Error: pages\/01\.page: chart loop: sankey contains a cycle$/);
});
