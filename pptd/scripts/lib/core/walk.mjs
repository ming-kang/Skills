// Nested configuration objects; chart rows/filter values are data, never styles or assets.
export function* walkObjects(value, label = '') {
  if (Array.isArray(value)) {
    for (const [index, child] of value.entries()) yield* walkObjects(child, `${label}[${index}]`);
  } else if (value && typeof value === 'object') {
    yield [value, label];
    for (const [key, child] of Object.entries(value)) {
      if (key !== 'data' && key !== 'dataFilter') yield* walkObjects(child, label ? `${label}.${key}` : key);
    }
  }
}
