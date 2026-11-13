# pptd — repository development notes

The distributable unit is `pptd/`. This directory holds only repository build tooling, focused regressions, fixtures and review helpers. Generated evidence belongs under `.artifacts/pptd/`.

## Architecture

Everything in `pptd/scripts/` runs inside a single Node.js process with zero external runtime dependencies.

```text
pptd/scripts/
  export.mjs          public CLI: read, prepare, WASM export, patch, verify
  validate.mjs        structural check only
  lib/deck/           yaml.mjs, contract.mjs, schema.mjs, project.mjs
  lib/prepare/        font_data, fonts, icons, media, images, formulas, charts, svg_text
  lib/pptx/           writer.mjs, zip.mjs, patch.mjs, verify.mjs
pptd/assets/
  vendor/             echarts, fontkit, katex, xmldom, yaml (+ licenses/)
  fonts/ icons/       generated catalogs (see build_vendor.mjs / build_fonts.py)
  wasm/               the single bundled writer
```

- `lib/deck/schema.mjs` is the only schema implementation: shared types, every element
  type, sparse merged table grids with style inheritance, chart channel/mapping rules and
  animations.
- `lib/prepare/media.mjs` is the single image byte-identity and intrinsic dimension
  parser shared by media preparation, native table image fills, and package verification.
- `lib/pptx/zip.mjs` implements ZIP reading, updating and IEEE CRC-32 verification on
  `node:zlib`; `patch.mjs` and `verify.mjs` reuse the vendored `@xmldom/xmldom`.
- `render_slides.py` and `render_powerpoint.ps1` are repository-only review helpers; they
  are not distributed with the skill and never run during export.

## Rebuild runtime assets

Development dependencies live at the repository root.

```bash
npm ci
npm run pptd:build-assets
```

- `build_vendor.mjs` vendors every runtime JavaScript file into `pptd/assets/vendor/`:
  the published ECharts standalone ESM build (unmodified), esbuild bundles of katex,
  xmldom, yaml and fontkit, and their verified upstream notices. Each bundle is checked
  for external imports before it is written; a missing supplemental license is restored
  from its pinned authoritative URL and hash-checked, never guessed.
- `build_fonts.py` vendors licensed original static TTFs with OFL attribution. Runtime
  EOT conversion needs only Node stdlib. Do not restore uncleared historical font files or
  redistribute loose Windows fonts.

After any renderer/formula/font update, inspect actual local Office output when available. Build tools and dependencies are never copied into the skill.

## Necessary regression checks

```bash
npm run test:pptd
python -B tools/quick_validate.py
git diff --check
```

`test:pptd` runs the unified Node suite (`deck`, `exporter`, `advanced-charts`, `pptx`).
No regression needs Python, PyYAML, a browser, network or Office installation.
Add tests only for a demonstrated regression or a critical new path that otherwise permits
silent damage.

## Conditional PowerPoint/LibreOffice review

```bash
node pptd/scripts/export.mjs tools/pptd/tests/fixtures/advanced-charts -o .artifacts/pptd/charts.pptx --force --offline
python -B tools/pptd/render_slides.py .artifacts/pptd/charts.pptx -o .artifacts/pptd/charts-powerpoint --if-available --force
```

Review every page PNG for font identity/styles, text fit, chart labels, image crop, tables, formulas and layering. After fixing source or adapter problems, export/render again. Compare against frozen reference outputs or inspect the underlying SVG/XML; no browser is required. PowerPoint fixed-format PDF preserves embedded-font playback; direct PNG export does not and must not be used as a font-fidelity oracle. Repository QA dependencies are recorded in `requirements-review.txt` at the root; they are not mandatory PPTX-export dependencies. If dependencies are absent, report `skipped`; do not claim a visual review. Render failures must be diagnosed rather than called passes.

The ECharts SVG adapters merge dashed/dotted treemap edges from `ecmeta_data_index` geometry and replace central text baselines with explicit offsets because PowerPoint ignores `dominant-baseline`. A chart picture stays bare; native `<id>-background`/`<id>-frame` rectangles own fill/border/shadow and mirror animations. The writer's `chartImages` input is PNG-only: never put SVG bytes there.

## Invariants

- **Byte-stable writer:** exactly one distributed WASM, SHA-256 `589b362a444824c948f21ae99cdc32958c83b28e47a296d4f5905c76b04e0e6e`. An explicit alternate build still needs real export verification.
- **One format contract:** `lib/deck/` owns the private v2 schema and the YAML 1.2 reading. Maintain project path containment and preserve unrelated source during edits/export.
- **No silent degradation:** unknown chart/icon data, malformed formulas, broken media/XML and missing animation targets are errors, not placeholder success.
- **Fonts are data, not just names:** preserve Windows style-linked family identity; respect fsType; group true RIBBI variants; disclose substitutions/unavailable styles/external fonts. An embedded ZIP part is not proof of rendering fidelity.
- **Editable source:** keep native text, vectors, tables, ordinary charts and OMML. Advanced charts remain SVG pictures with editable source data and original definitions in metadata; no native Edit Data or PNG fallback is claimed.
- **Single transition owner:** export postprocessing writes exactly one root fade after cSld/optional clrMapOvr and before timing/extLst.
- **Honest conditional QA:** neither Office nor PyMuPDF is mandatory for export. Never start/install a browser. Structural checks and successful rendering are not automatic visual acceptance or cross-application compatibility guarantees.
- **Design coverage:** preserve seven scenario guides and all 44 indexed presets.
- **Clean distribution:** runtime helpers/assets only in `pptd/`; tests/build tools only here; no `__pycache__`, generated decks or review PNGs in the distributed unit.
