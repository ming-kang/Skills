// Split CSS tokens respecting quoted family names and parenthesized url(...) values.
export const CSS_NUMBER = /^[+-]?\d+(?:\.\d+)?$/;

export function splitCss(value, delimiter) {
  const result = [];
  let start = 0;
  let quote = '';
  let depth = 0;
  for (let i = 0; i < value.length; i++) {
    const char = value[i];
    if (char === '\\') { i++; continue; }
    if (quote) { if (char === quote) quote = ''; continue; }
    if (char === '"' || char === "'") { quote = char; continue; }
    if (char === '(') depth++;
    else if (char === ')') depth--;
    else if (char === delimiter && depth === 0) {
      result.push(value.slice(start, i));
      start = i + 1;
    }
    if (depth < 0) throw new Error('unbalanced inline CSS');
  }
  if (quote || depth) throw new Error('unbalanced inline CSS');
  result.push(value.slice(start));
  return result;
}

/**
 * Inline declarations with CSS !important precedence; quoted/URL separators stay intact.
 * Authored rich text is read leniently, like a browser: a malformed declaration is
 * skipped. `strict` fails closed instead, for generated SVG that must be fully understood.
 */
export function parseCss(value = '', { strict = false } = {}) {
  const declarations = new Map(), important = new Set();
  let parts;
  try {
    if (strict && value.includes('/*')) throw new Error('comments in inline CSS are unsupported');
    parts = splitCss(value, ';');
  } catch (error) {
    if (strict) throw error;
    parts = value.split(';');
  }
  for (const part of parts) {
    if (!part.trim()) continue;
    const colon = part.indexOf(':');
    const property = part.slice(0, Math.max(colon, 0)).trim().toLowerCase();
    const raw = colon < 0 ? '' : part.slice(colon + 1);
    if (!property || !raw.trim() || (strict && splitCss(part, ':').length !== 2)) {
      if (strict) throw new Error(`unsupported inline CSS declaration: ${part}`);
      continue;
    }
    const priority = /\s*!important\s*$/i.test(raw);
    if (!important.has(property) || priority) {
      declarations.set(property, raw.replace(/\s*!important\s*$/i, '').trim());
      if (priority) important.add(property);
    }
  }
  return declarations;
}
