# Local offline WASM PPTX exporter

- `export-pptd.mjs` — Node entry (patched WASM writer, no network, no cookie)
- Single canonical patched WASM, shipped with the skill:  
  `../../assets/editor/app/pptd_wasm_bg-DPPWdROu.wasm`
- Used by `../export_pptx.py` as the **default** export path

```bash
# wasm path resolves automatically from the skill tree
node export-pptd.mjs /path/to/project -o out.pptx

# or pass it explicitly
node export-pptd.mjs /path/to/project -o out.pptx \
  --wasm ../../assets/editor/app/pptd_wasm_bg-DPPWdROu.wasm
```
