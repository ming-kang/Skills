// YAML 1.2 parsing for the PPTD format contract, from the vendored `yaml` package.
// YAML 1.1 loaders misread the private format: `notes: 2026-11-14` must stay a string,
// `version: v2` a string, and 0o17/0x1F integers. PyYAML's SafeLoader needs a custom
// resolver stack to approximate this; this module is the single source of that truth.
import { parseDocument, visit } from '../../../assets/vendor/yaml.mjs';

// Only plain values reach the exporter: never trust a tag's semantics for data.
function plainDocument(text, label) {
  const document = parseDocument(text, { strict: true, uniqueKeys: true, version: '1.2', schema: 'core' });
  if (document.errors.length) throw new Error(`invalid YAML in ${label}: ${document.errors[0].message}`);
  if (document.warnings.length) throw new Error(`unsupported YAML in ${label}: ${document.warnings[0].message}`);
  if (document.hasDirectives) throw new Error(`YAML directives are not supported in ${label}`);
  visit(document, {
    // Tags other than the implicit plain/str would silently change scalar meaning.
    Scalar(key, node, path) {
      if (node.tag?.startsWith('tag:yaml.org,2002:') && !['str', 'int', 'float', 'bool', 'null'].includes(node.tag.slice(19))) {
        throw new Error(`${label}: YAML tags are not supported (${node.tag})`);
      }
      if (node.range.length === 2 && node.value === '') throw new Error(`${label}: empty plain scalar`);
    },
    Pair(key, pair) {
      if (pair.key && pair.key.value === '<<') throw new Error(`${label}: explicit merge keys are not supported`);
    },
    Node(key, node, path) {
      const field = path.length ? `.${String(path.at(-1))}` : '';
      if (node.range.length === 1) throw new Error(`${label}${field}: empty value`);
    },
  });
  return document;
}

/** Parse one PPTD YAML file into JSON-compatible plain data (maps, lists, scalars). */
export function readYamlMapping(text, label) {
  const document = plainDocument(text, label);
  const value = document.toJS({ json: true, maxAliasCount: 100 });
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`expected a YAML mapping in ${label}`);
  }
  // A shared anchor node must be copied before it is normalized in two places.
  return JSON.parse(JSON.stringify(value));
}

/** YAML 1.2 core-schema scalars: 1_000 and 0x1F are numbers, 2026-11-14 is a string. */
export function yamlScalarKind(value) {
  if (value === null) return 'null';
  if (typeof value === 'boolean') return 'bool';
  if (typeof value === 'number') return Number.isInteger(value) ? 'int' : 'float';
  if (typeof value === 'string') return 'str';
  throw new Error(`YAML produced an unsupported value: ${typeof value}`);
}
