# PPTD WASM writer

`pptd_wasm_bg.wasm` is the sole bundled writer for the private PPTD v2 format. Its source is unavailable; treat the binary and `scripts/wasm-exporter.mjs` as one version-locked unit.

- Original filename: `pptd_wasm_bg-DPPWdROu.wasm`
- Size: 788074 bytes
- SHA-256: `589b362a444824c948f21ae99cdc32958c83b28e47a296d4f5905c76b04e0e6e`
- Public export used by the adapter: `exportPPTDToPPTXBytes`

Do not replace the binary with another build without checking its wasm-bindgen imports and exports and running a real PPTD → PPTX export. `export_pptx.py --wasm` exists for that explicit compatibility testing. The browser editor and its fonts are not runtime dependencies of this core.
