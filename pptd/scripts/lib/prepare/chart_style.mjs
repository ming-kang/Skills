// The WASM writer's native chart cycle, so advanced and native charts in one deck match.
// Theme.colors also holds text/background tokens, so it is not a series palette.
const DEFAULT_PALETTE = ['#1783FF', '#68B8A8', '#C9A86A', '#8C84C9', '#8D98A8', '#5F9CF5', '#7BB6D9', '#B28A9E'];
const DARK_LABEL = '#111827';
const LIGHT_LABEL = '#FFFFFF';

export function lineStyle(value = 'solid') {
  const types = { solid: 'solid', dash: 'dashed', dot: 'dotted' };
  if (!Object.hasOwn(types, value)) throw new Error(`invalid chart line style: ${value}`);
  return types[value];
}

export function formatNumber(value, format) {
  if (value == null) return '';
  if (!format) return String(value);
  if (format === '#,##0') return value.toLocaleString('en-US', { maximumFractionDigits: 0 });
  if (format === '0.0E+00') {
    const [mantissa, exponent] = value.toExponential(1).split('e');
    return `${mantissa}E${Number(exponent) < 0 ? '-' : '+'}${String(Math.abs(Number(exponent))).padStart(2, '0')}`;
  }
  const match = /^0(?:\.(0+))?(%)?$/.exec(format);
  if (!match) throw new Error(`unsupported chart numberFormat: ${format}`);
  const digits = match[1]?.length ?? 0;
  return (value * (match[2] ? 100 : 1)).toFixed(digits) + (match[2] ?? '');
}

function fontFamily(value) {
  if (value == null) return 'MiSans, sans-serif';
  if (typeof value === 'string' && value.trim()) return value;
  if (value && typeof value.latin === 'string' && typeof value.ea === 'string') {
    return [value.latin, value.ea].filter(Boolean).join(', ');
  }
  throw new Error('chart fontFamily must be a font name or {latin, ea}');
}

export function chartStyle(chart, theme, colorApi) {
  const colors = theme?.colors ?? {};
  function resolveColor(value) {
    const visited = new Set();
    while (typeof value === 'string' && value.startsWith('$')) {
      if (visited.has(value) || !Object.hasOwn(colors, value.slice(1))) {
        throw new Error(`unresolved or cyclic chart color: ${value}`);
      }
      visited.add(value);
      value = colors[value.slice(1)];
    }
    if (typeof value !== 'string' || !/^#[\da-f]{6}(?:[\da-f]{2})?$/i.test(value)) {
      throw new Error(`chart color must be HEX6, HEX8 or a theme token: ${value}`);
    }
    return value;
  }

  function color(value) {
    // Normalize HEX8 for both ECharts' color scale and SVG consumers.
    return colorApi.stringify(colorApi.parse(resolveColor(value)), 'rgba');
  }

  const palette = DEFAULT_PALETTE;
  const textColor = Object.hasOwn(colors, 'text') ? color('$text') : '#333333';

  // Perceptual lightness in [0, 1] (zrender's lum); gradients use their average stop.
  function perceivedLightness(value) {
    if (value && typeof value === 'object') {
      const stops = value.colorStops.map((stop) => perceivedLightness(stop.color));
      return stops.reduce((sum, item) => sum + item, 0) / stops.length;
    }
    return colorApi.lum(value, 1);
  }

  // Label color for text drawn on top of `fill`, unless the deck sets one explicitly.
  // White on saturated mid-tones, the theme text color (or near-black) on light fills.
  function labelColor(series, fill) {
    const configured = series.dataLabels?.color ?? chart.dataLabels?.color;
    if (configured !== undefined) return color(configured);
    if (perceivedLightness(fill) <= 0.6) return LIGHT_LABEL;
    return perceivedLightness(textColor) < 0.4 ? textColor : DARK_LABEL;
  }

  // The color ECharts' continuous visualMap assigns to `value` (stops evenly spread over the domain).
  function scaleColor(stops, [min, max], value) {
    const t = Math.min(1, Math.max(0, (value - min) / (max - min)));
    return colorApi.lerp(t, stops);
  }

  function shade(value, depth) {
    const resolved = color(value);
    if (!depth) return resolved;
    const rgb = colorApi.parse(resolved).slice(0, 3);
    const lightness = (Math.max(...rgb) + Math.min(...rgb)) / 510;
    return colorApi.modifyHSL(resolved, null, null, Math.max(0, lightness - depth * 0.1));
  }

  function paint(value, fallback = DEFAULT_PALETTE[0], depth = 0) {
    if (value == null) value = fallback;
    if (typeof value === 'string') return shade(value, depth);
    if (value.type === 'solid') return shade(value.color, depth);
    if (value.type !== 'gradient' || !['linear', 'radial'].includes(value.gradientType)) {
      throw new Error('chart paint must be a color or a linear/radial gradient');
    }
    if (!Array.isArray(value.stops) || value.stops.length < 2) {
      throw new Error('chart gradients need at least two stops');
    }
    const colorStops = value.stops.map((stop) => {
      if (!Number.isFinite(stop.position) || stop.position < 0 || stop.position > 1) {
        throw new Error('chart gradient stop.position must be between 0 and 1');
      }
      return { offset: stop.position, color: shade(stop.color, depth) };
    }).sort((a, b) => a.offset - b.offset);
    if (value.gradientType === 'radial') {
      return { type: 'radial', x: 0.5, y: 0.5, r: 0.5, colorStops };
    }
    const angle = (value.angle ?? 0) * Math.PI / 180;
    if (!Number.isFinite(angle)) throw new Error('chart gradient angle must be finite');
    return {
      type: 'linear',
      x: 0.5 - Math.cos(angle) / 2, y: 0.5 - Math.sin(angle) / 2,
      x2: 0.5 + Math.cos(angle) / 2, y2: 0.5 + Math.sin(angle) / 2,
      colorStops,
    };
  }

  function text(config = {}, size = 12) {
    config ??= {};
    if (config.fontSize !== undefined && !(Number.isFinite(config.fontSize) && config.fontSize > 0)) {
      throw new Error('chart fontSize must be positive and finite');
    }
    return {
      color: config.color === undefined ? textColor : color(config.color),
      fontSize: config.fontSize ?? size,
      fontFamily: fontFamily(config.fontFamily ?? chart.fontFamily),
    };
  }

  function border(config) {
    if (config == null) return { borderWidth: 0 };
    const width = config.width ?? 1;
    if (!Number.isFinite(width) || width < 0) throw new Error('chart border width must be non-negative and finite');
    return {
      borderWidth: width,
      borderColor: color(config.color ?? '#000000'),
      borderType: lineStyle(config.style),
    };
  }

  function label(series, defaultContent, valueOf = (params) => params.value) {
    const config = { ...chart.dataLabels, ...series.dataLabels };
    const content = config.content ?? defaultContent;
    const allowed = series.type === 'heatmap' ? ['value'] : ['category', 'value'];
    if (!allowed.includes(content)) {
      throw new Error(`${series.type} does not support dataLabels.content: ${content}`);
    }
    // Validate formatting even when an empty dataset never invokes the formatter.
    formatNumber(0, config.numberFormat);
    return {
      show: config.show === true,
      ...text(config),
      formatter: (params) => content === 'category'
        ? params.name
        : formatNumber(valueOf(params), config.numberFormat),
    };
  }

  return { color, palette, paint, text, border, label, labelColor, scaleColor };
}
