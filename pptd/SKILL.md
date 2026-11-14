---
name: pptd
description: "Create, edit, replicate, validate, and export presentations with the private PPTD YAML format and its bundled WASM writer. Use whenever a slide deck, PowerPoint, PPT/PPTX, infographic, or poster is involved. Produces BOTH a self-contained editable PPTD project and a local .pptx by default; supports PPTD → PPTX only."
---

# PPTD

Author presentations in the private PPTD v2 YAML format and export locally with the bundled WASM writer. Resolve all paths below relative to this skill folder. **Node.js 26+** is required; no browser, runtime npm install or cloud service is needed.

Deliver **both** a self-contained editable project (`.pptd`, `pages/`, referenced assets) and the matching `.pptx`, with fade slide transitions, unless the user requests PPTD-only output.

This is **PPTD → PPTX only**: no PPTX importer, browser editor or independent full-slide layout engine. To edit/replicate an existing `.pptx`, obtain PDF/page images and rebuild it as PPTD. Preserve unrelated source during edits.

## 1. Establish the brief and read selectively

Infer the audience, language, page count, aspect ratio and design direction; ask only when missing choices materially affect the result. User content, brand rules and references take priority. Never fabricate facts, data, citations or missing source material.

- Read **`references/pptd.md`** for every project, then only the linked shared types and element contracts you use. Charts have their own reading index. Do not invent fields or substitute another schema.
- Read **`references/slides_categories.md`** for the design baseline. For self-directed design, add one matching scenario guide from its router.
- Use a preset **only when explicitly named**: read `references/design_system/README.md`, the named signature, and its linked category baseline or shared file. Do not mix or auto-select presets. Signatures override visual defaults, not evidence boundaries.
- For posters/infographics, read `references/general-poster.md`; for font selection/custom fonts/warnings, `references/fonts.md`; for shape names/adjustments, `references/shapes.md`.

## 2. Build a portable project

```text
deck/
  deck.pptd
  pages/
    01-cover.page
    02-content.page
  media/                 # when used
```

Keep page/media/custom-font paths relative to the manifest and inside its directory. Localize remote images and authorized font sources before claiming self-contained delivery; a cache or embedded PPTX asset does not make the editable source portable. Prefer bundled or licensed project-local fonts. Embedding permission alone does not authorize distributing loose system fonts.

Give each page a reader task, then choose composition, hierarchy and imagery that explain its content. Keep text, vectors, tables and ordinary charts editable where practical; crop images rather than distort them. Use literal `\(...\)` formulas in text block scalars for editable Office Math. Text uses the documented rich-text tags and decoded HTML entities; close tags and quote attribute values. Add notes only when requested, and element animations only when requested or useful for live delivery.

## 3. Validate and export

```bash
node scripts/export.mjs /absolute/path/deck/deck.pptd \
  --output /absolute/path/deck/deck.pptx
```

A project directory is accepted when it contains exactly one manifest. Options: `--force` replaces an output; `--transition none` disables fade; repeat `--font-dir PATH` to search local font directories; `--no-embed-fonts` deliberately leaves fonts external; `--offline` forbids remote media and uncached Google Fonts requests.

Export validates the schema/assets, prepares fonts/icons/formulas/charts, runs WASM, patches font bindings/table image fills/transitions, and verifies XML, relationships, media and ZIP integrity. Fix errors; never bypass an invalid formula or unknown chart/icon with a placeholder. Review warnings: intentional bleed may be acceptable, but substitutions, unavailable styles and non-embeddable fonts need correction or disclosure, not an “exact match” claim.

For PPTD-only delivery or a standalone check:

```bash
node scripts/validate.mjs /absolute/path/deck/deck.pptd
```

`heatmap`, `treemap`, `sunburst` and `sankey` become **SVG pictures**, with editable data retained in PPTD and SVG metadata—not native PowerPoint “Edit Data” charts. Selected font outlines freeze their labels without flattening the slide; unsupported complex/bidi shaping fails explicitly. SVG-capable playback is required; there is no raster fallback. Other chart types keep native export.

## 4. Review and deliver honestly

Always review source layout, text length, hierarchy, contrast, alignment, cropping, layering, sources and deck rhythm. When local PowerPoint/LibreOffice and optional Python 3 + PyMuPDF are available:

```bash
python scripts/render_slides.py /absolute/path/deck/deck.pptx \
  --output /absolute/path/deck/.qa-images --if-available
```

The helper prefers Windows PowerPoint, otherwise LibreOffice; both render through PDF to preserve embedded fonts. Use `--force` only to replace this helper's prior renders. Do not install/start a browser for QA.

- **`rendered`**: inspect every page image for fonts, overflow, occlusion, image fit, chart labels, tables and formulas. Repair the PPTD source, re-export and re-render before delivery.
- **`skipped`**: continue source/package checks and disclose that rendered visual review was not performed. An available renderer's failure is not a pass.

Link the project and `.pptx` with absolute local paths, and disclose unresolved warnings/limitations. Valid XML, a ZIP or PNG existence is not visual acceptance or proof of identical rendering/playback in PowerPoint, WPS or Keynote.
