// Shared HEX, $theme token and gradient color validation/resolution.

const HEX_PATTERN = /^#?[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?$/;

export const NAMED_COLORS = {
  black: '000000', white: 'FFFFFF', red: 'FF0000', green: '008000', blue: '0000FF',
  yellow: 'FFFF00', orange: 'FFA500', purple: '800080', gray: '808080', grey: '808080',
  brown: 'A52A2A', cyan: '00FFFF', magenta: 'FF00FF', teal: '008080', navy: '000080',
  lime: '00FF00', maroon: '800000', olive: '808000', silver: 'C0C0C0',
};

export function checkHexColor(value, label) {
  if (typeof value !== 'string' || !HEX_PATTERN.test(value)) {
    throw new Error(`${label} must be a six/eight-digit HEX color`);
  }
  return value;
}

export function resolveThemeColor(value, themeColors = {}, label = 'color') {
  const visited = new Set();
  let current = value;
  while (typeof current === 'string' && current.startsWith('$')) {
    const token = current.slice(1);
    if (!token) throw new Error(`${label} theme color reference must name a token`);
    if (visited.has(token)) throw new Error(`${label} contains a cyclic color reference`);
    if (!Object.hasOwn(themeColors, token)) {
      throw new Error(`${label} references an unknown theme color: ${JSON.stringify(current)}`);
    }
    visited.add(token);
    current = themeColors[token];
  }
  return current;
}

export function checkColorSpec(value, label, themeColors = null) {
  if (typeof value === 'string') {
    if (value.startsWith('$')) {
      const token = value.slice(1);
      if (!token) throw new Error(`${label} theme color reference must name a token`);
      if (themeColors && !Object.hasOwn(themeColors, token)) {
        throw new Error(`${label} references an unknown theme color: ${JSON.stringify(value)}`);
      }
      return;
    }
    checkHexColor(value, label);
    return;
  }
  if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
    if (value.type !== 'gradient') throw new Error(`${label}.type must be gradient for a gradient mapping`);
    if (!['linear', 'radial'].includes(value.gradientType)) throw new Error(`${label}.gradientType must be linear or radial`);
    const stops = value.stops;
    if (!Array.isArray(stops) || stops.length < 2) throw new Error(`${label}: a gradient requires at least two color stops`);
    for (const [index, stop] of stops.entries()) {
      if (typeof stop !== 'object' || stop === null || typeof stop.position !== 'number' || !Number.isFinite(stop.position) || stop.position < 0 || stop.position > 1) {
        throw new Error(`${label}.stops[${index}] must have a position in [0, 1]`);
      }
      checkColorSpec(stop.color, `${label}.stops[${index}].color`, themeColors);
    }
    if (value.gradientType === 'linear' && value.angle !== undefined && (typeof value.angle !== 'number' || !Number.isFinite(value.angle) || value.angle < 0 || value.angle >= 360)) {
      throw new Error(`${label}.angle must be in [0, 360)`);
    }
    return;
  }
  throw new Error(`${label} must be a HEX color, a $theme token or a gradient mapping`);
}
