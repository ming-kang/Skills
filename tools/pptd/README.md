# PPTD development

The distributable unit is `pptd/`: runtime instructions, helpers and reusable assets only. Build tooling/tests live here, dev dependencies at the root, and generated review evidence under `.artifacts/pptd/`.

## Ownership

```text
pptd/scripts/
  export.mjs            CLI and pipeline: read → prepare → write → patch → verify
  validate.mjs          standalone structural/semantic/local-asset validation
  render_slides.py      optional Office → PDF → PyMuPDF PNG review
  render_powerpoint.ps1 scoped Windows COM bridge
  lib/core/            XML/namespaces, CSS/rich text, media, HTTP, catalogs, config traversal
  lib/deck/            YAML/paths/project, page+animation schema, shared styles, tables, charts, text holders
  lib/prepare/         fonts/metadata, icons/images, formulas, chart SVGs/glyph outlines
  lib/pptx/            version-locked writer, ZIP, package editing, OOXML patching/verification
pptd/assets/
  vendor/              tailored ECharts/fontkit + KaTeX/xmldom/YAML (+ licenses/)
  fonts/ icons/        licensed offline data
  shapes.json          generated preset geometry metadata
  wasm/                one immutable writer
```

- `deck/schema.mjs` owns page/element geometry and animations; `style.mjs`, `table.mjs`, `chart.mjs` own their domain contracts. Do not create a second validation path.
- `tableCells` is the single sparse-grid/style expansion for validation, fonts and OOXML image fills. Cells retain logical positions, source holders and diagnostic labels.
- `readContent` builds one per-deck plan of effective text styles, sparse table cells, text DOMs and formula tokens. Fonts, formulas and table image patching consume that plan without re-parsing text or re-expanding tables. The canonical deck is one plain-data object; the plan never reaches WASM.
- `core/markup.mjs` owns the text grammar, including entities, literal comparisons, loose inline text and multiline formulas. All text is serialized into well-formed blocks before export; no separate HTML lexer or font-dependent rewriting path remains. CSS splitting honors quoted values and URL parentheses. Inline CSS is a closed contract: the supported declarations per element are enumerated, anything else fails with that list instead of being dropped, `$theme` colors are resolved to HEX (the writer only understands tokens in element fields), `list-style-type` keywords are mapped to real bullet glyphs, and `<br>` becomes a paragraph split because the writer has no `<a:br/>`. `export.mjs` materializes `Cell.textStyle` and `manifest.metadata` onto the writer's own fields.
- `core/media.mjs` owns byte identity/dimensions; `core/catalog.mjs` shares icon data; `walkObjects` traverses config, never chart rows/filter data. HTTP payloads are bounded while streaming, not after allocation.
- `PptxPackage` distinguishes cached reads from edits and keeps binary/XML replacements coherent. ZIP reads are cached, XML is parsed once during verification, and CRC checks also cover unparsed binary parts without retaining decoded font payloads.
- Font descriptors expose lazy original SFNT/TTC bytes, shared with embedding. `svg_text.mjs` is a chart-label adapter, not a general SVG/CSS layout engine: explicit px/family, standalone text, known anchor/baseline and monochrome glyphs only. Unexpected renderer structure/CSS, missing glyphs and complex/bidi shaping fail closed.

## Rebuild assets

```bash
npm ci
npm run pptd:build-assets
```

- `build_vendor.mjs` bundles only heatmap/treemap/sunburst/sankey, SVG, grid, title and colorbar from ECharts. fontkit registers SFNT/TTC containers, omitting unused WOFF/WOFF2/DFont and Brotli. Its pinned source build preserves legacy three-argument `@cache` decorators and inlines Parcel's three Unicode trie reads. Do not switch to TC39 decorator semantics or strip shaping/subsetting imports by patching upstream code.
- Every bundle is checked for external imports; notices are derived from actual inputs. Missing licenses are restored only from pinned authoritative sources and verified hashes. Preserve source attributions and Unicode/base64 notices.
- `build_fonts.mjs` rebuilds `.ttf.gz` storage from the catalog's pinned sources, reusing intact local payloads offline. Complete TTF bytes and OFL attribution are preserved. `build_shapes.mjs` derives 177 shapes/adjustment arities; the Font Awesome catalog is pre-vendored, not rebuilt by this command.
- Binary and `writer.mjs` are one version-locked unit verified by wasm-bindgen imports/exports.

## Checks

```bash
npm run test:pptd
python -B tools/quick_validate.py
git diff --check
```

The Node suite covers deck/exporter/advanced-chart/PPTX paths plus shared-contract regressions: sparse styles, rich text/duplicate formulas, Unicode safety, bounded downloads, coherent package caches, legacy fontkit decorators and writer override validation. It needs no network, browser, Office or Python. Add tests for demonstrated regressions or critical paths that could otherwise silently damage output.

After renderer/font/formula changes, review actual Office output when available:

```bash
node pptd/scripts/export.mjs tools/pptd/tests/fixtures/advanced-charts -o .artifacts/pptd/charts.pptx --force --offline
python -B pptd/scripts/render_slides.py .artifacts/pptd/charts.pptx -o .artifacts/pptd/charts-review --if-available --force
```

Inspect every page's fonts, fit, labels, crop, tables, formulas and layering; compare SVG/XML and frozen outputs where appropriate. ECharts source bundles can differ slightly from published monolithic builds in SSR text-width estimates, so do not assert pixel identity from package tests. Direct PowerPoint PNG export is not a font-fidelity oracle. `skipped` is an environment limit, not a review; render failures are not passes.

## Keep these contracts

- Preserve project containment, source files and unrelated output; export failure must not replace a good PPTX.
- Unknown charts/icons, malformed formulas/media/XML and broken animation targets are errors, never placeholder success.
- Font names are insufficient: preserve actual Windows family identity, fsType and RIBBI style bindings; disclose external/synthetic/substituted faces.
- Native text, vectors, tables, ordinary charts and OMML stay editable. Advanced charts retain editable source/metadata; SVG labels freeze as paths, while native frame rectangles own fill/border/shadow and mirrored animations. `chartImages` is PNG-only in this writer.
- Write exactly one root fade after cSld/optional clrMapOvr and before timing/extLst, or remove transitions explicitly.
- Keep all 44 preset IDs and seven scenario guides. Baselines/shared signatures are linked, not copied into every preset. `references/pptd.md` is the short core/index; element contracts contain the full fields/examples.
- No generated decks, browser tooling, development deps or `__pycache__` in the distributed skill. Never commit/push unless asked.
