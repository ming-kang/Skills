#!/usr/bin/env node
/**
 * Offline PPTD → PPTX exporter using Kimi's public patched pptd-wasm.
 *
 * What this does:
 *   1. Load a PPTD project from disk (manifest + pages + media)
 *   2. Resolve images to bytes
 *   3. Derive the local offline signature accepted by the patched WASM
 *   4. Call the WASM writer: exportPPTDToPPTXBytes(pptd, options, signature)
 *   5. Write .pptx
 *
 * No network, no cookie, no browser. Usually invoked through
 * scripts/export_pptx.py, which also patches slide transitions.
 *
 * Usage:
 *   node export-pptd.mjs <projectDirOr.pptd> -o out.pptx [--transition fade|none]
 */

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

// ---------- YAML (standalone use only) ----------
// scripts/export_pptx.py never reaches this: it parses the project with PyYAML
// and hands over --json. This chain only serves direct `node export-pptd.mjs`
// invocations, where no npm package tree is guaranteed next to the skill.
const PYTHON_CANDIDATES = [
  process.env.PPTD_PYTHON,
  'python3',
  'python',
  'py',
].filter(Boolean);

function pythonYamlParser() {
  const { spawnSync } = require('node:child_process');
  const script =
    'import sys,yaml,json; print(json.dumps(yaml.safe_load(sys.stdin.read()), ensure_ascii=False))';
  const failures = [];
  for (const exe of PYTHON_CANDIDATES) {
    const args = exe === 'py' ? ['-3', '-c', script] : ['-c', script];
    const probe = spawnSync(exe, args, { input: '{}', encoding: 'utf8' });
    if (probe.error || probe.status !== 0) {
      failures.push(`${exe}: ${probe.error?.code || probe.stderr?.trim() || 'failed'}`);
      continue;
    }
    return (text) => {
      const r = spawnSync(exe, args, {
        input: text,
        encoding: 'utf8',
        maxBuffer: 50 * 1024 * 1024,
      });
      if (r.status !== 0) throw new Error('python yaml failed: ' + (r.stderr || r.stdout));
      return JSON.parse(r.stdout);
    };
  }
  throw new Error(
    'No YAML parser available. Install the npm "yaml" package next to this script, ' +
      'or make a Python with PyYAML reachable (set PPTD_PYTHON), ' +
      'or pass a pre-parsed project with --json.\nTried: ' +
      failures.join('; '),
  );
}

async function loadYaml() {
  try {
    const yaml = await import('yaml');
    return yaml.parse;
  } catch {
    try {
      const yaml = require('js-yaml');
      return (s) => yaml.load(s);
    } catch {
      return pythonYamlParser();
    }
  }
}

/** Single canonical patched WASM, shipped in the skill at assets/editor/. */
const CANONICAL_WASM_NAME = 'pptd_wasm_bg-DPPWdROu.wasm';

function resolveDefaultWasmPath() {
  // scripts/local-export → skill root → assets/editor/neo-ppt/assets/
  return path.join(
    __dirname,
    '..',
    '..',
    'assets',
    'editor',
    'neo-ppt',
    'assets',
    CANONICAL_WASM_NAME,
  );
}

// ---------- CLI ----------
const TRANSITIONS = new Set(['fade', 'none']);

function parseArgs(argv) {
  const args = {
    input: null,
    output: null,
    transition: 'fade',
    wasmPath: null,
    json: null,
  };
  const a = [...argv];
  while (a.length) {
    const x = a.shift();
    if (x === '-o' || x === '--output') args.output = a.shift();
    else if (x === '--transition') args.transition = a.shift();
    else if (x === '--wasm') args.wasmPath = a.shift();
    else if (x === '--json') args.json = a.shift();
    else if (x === '-h' || x === '--help') args.help = true;
    else if (!x.startsWith('-') && !args.input) args.input = x;
    else throw new Error(`Unknown arg: ${x}`);
  }
  if (!args.wasmPath) args.wasmPath = resolveDefaultWasmPath();
  if (!args.help && !TRANSITIONS.has(args.transition)) {
    throw new Error(
      `--transition must be one of ${[...TRANSITIONS].join('|')}; got: ${args.transition}`,
    );
  }
  return args;
}

// ---------- PPTD project load ----------
function findManifest(input) {
  const p = path.resolve(input);
  if (!fs.existsSync(p)) throw new Error(`Input does not exist: ${p}`);
  if (fs.statSync(p).isFile()) {
    if (!p.endsWith('.pptd')) {
      throw new Error(`Input must be a .pptd file or a project directory: ${p}`);
    }
    return p;
  }
  const files = fs.readdirSync(p).filter((f) => f.endsWith('.pptd'));
  if (files.length === 1) return path.join(p, files[0]);
  if (files.length === 0) throw new Error(`No .pptd in ${p}`);
  throw new Error(`Multiple .pptd in ${p}: ${files.join(', ')}`);
}

/**
 * PPTD spec: every referenced file lives inside the folder holding the .pptd,
 * and paths are relative to it. Mirrors safe_project_path() in export_pptx.py.
 */
function safeJoin(root, relative) {
  if (typeof relative !== 'string' || !relative.trim()) {
    throw new Error('project path must be a non-empty string');
  }
  const base = path.resolve(root);
  const target = path.resolve(base, relative.replace(/\\/g, '/'));
  const prefix = base.endsWith(path.sep) ? base : base + path.sep;
  if (target !== base && !target.startsWith(prefix)) {
    throw new Error(`project path escapes the PPTD directory: ${relative}`);
  }
  return target;
}

/** Match official nt()/rt() shape: embed full page objects. */
function buildProject(manifest, pages, manifestPath) {
  return {
    ...manifest,
    version: 'v2',
    pages: pages.map(({ rel, page }) => {
      if (!page || !Array.isArray(page.elements)) {
        throw new Error(`Invalid page elements: ${rel}`);
      }
      return {
        ...page,
        pagePath: String(rel).replace(/\\/g, '/'),
        elements: page.elements.map(normalizeElement),
      };
    }),
    pptdFileName: path.basename(manifestPath),
  };
}

function assertManifest(manifest) {
  if (!manifest || manifest.version !== 'v2') {
    throw new Error('Only PPTD version: v2 is supported');
  }
  if (!Array.isArray(manifest.pages) || !manifest.pages.length) {
    throw new Error('manifest.pages must be a non-empty array');
  }
}

async function loadProject(manifestPath, parseYaml) {
  const root = path.dirname(manifestPath);
  const manifest = parseYaml(fs.readFileSync(manifestPath, 'utf8'));
  assertManifest(manifest);

  const pages = manifest.pages.map((rel) => {
    const pagePath = safeJoin(root, rel);
    if (!fs.existsSync(pagePath)) throw new Error(`Missing page: ${rel}`);
    return { rel, page: parseYaml(fs.readFileSync(pagePath, 'utf8')) };
  });

  return buildProject(manifest, pages, manifestPath);
}

/**
 * Pre-parsed project handed over by export_pptx.py, which already has PyYAML.
 * Shape: { manifestPath, manifest, pages: [{ path, data }] }
 */
function loadProjectFromJson(jsonPath) {
  const payload = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
  const { manifestPath, manifest } = payload;
  if (typeof manifestPath !== 'string' || !manifestPath) {
    throw new Error('--json payload needs a manifestPath');
  }
  assertManifest(manifest);
  if (!Array.isArray(payload.pages) || !payload.pages.length) {
    throw new Error('--json payload needs a non-empty pages array');
  }
  const pages = payload.pages.map((entry) => ({ rel: entry.path, page: entry.data }));
  return { project: buildProject(manifest, pages, manifestPath), manifestPath };
}

function normalizeElement(el) {
  // Official it()/at(): ensure custom shapes get viewBox from bounds
  const size = [el.bounds?.[2], el.bounds?.[3]];
  if (el.elementType === 'shape') {
    return normalizeCustomShape(el, size);
  }
  if (el.elementType === 'image' && el.cropShape) {
    return {
      ...el,
      cropShape: normalizeCustomShape(el.cropShape, size),
    };
  }
  return el;
}

/**
 * Give a custom shape its viewBox, whichever encoding the deck used.
 *
 * A custom shape's path is either "w,h;pathdata" (split into viewBox + path)
 * or a bare pathdata string whose viewBox comes from the element's bounds.
 * One normalizer for both encodings: the old code bailed out on the ";"
 * encoding here and left it to a second, separate pass, so every reader had
 * to hold both data shapes in their head at once.
 */
function normalizeCustomShape(shape, size) {
  if (shape?.shapeName !== 'custom' || !shape.path || shape.viewBox) return shape;
  const separator = String(shape.path).indexOf(';');
  if (separator >= 0) {
    const [w, h] = String(shape.path)
      .slice(0, separator)
      .split(',')
      .map(Number);
    if (!(w > 0) || !(h > 0)) return shape;
    return { ...shape, viewBox: [w, h], path: String(shape.path).slice(separator + 1) };
  }
  return { ...shape, viewBox: size };
}

// ---------- image resolve (official Bt + Ht) ----------
function collectImageSrcs(pptd) {
  const set = new Set();
  const visit = (obj) => {
    if (obj && typeof obj.src === 'string' && obj.src) set.add(obj.src);
  };
  for (const page of pptd.pages ?? []) {
    if (page.background?.type === 'image') visit(page.background);
    for (const el of page.elements ?? []) {
      if (el?.elementType === 'image') visit(el);
      if (el?.fill?.type === 'image') visit(el.fill);
    }
  }
  return [...set];
}

function extFromSrc(src, contentType = '') {
  const m = /\.(png|jpe?g|gif|svg)(?:$|[?#])/i.exec(src);
  const byPath = m?.[1]?.toLowerCase();
  const byCt = {
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/gif': 'gif',
    'image/svg+xml': 'svg',
  }[String(contentType).split(';')[0].trim()];
  let ext = byPath || byCt || 'png';
  if (ext === 'jpeg') ext = 'jpg';
  return `.${ext}`;
}

async function resolveImages(pptd, projectRoot) {
  const srcs = collectImageSrcs(pptd);
  const images = {}; // path -> Uint8Array
  const remap = new Map();

  await Promise.all(
    srcs.map(async (src, idx) => {
      let bytes;
      let ext = extFromSrc(src);
      if (/^(https?:\/\/|data:)/i.test(src)) {
        if (src.startsWith('data:')) {
          const m = /^data:([^;,]+)?(;base64)?,(.*)$/s.exec(src);
          if (!m) return;
          const ct = m[1] || '';
          ext = extFromSrc(src, ct);
          bytes = m[2]
            ? Buffer.from(m[3], 'base64')
            : Buffer.from(decodeURIComponent(m[3]));
        } else {
          const res = await fetch(src);
          if (!res.ok) {
            console.warn(`[warn] image fetch failed ${res.status}: ${src}`);
            return;
          }
          ext = extFromSrc(src, res.headers.get('content-type') || '');
          bytes = Buffer.from(await res.arrayBuffer());
        }
      } else {
        // local, relative to the project root and required to stay inside it
        const local = safeJoin(projectRoot, src.replace(/^file:\/\/+/, ''));
        if (!fs.existsSync(local)) {
          console.warn(`[warn] missing local image: ${src}`);
          return;
        }
        bytes = fs.readFileSync(local);
        ext = extFromSrc(src);
      }
      const key = `wasm-assets/img-${idx}${ext}`;
      images[key] = new Uint8Array(bytes);
      remap.set(src, key);
    }),
  );

  // rewrite src in place
  const rewrite = (obj) => {
    if (obj && typeof obj.src === 'string' && remap.has(obj.src)) {
      obj.src = remap.get(obj.src);
    }
  };
  for (const page of pptd.pages ?? []) {
    if (page.background?.type === 'image') rewrite(page.background);
    for (const el of page.elements ?? []) {
      if (el?.elementType === 'image') rewrite(el);
      if (el?.fill?.type === 'image') rewrite(el.fill);
    }
  }

  return images;
}

// ---------- offline signature (accepted by the patched WASM) ----------
function sha256Hex(text) {
  return crypto.createHash('sha256').update(text, 'utf8').digest('hex');
}

function offlineSignature(dataString) {
  return 'offline-bypass-' + sha256Hex(dataString).slice(0, 32);
}

// ---------- WASM glue (Node port of kimiDesign / wasm-bindgen) ----------
/**
 * wasm-bindgen hashes import names; upstream has shipped the JSON.stringify
 * binding under these two adjacent hashes. One of them must be present.
 */
const STRINGIFY_IMPORTS = [
  '__wbg_stringify_b54333f60f1e4ead',
  '__wbg_stringify_b54333f60f1e4dad',
];

/** Exports this glue calls directly; a renamed build must fail loudly here. */
const REQUIRED_WASM_EXPORTS = [
  'exportPPTDToPPTXBytes',
  'memory',
  '__wbindgen_add_to_stack_pointer',
  '__wbindgen_export', // malloc
  '__wbindgen_export2', // realloc
  '__wbindgen_export3', // throw
];

async function loadWasmExporter(wasmPath) {
  const wasmBytes = fs.readFileSync(wasmPath);
  let exportsRef;
  let memory;
  let cachedUint8;
  let cachedDataView;
  const textDecoder = new TextDecoder('utf-8', { ignoreBOM: true, fatal: true });
  const textEncoder = new TextEncoder();
  let heap = Array(1024).fill(undefined);
  heap.push(undefined, null, true, false);
  let heapNext = heap.length;
  let S = 0;

  function getUint8() {
    if (!cachedUint8 || cachedUint8.byteLength === 0) {
      cachedUint8 = new Uint8Array(memory.buffer);
    }
    return cachedUint8;
  }
  function getDataView() {
    if (
      !cachedDataView ||
      cachedDataView.buffer.detached === true ||
      (cachedDataView.buffer.detached === undefined &&
        cachedDataView.buffer !== memory.buffer)
    ) {
      cachedDataView = new DataView(memory.buffer);
    }
    return cachedDataView;
  }
  function addHeapObject(obj) {
    if (heapNext === heap.length) heap.push(heap.length + 1);
    const idx = heapNext;
    heapNext = heap[idx];
    heap[idx] = obj;
    return idx;
  }
  function takeObject(idx) {
    const ret = heap[idx];
    dropObject(idx);
    return ret;
  }
  function dropObject(idx) {
    if (idx < 1028) return;
    heap[idx] = heapNext;
    heapNext = idx;
  }
  function getObject(idx) {
    return heap[idx];
  }
  function isLikeNone(x) {
    return x == null;
  }
  function passStringToWasm(arg, malloc, realloc) {
    if (realloc === undefined) {
      const buf = textEncoder.encode(arg);
      const ptr = malloc(buf.length, 1) >>> 0;
      getUint8()
        .subarray(ptr, ptr + buf.length)
        .set(buf);
      S = buf.length;
      return ptr;
    }
    let len = arg.length;
    let ptr = malloc(len, 1) >>> 0;
    const mem = getUint8();
    let offset = 0;
    for (; offset < len; offset++) {
      const code = arg.charCodeAt(offset);
      if (code > 127) break;
      mem[ptr + offset] = code;
    }
    if (offset !== len) {
      if (offset !== 0) arg = arg.slice(offset);
      ptr = realloc(ptr, len, (len = offset + arg.length * 3), 1) >>> 0;
      const view = getUint8().subarray(ptr + offset, ptr + len);
      const ret = textEncoder.encodeInto(arg, view);
      offset += ret.written;
      ptr = realloc(ptr, len, offset, 1) >>> 0;
    }
    S = offset;
    return ptr;
  }
  function getStringFromWasm(ptr, len) {
    ptr = ptr >>> 0;
    return textDecoder.decode(getUint8().subarray(ptr, ptr + len));
  }
  function getArrayU8FromWasm(ptr, len) {
    ptr = ptr >>> 0;
    return getUint8().subarray(ptr / 1, ptr / 1 + len);
  }

  function handleError(f, args) {
    try {
      return f.apply(null, args);
    } catch (e) {
      exportsRef.__wbindgen_export3(addHeapObject(e));
    }
  }

  // Inspect the module's own import section before building the imports
  // object: which hash of the stringify binding this build actually wants.
  // Registering a name the module does not import is dead weight, and a
  // refreshed mirror with an unknown hash must stop and ask a human.
  const compiled = await WebAssembly.compile(wasmBytes);
  const importedNames = new Set(WebAssembly.Module.imports(compiled).map((entry) => entry.name));
  const stringifyImport = STRINGIFY_IMPORTS.find((name) => importedNames.has(name));
  if (!stringifyImport) {
    throw new Error(
      `patched WASM imports no known JSON.stringify binding (looked for ${STRINGIFY_IMPORTS.join(', ')}). ` +
        'The skill ships one specific build; a refreshed mirror needs its glue re-checked by hand.',
    );
  }

  const imports = {
    './pptd_wasm_bg.js': {
      __wbg___wbindgen_boolean_get_fa956cfa2d1bd751(arg0) {
        const v = getObject(arg0);
        const x = typeof v === 'boolean' ? v : undefined;
        return isLikeNone(x) ? 0xffffff : +!!x;
      },
      __wbg___wbindgen_is_function_1ff95bcc5517c252(arg0) {
        return typeof getObject(arg0) === 'function';
      },
      __wbg___wbindgen_is_null_ea9085d691f535d3(arg0) {
        return getObject(arg0) === null;
      },
      __wbg___wbindgen_is_object_a27215656b807791(arg0) {
        const val = getObject(arg0);
        return typeof val === 'object' && val !== null;
      },
      __wbg___wbindgen_is_undefined_c05833b95a3cf397(arg0) {
        return getObject(arg0) === undefined;
      },
      __wbg___wbindgen_number_get_394265ed1e1b84ee(arg0, arg1) {
        const obj = getObject(arg1);
        const val = typeof obj === 'number' ? obj : undefined;
        getDataView().setFloat64(arg0 + 8, isLikeNone(val) ? 0 : val, true);
        getDataView().setInt32(arg0 + 0, !isLikeNone(val), true);
      },
      __wbg___wbindgen_string_get_b0ca35b86a603356(arg0, arg1) {
        const obj = getObject(arg1);
        const val = typeof obj === 'string' ? obj : undefined;
        var ptr = isLikeNone(val)
          ? 0
          : passStringToWasm(val, exportsRef.__wbindgen_export, exportsRef.__wbindgen_export2);
        var len = S;
        getDataView().setInt32(arg0 + 4, len, true);
        getDataView().setInt32(arg0 + 0, ptr, true);
      },
      __wbg___wbindgen_throw_344f42d3211c4765(arg0, arg1) {
        throw new Error(getStringFromWasm(arg0, arg1));
      },
      __wbg_call_a6e5c5dce5018821() {
        return handleError(function (arg0, arg1, arg2) {
          return addHeapObject(getObject(arg0).call(getObject(arg1), getObject(arg2)));
        }, arguments);
      },
      __wbg_call_e3b662382210db98() {
        return handleError(function (arg0, arg1, arg2, arg3) {
          return addHeapObject(
            getObject(arg0).call(getObject(arg1), getObject(arg2), getObject(arg3)),
          );
        }, arguments);
      },
      __wbg_from_13e323c65fc8f464(arg0) {
        return addHeapObject(Array.from(getObject(arg0)));
      },
      __wbg_get_78f252d074a84d0b() {
        return handleError(function (arg0, arg1) {
          return addHeapObject(Reflect.get(getObject(arg0), getObject(arg1)));
        }, arguments);
      },
      __wbg_get_unchecked_6e0ad6d2a41b06f6(arg0, arg1) {
        return addHeapObject(getObject(arg0)[arg1 >>> 0]);
      },
      __wbg_instanceof_ArrayBuffer_4480b9e0068a8adb(arg0) {
        let result;
        try {
          result = getObject(arg0) instanceof ArrayBuffer;
        } catch {
          result = false;
        }
        return result;
      },
      __wbg_instanceof_Uint8Array_309b927aaf7a3fc7(arg0) {
        let result;
        try {
          result = getObject(arg0) instanceof Uint8Array;
        } catch {
          result = false;
        }
        return result;
      },
      __wbg_length_1f0964f4a5e2c6d8(arg0) {
        return getObject(arg0).length;
      },
      __wbg_length_370319915dc99107(arg0) {
        return getObject(arg0).length;
      },
      __wbg_new_cd45aabdf6073e84(arg0) {
        return addHeapObject(new Uint8Array(getObject(arg0)));
      },
      __wbg_new_da52cf8fe3429cb2() {
        return addHeapObject({});
      },
      __wbg_new_from_slice_77cdfb7977362f3c(arg0, arg1) {
        return addHeapObject(getArrayU8FromWasm(arg0, arg1).slice());
      },
      __wbg_prototypesetcall_4770620bbe4688a0(arg0, arg1, arg2) {
        Uint8Array.prototype.set.call(getArrayU8FromWasm(arg0, arg1), getObject(arg2));
      },
      __wbg_set_8535240470bf2500() {
        return handleError(function (arg0, arg1, arg2) {
          return Reflect.set(getObject(arg0), getObject(arg1), getObject(arg2));
        }, arguments);
      },
      // The JSON.stringify binding: wasm-bindgen hashes the import name, and
      // upstream has shipped this one under two adjacent hashes. Detect which
      // one this build actually imports (below) and register only that one —
      // an unknown hash is a mirror refresh that must stop and ask a human,
      // not silently register both and hope.
      // A plain function expression, not an arrow: `arguments` must be this
      // import call's arguments (the wasm passes them via apply), not the
      // enclosing loadWasmExporter's.
      [stringifyImport]: function () {
        return handleError(function (arg0) {
          return addHeapObject(JSON.stringify(getObject(arg0)));
        }, arguments);
      },
      __wbindgen_cast_0000000000000001(arg0) {
        return addHeapObject(arg0);
      },
      __wbindgen_cast_0000000000000002(arg0, arg1) {
        return addHeapObject(getStringFromWasm(arg0, arg1));
      },
      __wbindgen_object_drop_ref(arg0) {
        takeObject(arg0);
      },
    },
  };

  // instantiate(Module, …) resolves to the Instance itself (unlike the
  // bytes form, which resolves to a { module, instance } result object).
  const instance = await WebAssembly.instantiate(compiled, imports);
  exportsRef = instance.exports;
  // Fail loudly on a build this glue does not match, instead of a cryptic
  // TypeError deep inside the first call.
  const missingExports = REQUIRED_WASM_EXPORTS.filter((name) => exportsRef[name] === undefined);
  if (missingExports.length) {
    throw new Error(
      `patched WASM is missing expected export(s): ${missingExports.join(', ')} — ` +
        'this glue matches one specific wasm-bindgen build, not any patched WASM.',
    );
  }
  memory = exportsRef.memory;
  cachedUint8 = null;
  cachedDataView = null;

  function exportPPTDToPPTXBytes(pptd, options, signature) {
    const retptr = exportsRef.__wbindgen_add_to_stack_pointer(-16);
    try {
      const ptr0 = isLikeNone(signature)
        ? 0
        : passStringToWasm(
            signature,
            exportsRef.__wbindgen_export,
            exportsRef.__wbindgen_export2,
          );
      const len0 = S;
      exportsRef.exportPPTDToPPTXBytes(
        retptr,
        addHeapObject(pptd),
        addHeapObject(options),
        ptr0,
        len0,
      );
      const r0 = getDataView().getInt32(retptr + 0, true);
      const r1 = getDataView().getInt32(retptr + 4, true);
      const r2 = getDataView().getInt32(retptr + 8, true);
      if (r2) throw takeObject(r1);
      return takeObject(r0);
    } finally {
      exportsRef.__wbindgen_add_to_stack_pointer(16);
    }
  }

  return { exportPPTDToPPTXBytes };
}

// ---------- main ----------
async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || (!args.input && !args.json)) {
    console.log(`Usage: node export-pptd.mjs <pptd|projectDir> -o out.pptx [options]

Options:
  -o, --output PATH     output .pptx
  --transition fade|none
  --json PATH           pre-parsed project JSON (skips YAML; used by
                        scripts/export_pptx.py)
  --wasm PATH           path to patched pptd_wasm (default: the skill's
                        assets/editor copy)
  -h, --help            show this help

Env:
  PPTD_PYTHON           python executable used for the YAML fallback
`);
    process.exit(args.help ? 0 : 1);
  }

  let manifestPath;
  let pptd;
  if (args.json) {
    ({ project: pptd, manifestPath } = loadProjectFromJson(args.json));
    console.log('[1/5] load PPTD (pre-parsed)', manifestPath);
  } else {
    const parseYaml = await loadYaml();
    manifestPath = findManifest(args.input);
    console.log('[1/5] load PPTD', manifestPath);
    pptd = await loadProject(manifestPath, parseYaml);
  }
  const projectRoot = path.dirname(manifestPath);
  const output =
    args.output ||
    path.join(projectRoot, path.basename(manifestPath, '.pptd') + '.offline.pptx');

  console.log('[2/5] resolve images');
  // resolveImages rewrites src in place; the project object is used once and
  // discarded, so there is nothing to protect with a clone.
  const images = await resolveImages(pptd, projectRoot);
  console.log(`      ${Object.keys(images).length} image(s)`);

  console.log('[3/5] signature (offline)');
  const signature = offlineSignature(JSON.stringify(pptd));

  console.log('[4/5] load WASM', args.wasmPath);
  if (!fs.existsSync(args.wasmPath)) {
    throw new Error(
      `patched WASM not found: ${args.wasmPath}\n` +
        `Expected assets/editor/neo-ppt/assets/${CANONICAL_WASM_NAME} inside the skill.`,
    );
  }
  const { exportPPTDToPPTXBytes } = await loadWasmExporter(args.wasmPath);

  console.log('[5/5] export PPTX');
  const options = {
    fonts: [],
    customFonts: [],
    images,
    fileName: path.basename(output),
    slideTransition: {
      effect: args.transition,
      speed: 'fast',
    },
    chartImages: [],
  };

  const bytes = exportPPTDToPPTXBytes(pptd, options, signature);

  const outBuf = Buffer.from(bytes);
  fs.writeFileSync(output, outBuf);
  console.log('Wrote', output, `(${outBuf.length} bytes)`);

  // quick zip sanity
  if (outBuf[0] !== 0x50 || outBuf[1] !== 0x4b) {
    console.warn('[warn] output does not start with PK (not a ZIP/PPTX?)');
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
