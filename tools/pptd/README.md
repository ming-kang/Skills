# pptd — repository development notes

The distributable skill is the repository-root `pptd/` folder. This directory contains repository-only build tooling, development tests, and fixtures.

## Runtime map

```text
pptd/
  SKILL.md
  assets/wasm/pptd_wasm_bg.wasm  # sole private writer binary
  assets/charts/                 # standalone ECharts ESM bundle + upstream notices
  references/                    # format + all design guides and 44 presets
  scripts/
    validate_pptd.py             # public structural-validation CLI
    export_pptx.py               # public validation + export CLI
    pptd_deck.py                 # YAML loading, project paths, structural checks
    pptd_pptx.py                 # transition patching + PPTX verification
    pptd_common.py               # shared error, path, logging, process helpers
    export_pptd.mjs              # JSON handoff, media resolution, WASM invocation
    advanced-charts.mjs          # advanced chart → framed SVG picture, preserving source metadata
    chart-data.mjs               # chart columns, hierarchy totals, DAG validation
    chart-style.mjs              # palette, theme tokens, gradients, label contrast, number formats
    wasm-exporter.mjs            # version-locked wasm-bindgen adapter
```

The Python wrapper owns YAML parsing and slide-transition policy. It passes pre-parsed JSON to Node, so the installed skill needs no adjacent `node_modules`. Node resolves media, renders advanced charts using the bundled SVG-only SSR path, and invokes the private writer. Browser editing, full-slide image export, browser automation, and process-reaping code are intentionally outside the core skill.

## Chart renderer asset

`build_charts.mjs` copies the published ECharts standalone ESM bundle and its licenses/notices into `pptd/assets/charts/`. The build dependency is pinned at the repository root; neither package resolution nor npm is used by the installed renderer. Two SVG adapters depend on ECharts 6's SSR output: dashed/dotted treemap borders are drawn as one merged edge grid from the node rectangles (`ecmeta_data_index` paths), and every `<text>` gets an explicit baseline offset in place of `dominant-baseline="central"`, which PowerPoint ignores. Review real PowerPoint renders when updating the bundle (see below).

```bash
npm ci
npm run pptd:build-charts
```

`heatmap`, `treemap`, `sunburst`, and `sankey` are prepared after image resolution and before the existing signature/WASM call. They become normal SVG image elements in the in-memory project; the original files are not rewritten. The writer's `chartImages` interface is PNG-only, so it must not receive SVG bytes. The picture itself stays bare and transparent. The chart frame is drawn by native rectangles: `<id>-background` below it (fill, plus shadow) and `<id>-frame` above it (border, plus shadow when there is no fill). Picture shadows would be traced from the SVG's alpha (every label and cell), the writer splits picture borders into an unanimated shape, and nested SVG images are not consistently displayed by Office. Frame layers mirror the chart's animations with `withPrevious` triggers, except `fill-color`/`color-pulse`, which would recolor a frame.

## Tests

```text
tools/pptd/
  tests/
    test_export_pptx.py
    fixtures/minimal/            # one text slide
    fixtures/qa-deck/            # three slides + local media
    fixtures/advanced-charts/    # all four advanced charts, frames, animations + a native bar
  tests-node/
    exporter.test.js             # project/media normalization without a browser
    advanced-charts.test.js      # SVG text baselines, frame layers, palette, borders, labels
  render_powerpoint.ps1          # Windows-only: render a .pptx's slides to PNG with PowerPoint
```

Run:

```bash
npm run test:pptd
node --test "tools/pptd/tests-node/*.test.js"
python -B -m unittest discover -s tools/pptd/tests -p "test_*.py"
```

The Python suite includes real Node + WASM exports and skips those cases only when Node is unavailable. No test needs a browser or network access.

### PowerPoint review of advanced charts

Structural tests cannot show how Office's SVG renderer draws a chart. After changing `advanced-charts.mjs`, `chart-style.mjs`, or the ECharts bundle, export the fixture and look at PowerPoint's own render (Windows with PowerPoint installed):

```bash
python pptd/scripts/export_pptx.py tools/pptd/tests/fixtures/advanced-charts -o .artifacts/pptd/charts.pptx --force
powershell -NoProfile -ExecutionPolicy Bypass -File tools/pptd/render_powerpoint.ps1 -Pptx .artifacts/pptd/charts.pptx -OutDir .artifacts/pptd/charts-powerpoint
```

Compare text placement with the same SVGs (`ppt/media/*.svg`) opened in a browser; labels should sit within about 1px of the browser render.

## Invariants

- **Byte-stable WASM.** The canonical binary is `pptd/assets/wasm/pptd_wasm_bg.wasm`, SHA-256 `589b362a444824c948f21ae99cdc32958c83b28e47a296d4f5905c76b04e0e6e`. Keep exactly one `.wasm` in the distributed skill. The adapter expects this build's imports and exports; a replacement requires real export testing.
- **Format compatibility.** `references/pptd.md` is the authoritative private v2 contract. Do not invent fields or weaken project-path containment to accommodate a deck.
- **No browser fallback.** Deck, dependency, and export errors are reported directly. The runtime does not auto-install packages or start background processes.
- **Advanced charts are SVG pictures.** Preserve native export for the other chart types. Never silently feed an unsupported advanced series to the WASM chart writer. Retain the original chart definition in SVG metadata and keep element IDs/animation targets intact. Keep the picture bare (frame styling on native shapes) and text baselines explicit. Playback requires SVG support; do not claim native Edit Data or a PNG fallback.
- **Single transition owner.** `export_pptx.py` patches and verifies root-level slide transitions after WASM export. `p:transition` must follow `cSld`/optional `clrMapOvr` and precede `timing`/`extLst`.
- **Honest verification.** ZIP/XML checks do not establish rendering fidelity or application compatibility. The core does not claim font embedding or rendered visual QA.
- **Design reference coverage.** Keep all seven scenario guides and all 44 presets. `references/design_system/README.md` maps each theme ID to `<theme-id>.md` beside the index; update it whenever a preset is added, removed, or renamed.
- **Clean distribution.** Runtime helpers and assets stay inside `pptd/`; repository-only tests stay here. Remove `__pycache__` and generated exports before packaging.
