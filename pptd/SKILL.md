---
name: pptd
description: "Create, design and export presentations in the PPTD format. Use when building slides from a brief or document or working with .pptd projects."
---

# PPTD

Author presentations in the PPTD v2 YAML format and export locally to `.pptx` (requires **Node.js 26+**). Resolve `scripts/` and `references/` below relative to this skill folder.

Deliver **both** a self-contained editable project (`.pptd`, `pages/`, referenced assets) and the matching `.pptx` with fade transitions, unless the user asks for PPTD-only output. Export is one-way (**PPTD → PPTX**). When given a standalone `.pptx` without PPTD source, rebuild visual or structural references in PPTD for redesigns, or use a direct `.pptx` workflow for small in-place edits.

## 1. Plan and read selectively

Infer audience, language, page count, aspect ratio and design direction; ask only when missing choices materially affect the output. User content, brand rules and references take priority. Never fabricate facts, data, citations or missing source material.

- Always read **`references/pptd.md`**, then only the linked shared types and element contracts you use (charts have their own reading index). Do not invent fields.
- Read **`references/slides_categories.md`** for the design baseline. For self-directed design, add one matching scenario guide from its router.
- Use a preset **only when explicitly named**: read `references/design_system/README.md`, that preset, and its linked baseline/shared file. Never mix or auto-select presets.
- Load on demand: `references/general-poster.md` (posters/infographics), `references/fonts.md` (fonts/warnings), `references/shapes.md` (shapes beyond `elements/shape.md`).

## 2. Build a portable project

Use the layout in `references/pptd.md` (**Project paths**): a `deck.pptd` manifest, `pages/*.page`, optional `media/`. Keep every page, media and custom-font path relative to the manifest and inside its directory.

For dependable portability:

- Prefer bundled or project-local fonts for predictable offline export and portability.
- For fully self-contained decks without a corporate font requirement, choose explicit bundled families (for example `{latin: Liter, ea: Noto Sans SC}`) instead of relying on unavailable system defaults.
- Localize remote images and font files before calling the source self-contained; a cache or `.pptx` copy does not make `.pptd` source portable.
- Give each page a clear reader task and visual hierarchy. Keep text, vectors, tables and ordinary charts editable where practical; crop images instead of distorting them.
- Write literal `\(...\)` inside text block scalars for editable Office Math. Use only documented rich-text tags, quoted attributes and HTML entities; unsupported inline CSS and unsafe links are errors. `$theme` colors resolve automatically.
- Add notes or element animations only when requested or clearly helpful for live delivery.

## 3. Validate, export and inspect warnings

Normal delivery needs only the export gate below; it already performs structural and asset validation before writing:

```bash
node scripts/export.mjs /absolute/path/deck/deck.pptd \
  --output /absolute/path/deck/deck.pptx
```

For PPTD-only output, early iteration or font-warning inspection without building a `.pptx`:

```bash
node scripts/validate.mjs /absolute/path/deck/deck.pptd --check-fonts
```

A project directory works when it contains one manifest. `node scripts/export.mjs --help` and `node scripts/validate.mjs --help` list every option. Useful variants:

```bash
# replace an existing successful export only after a successful new build
node scripts/export.mjs deck/deck.pptd -o deck/deck.pptx --force

# reproducible offline validation/export; remote images/fonts become errors
node scripts/export.mjs deck/deck.pptd -o deck/deck.pptx --offline

# remove transitions when a user explicitly objects to motion
node scripts/export.mjs deck/deck.pptd -o deck/deck.pptx --transition none
```

Export validates schema and assets, prepares icons/fonts/formulas/charts, builds `.pptx`, and verifies XML, relationships, media and ZIP integrity. Fix errors—never substitute placeholders for broken formulas, charts or icons. Review warnings carefully: intentional bleed may be fine, but font substitutions, missing styles or non-embeddable fonts need fixing or honest disclosure.

`heatmap`, `treemap`, `sunburst` and `sankey` export as **SVG pictures** (retaining source data in PPTD and SVG metadata, with labels frozen as glyph paths; requires SVG-capable playback, no raster fallback). Other chart types stay native.

## 4. Visual review and honest delivery

Always review layout, text length, hierarchy, contrast, alignment, cropping, layering, sources and export warnings. Fix visual issues in the **PPTD source** and re-export so `.pptd` and `.pptx` stay in sync.

Use whatever inspection or rendering capability the current environment already provides; do not make one office suite or extra package a hard QA requirement. Depending on what is available, examples include opening or automating PowerPoint, converting through LibreOffice, using an existing PDF/PNG preview path, inspecting the package structure, or the bundled helper:

```bash
python scripts/render_slides.py /absolute/path/deck/deck.pptx \
  --output /absolute/path/deck/rendered --if-available
```

- `--force` replaces only helper-managed prior renders and never deletes unrelated files.
- PowerPoint is a useful font-fidelity example when already available. LibreOffice is useful for layout/structure QA, but it may substitute embedded fonts; inspect the JSON `pdfFonts` field and do not treat it as final font acceptance. Other available tools can be equally valid when their limits are understood and disclosed.
- PNG existence is not enough: review every page for overflow, occlusion, image fit, chart labels, tables and formulas.
- A failed render, unavailable renderer or skipped render is not visual acceptance. Continue source/package checks, use any other available inspection route, and disclose exactly what visual review was possible or skipped.

Deliver the project and `.pptx` with absolute local paths. State unresolved warnings, font substitutions, rendering-engine limitations, and anything the user must install or provide.
