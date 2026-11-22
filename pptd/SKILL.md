---
name: pptd
description: "Create, design and export presentations in the PPTD format. Use when building slides from a brief or document or working with .pptd projects."
---

# PPTD

Author presentations in the PPTD v2 YAML format and export locally to `.pptx` (requires **Node.js 26+**). Resolve `scripts/` and `references/` below relative to this skill folder.

Deliver **both** a self-contained editable project (`.pptd`, `pages/`, referenced assets) and the matching `.pptx` with fade transitions, unless the user asks for PPTD-only output.

Export is one-way (**PPTD → PPTX**). When given a standalone `.pptx` without PPTD source, match the workflow to the request and environment—gather visual or structural references to rebuild it in PPTD when redesigning or producing `.pptd` source, or handle small in-place edits directly when supported. Preserve unrelated source during PPTD edits.

## 1. Plan and read selectively

Infer audience, language, page count, aspect ratio and design direction; ask only when missing choices materially affect the output. User content, brand rules and references take priority. Never fabricate facts, data, citations or missing source material.

- Read **`references/pptd.md`** for every project, then only the linked shared types and element contracts you use (charts have their own reading index). Do not invent fields.
- Read **`references/slides_categories.md`** for the design baseline. For self-directed design, add one matching scenario guide from its router.
- Use a preset **only when explicitly named**: read `references/design_system/README.md`, that preset, and its linked baseline/shared file. Never mix or auto-select presets.
- Load on demand: `references/general-poster.md` (posters/infographics), `references/fonts.md` (fonts/warnings), `references/shapes.md` (shapes beyond `elements/shape.md`).

## 2. Build a portable project

Use the layout in `references/pptd.md` (**Project paths**): a `deck.pptd` manifest, `pages/*.page`, optional `media/`.

Keep page, media and custom-font paths relative to the manifest and inside its directory. Localize remote images and authorized font files before calling the source self-contained; a cache or `.pptx` copy does not make the `.pptd` source portable. Prefer bundled or licensed project-local fonts (embedding permission does not authorize redistributing system fonts).

Give each page a clear reader task and visual hierarchy. Keep text, vectors, tables and ordinary charts editable where practical; crop images instead of distorting them. Write literal `\(...\)` inside text block scalars for editable Office Math, and use only documented rich-text tags (closed tags, quoted attributes) and HTML entities. Inline CSS is a closed contract: unsupported declarations and non-`https`/`http`/`mailto` links are errors that name the supported forms, and `$theme` colors resolve automatically. Add notes or element animations only when requested or clearly helpful for live delivery.

## 3. Validate and export

```bash
node scripts/export.mjs /absolute/path/deck/deck.pptd \
  --output /absolute/path/deck/deck.pptx
```

A project directory works when it contains one manifest. `node scripts/export.mjs --help` lists every option.

Export validates schema and assets, prepares icons/fonts/formulas/charts, builds `.pptx`, and verifies XML, relationships, media and ZIP integrity. Fix errors—never substitute placeholders for broken formulas, charts or icons. Review warnings carefully: intentional bleed may be fine, but font substitutions, missing styles or non-embeddable fonts need fixing or honest disclosure.

For PPTD-only output or a standalone check:

```bash
node scripts/validate.mjs /absolute/path/deck/deck.pptd
# also preview font resolution/style/embedding/coverage warnings without exporting:
node scripts/validate.mjs /absolute/path/deck/deck.pptd --check-fonts [--font-dir PATH] [--offline]
```

`heatmap`, `treemap`, `sunburst` and `sankey` export as **SVG pictures** (retaining source data in PPTD and SVG metadata, with labels frozen as glyph paths; requires SVG-capable playback, no raster fallback). Other chart types stay native.

## 4. Review and deliver honestly

Always review layout, text length, hierarchy, contrast, alignment, cropping, layering, sources and export warnings.

When your environment can inspect or render `.pptx` files—via local tools or the bundled `scripts/render_slides.py` helper (`--if-available`; `--force` replaces its own prior renders), review every page visually for font fidelity, overflow, occlusion, image fit, chart labels, tables and formulas, keeping in mind how faithfully the preview backend handles embedded fonts and math. Always fix issues in the **PPTD source** and re-export so `.pptd` and `.pptx` stay in sync.

Never treat a failed render or structural-only check (XML, ZIP, PNG existence) as visual acceptance. If visual rendering isn't possible locally, continue source/package checks and disclose that rendered visual review was skipped. Link the project and `.pptx` with absolute local paths, and state any unresolved warnings or font limitations.
