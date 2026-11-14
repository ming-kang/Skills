# PPTD WASM writer

`pptd_wasm_bg.wasm` is the sole bundled writer for the private PPTD v2 format. Treat the binary and `scripts/lib/pptx/writer.mjs` as one version-locked unit.

- Original filename: `pptd_wasm_bg-DPPWdROu.wasm`
- Size: 788074 bytes
- Public export used by the adapter: `exportPPTDToPPTXBytes`

Do not replace the binary with another build without checking its wasm-bindgen imports and exports and running a real PPTD → PPTX export. `node scripts/export.mjs --wasm` exists for that explicit compatibility testing. The browser editor and its fonts are not runtime dependencies of this core.
