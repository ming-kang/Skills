---
name: pptd
description: "Create, edit, replicate, validate, and export presentations with the private PPTD YAML format and its bundled WASM writer. Use whenever a slide deck, PowerPoint, PPT/PPTX, infographic, or poster is involved. Produces BOTH a self-contained editable PPTD project and a local .pptx by default; supports PPTD → PPTX only."
---

# PPTD

PPTD is a private, YAML-based presentation format. Each `.pptd` manifest lists self-contained `.page` files; the bundled WASM writer converts the project to PPTX without a browser or cloud service.

Resolve paths below relative to this skill folder, including when working from another directory.

## Scope and delivery

Unless the user explicitly requests PPTD-only output, deliver:

1. A complete PPTD project: one `.pptd`, its `pages/`, and every referenced local asset.
2. The matching `.pptx`, exported locally with a fade slide transition by default.

The exporter is one-way: **PPTD → PPTX**. There is no PPTX importer, browser editor, or independent full-slide layout engine. To edit or replicate an existing `.pptx`, ask for a PDF or page images and rebuild it as PPTD. Local adapters prepare editable vector icons, permitted font embedding, native Office Math, table image fills, and advanced-chart SVGs. Optional local PowerPoint or LibreOffice rendering supplies page PNGs for visual review when available; no part of this workflow needs a browser.

`references/pptd.md` is the authoritative format contract. Do not invent fields or substitute another YAML schema.

## Runtime layout

```text
scripts/
  export.mjs           # public CLI: read, prepare, WASM export, patch, verify
  validate.mjs         # structural check without exporting
  render_slides.py     # optional local Office/LibreOffice QA renderer
  render_powerpoint.ps1
  lib/deck/            # YAML 1.2 reader and the v2 schema
  lib/prepare/         # fonts, icons, images, formulas, advanced charts, SVG text
  lib/pptx/            # version-locked WASM writer, ZIP, OOXML patch & verify
```

Node.js 26+ is the only mandatory runtime requirement. Python 3 + PyMuPDF are only needed when running the optional `render_slides.py` visual review helper.

## Workflow

### 1. Establish the task

Identify whether the task is creating a deck, editing an existing PPTD project, or replicating PDF/page images. Preserve unrelated pages and elements during edits.

Confirm page count, audience, language, aspect ratio, and design direction when they materially affect the result and cannot be inferred. User-provided content, templates, brand rules, and style references take priority over built-in guides. Never fabricate facts, citations, data, or missing source material.

### 2. Load only the references needed

For every deck, read `references/pptd.md` using its own reading index: conventions and §§1, 3, 4 first; then only the shared types, elements, and animation sections used by the deck. Read the general rules in `references/slides_categories.md` for all design work.

| Situation | Additional reading |
|---|---|
| Self-directed presentation design | One matching file under `references/slides_categories/` |
| User explicitly names a preset | `references/design_system/README.md`, then only `<theme-id>.md` beside it |
| Poster, infographic, or highly visual single page | `references/general-poster.md` |
| Font selection, embedding, or a font warning | `references/fonts.md` |
| Built-in or custom shapes | `references/shapes.md` and the corresponding PPTD spec section |

Use a preset only when the user names it; do not mix presets or auto-select one. A preset's signature rules override the general design defaults.

### 3. Build a self-contained project

Use this layout unless editing an existing valid project:

```text
deck/
  deck.pptd
  pages/
    01-cover.page
    02-content.page
  media/                 # when local media is used
```

- Follow the format contract for the manifest, page paths, element IDs, and bounds.
- Keep text, shapes, tables, charts, and images editable where practical; crop source images instead of distorting them.
- Download image assets into `media/` before authoring their paths. Prefer bundled or installed fonts; put user-supplied, redistributable custom fonts inside the project and reference their relative paths. Do not copy loose system fonts merely because document embedding is permitted.
- Use literal `\(...\)` inside text block scalars for formulas. The exporter creates editable OMML; conversion errors must be repaired, not bypassed with the writer's incomplete fallback.
- Add speaker notes only when requested. Add element animations only when requested or clearly useful for a live presentation; slide-level fade is handled during export.

For self-directed design, decide each page's reader task before laying it out. Use relevant images as evidence or explanation, not as decoration quotas. Prefer user-supplied sources, then authoritative sources, and keep factual source links where appropriate.

### 4. Validate and export

Run:

```bash
node scripts/export.mjs \
  /absolute/path/deck/deck.pptd \
  --output /absolute/path/deck/deck.pptx
```

A project directory is accepted when it contains exactly one `.pptd`.

- `--transition none` disables slide transitions; the default is `fade`.
- `--force` replaces an existing output file.
- `--font-dir PATH` adds a local font directory; it may be repeated.
- `--no-embed-fonts` deliberately leaves fonts external. Otherwise permitted static TrueType/EOT faces are embedded with their correct style bindings.
- `--offline` forbids remote media and uses only bundled, local, or cached fonts.

The command reads and validates the project, checks the manifest, element types/IDs/bounds, chart data/mappings, table grids, animations, crop constraints, and XML-safe strings. It prepares icons, fonts, formulas and media, calls the bundled writer, restores native table image fills and font style bindings, writes schema-ordered transitions, and checks all XML/relationships, content types, image signatures, slide count, and ZIP integrity. Fix every error. Review warnings with judgment: intentional canvas bleed is allowed, but a font substitution may violate the brief and needs correction or disclosure.

For PPTD-only delivery or a standalone structural check, run:

```bash
node scripts/validate.mjs /absolute/path/deck/deck.pptd
```

Export is offline for local media and bundled/local/cached fonts. Remote images or uncached Google Fonts CSS require network access. Missing fonts, unavailable style faces, or non-embeddable variable/CFF/restricted fonts are disclosed in the summary. Do not describe substituted fonts as an exact style match.

`heatmap`, `treemap`, `sunburst`, and `sankey` are exported automatically as SVG pictures, not native PowerPoint charts. Their data stays editable in the PPTD source and is retained in SVG metadata. Selected font glyph outlines freeze SVG labels so picture renderers do not substitute their fonts; this does not flatten the slide. Simple horizontal Latin/CJK labels are supported; unsupported complex/bidi shaping is reported explicitly. Other chart types keep the native WASM path. Use SVG-capable presentation software; there is no raster fallback. Invalid advanced-chart data is reported with its page and element ID instead of silently exporting a different chart type.

### 5. Review quality; render when conditions allow

Always inspect text length, hierarchy, contrast, alignment, cropping, layering, sources, and deck rhythm. When local rendering is available, run:

```bash
python scripts/render_slides.py \
  /absolute/path/deck/deck.pptx \
  --output /absolute/path/deck/.qa-images \
  --if-available
```

Use `--force` only to replace this helper's previous renders. Auto selects Windows PowerPoint first, otherwise LibreOffice. Both export a font-faithful PDF and use optional PyMuPDF for PNG rasterization: direct PowerPoint PNG export may substitute embedded fonts and is deliberately avoided. Neither Office nor PyMuPDF is a mandatory PPTX-export dependency; never install or start a browser for QA.

- If `status` is `rendered`, inspect every page image, using an overview when available and full-resolution images for suspicious pages. Check fonts, overflow, occlusion, image fit, chart labels, tables, formulas, and consistent layout. Fix the PPTD source, re-export, and re-render affected output before delivery.
- If `status` is `skipped`, continue with semantic/package checks and manual source-layout review; state that rendered visual review was not performed. An available renderer's failure is not a successful review.
- Rendering creates evidence, not an automatic acceptance verdict. Do not treat valid XML, a ZIP, or a PNG's existence as proof of visual quality.

### 6. Deliver accurately

Link the project directory and generated `.pptx` using absolute local paths; link the `.pptd` directly when useful. Mention unresolved validation warnings or environment limitations, and do not present package verification as proof of identical rendering or playback in PowerPoint, WPS, or Keynote.
