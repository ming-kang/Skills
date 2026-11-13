import fs from 'node:fs';

const STRINGIFY_IMPORTS = [
  '__wbg_stringify_b54333f60f1e4ead',
  '__wbg_stringify_b54333f60f1e4dad',
];

const REQUIRED_WASM_EXPORTS = [
  'exportPPTDToPPTXBytes',
  'memory',
  '__wbindgen_add_to_stack_pointer',
  '__wbindgen_export',
  '__wbindgen_export2',
  '__wbindgen_export3',
];

export async function loadWasmExporter(wasmPath) {
  const wasmBytes = fs.readFileSync(wasmPath);
  let exportsRef;
  let memory;
  let cachedUint8;
  let cachedDataView;
  const textDecoder = new TextDecoder('utf-8', { ignoreBOM: true, fatal: true });
  const textEncoder = new TextEncoder();
  const heap = Array(1024).fill(undefined);
  heap.push(undefined, null, true, false);
  let heapNext = heap.length;
  let stringLength = 0;

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
      (cachedDataView.buffer.detached === undefined && cachedDataView.buffer !== memory.buffer)
    ) {
      cachedDataView = new DataView(memory.buffer);
    }
    return cachedDataView;
  }

  function addHeapObject(object) {
    if (heapNext === heap.length) heap.push(heap.length + 1);
    const index = heapNext;
    heapNext = heap[index];
    heap[index] = object;
    return index;
  }

  function takeObject(index) {
    const object = heap[index];
    dropObject(index);
    return object;
  }

  function dropObject(index) {
    if (index < 1028) return;
    heap[index] = heapNext;
    heapNext = index;
  }

  function getObject(index) {
    return heap[index];
  }

  function isLikeNone(value) {
    return value == null;
  }

  function passStringToWasm(value, malloc, realloc) {
    if (realloc === undefined) {
      const buffer = textEncoder.encode(value);
      const pointer = malloc(buffer.length, 1) >>> 0;
      getUint8().subarray(pointer, pointer + buffer.length).set(buffer);
      stringLength = buffer.length;
      return pointer;
    }
    let length = value.length;
    let pointer = malloc(length, 1) >>> 0;
    const memoryBytes = getUint8();
    let offset = 0;
    for (; offset < length; offset++) {
      const code = value.charCodeAt(offset);
      if (code > 127) break;
      memoryBytes[pointer + offset] = code;
    }
    if (offset !== length) {
      if (offset !== 0) value = value.slice(offset);
      pointer = realloc(pointer, length, (length = offset + value.length * 3), 1) >>> 0;
      const view = getUint8().subarray(pointer + offset, pointer + length);
      const result = textEncoder.encodeInto(value, view);
      offset += result.written;
      pointer = realloc(pointer, length, offset, 1) >>> 0;
    }
    stringLength = offset;
    return pointer;
  }

  function getStringFromWasm(pointer, length) {
    return textDecoder.decode(getUint8().subarray(pointer >>> 0, (pointer >>> 0) + length));
  }

  function getArrayU8FromWasm(pointer, length) {
    return getUint8().subarray(pointer >>> 0, (pointer >>> 0) + length);
  }

  function handleError(callback, args) {
    try {
      return callback.apply(null, args);
    } catch (error) {
      exportsRef.__wbindgen_export3(addHeapObject(error));
      return undefined;
    }
  }

  const compiled = await WebAssembly.compile(wasmBytes);
  const importedNames = new Set(WebAssembly.Module.imports(compiled).map((entry) => entry.name));
  const stringifyImport = STRINGIFY_IMPORTS.find((name) => importedNames.has(name));
  if (!stringifyImport) {
    throw new Error(
      `WASM imports no known JSON.stringify binding (${STRINGIFY_IMPORTS.join(', ')}); ` +
        'this adapter is version-locked to the bundled writer',
    );
  }

  const imports = {
    './pptd_wasm_bg.js': {
      __wbg___wbindgen_boolean_get_fa956cfa2d1bd751(arg0) {
        const value = getObject(arg0);
        const boolean = typeof value === 'boolean' ? value : undefined;
        return isLikeNone(boolean) ? 0xffffff : +!!boolean;
      },
      __wbg___wbindgen_is_function_1ff95bcc5517c252(arg0) {
        return typeof getObject(arg0) === 'function';
      },
      __wbg___wbindgen_is_null_ea9085d691f535d3(arg0) {
        return getObject(arg0) === null;
      },
      __wbg___wbindgen_is_object_a27215656b807791(arg0) {
        const value = getObject(arg0);
        return typeof value === 'object' && value !== null;
      },
      __wbg___wbindgen_is_undefined_c05833b95a3cf397(arg0) {
        return getObject(arg0) === undefined;
      },
      __wbg___wbindgen_number_get_394265ed1e1b84ee(arg0, arg1) {
        const value = getObject(arg1);
        const number = typeof value === 'number' ? value : undefined;
        getDataView().setFloat64(arg0 + 8, isLikeNone(number) ? 0 : number, true);
        getDataView().setInt32(arg0, !isLikeNone(number), true);
      },
      __wbg___wbindgen_string_get_b0ca35b86a603356(arg0, arg1) {
        const value = getObject(arg1);
        const string = typeof value === 'string' ? value : undefined;
        const pointer = isLikeNone(string)
          ? 0
          : passStringToWasm(string, exportsRef.__wbindgen_export, exportsRef.__wbindgen_export2);
        getDataView().setInt32(arg0 + 4, stringLength, true);
        getDataView().setInt32(arg0, pointer, true);
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
        try {
          return getObject(arg0) instanceof ArrayBuffer;
        } catch {
          return false;
        }
      },
      __wbg_instanceof_Uint8Array_309b927aaf7a3fc7(arg0) {
        try {
          return getObject(arg0) instanceof Uint8Array;
        } catch {
          return false;
        }
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

  const instance = await WebAssembly.instantiate(compiled, imports);
  exportsRef = instance.exports;
  const missingExports = REQUIRED_WASM_EXPORTS.filter((name) => exportsRef[name] === undefined);
  if (missingExports.length) {
    throw new Error(`WASM is missing expected exports: ${missingExports.join(', ')}`);
  }
  memory = exportsRef.memory;
  cachedUint8 = null;
  cachedDataView = null;

  function exportPPTDToPPTXBytes(project, options, signature) {
    const returnPointer = exportsRef.__wbindgen_add_to_stack_pointer(-16);
    try {
      const signaturePointer = isLikeNone(signature)
        ? 0
        : passStringToWasm(
            signature,
            exportsRef.__wbindgen_export,
            exportsRef.__wbindgen_export2,
          );
      const signatureLength = stringLength;
      exportsRef.exportPPTDToPPTXBytes(
        returnPointer,
        addHeapObject(project),
        addHeapObject(options),
        signaturePointer,
        signatureLength,
      );
      const result0 = getDataView().getInt32(returnPointer, true);
      const result1 = getDataView().getInt32(returnPointer + 4, true);
      const result2 = getDataView().getInt32(returnPointer + 8, true);
      if (result2) throw takeObject(result1);
      return takeObject(result0);
    } finally {
      exportsRef.__wbindgen_add_to_stack_pointer(16);
    }
  }

  return { exportPPTDToPPTXBytes };
}
