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

The exporter is one-way: **PPTD → PPTX**. There is no PPTX importer, editor, renderer, or image exporter in this skill. To edit or replicate an existing `.pptx`, ask the user for a PDF or page images and rebuild it as PPTD. Do not claim font embedding or image-based visual QA; the bundled pipeline performs structural checks and PPTX package verification.

`references/pptd.md` is the authoritative format contract. It describes the private dialect understood by the WASM writer, so do not invent fields or substitute another YAML schema.

## Workflow

### 1. Establish the task

Determine whether the user wants to:

- **Create** a deck from a topic, document, outline, or template.
- **Edit** an existing PPTD project while preserving unrelated pages and elements.
- **Replicate** PDF or page images as editable PPTD, as closely as the available detail allows.

Confirm page count, audience, language, aspect ratio, and design direction when they materially affect the result and cannot be inferred. User-provided content, templates, brand rules, and style references take priority over built-in guides. Never fabricate facts, citations, data, or missing source material.

### 2. Load only the references needed

For every deck, read `references/pptd.md` using its own reading index: conventions and §§1, 3, 4 first; then only the shared types, elements, and animation sections used by the deck.

| Situation | Additional reading |
|---|---|
| Self-directed presentation design | `references/slides_categories.md`, then one matching file under `references/slides_categories/` |
| User explicitly names a preset | `references/design_system/README.md`, then only that preset's file |
| Poster, infographic, or highly visual single page | `references/general-poster.md` |
| Font selection | `references/fonts.md` |
| Built-in or custom shapes | `references/shapes.md` and the corresponding PPTD spec section |

Use a design preset only when the user names it; do not mix presets or auto-select one for self-directed work. Keep all 44 presets available through the index.

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

Follow the format contract:

- Use `version: v2`, an explicit positive `size`, and an ordered `pages` list.
- Keep page and media paths relative to the manifest directory and inside the project.
- Give every element a unique `elementId` within its page and valid `[x, y, width, height]` bounds.
- Keep text, shapes, tables, charts, and images editable where practical; crop source images instead of distorting them.
- Add speaker notes only when requested. Add element animations only when requested or clearly useful for a live presentation; slide-level fade is handled separately during export.

For self-directed design, decide each page's reader task before laying it out. Use relevant images as evidence or explanation, not as decoration quotas. Prefer sources supplied by the user, then authoritative sources. Keep factual source links in the deck where appropriate.

### 4. Validate the PPTD project

Run the structural validator before exporting:

```bash
python scripts/validate_pptd.py /absolute/path/deck/deck.pptd
```

On Windows, `python` may be the available command; elsewhere use `python3`. The validator requires PyYAML and checks YAML, manifest/page structure, paths, element basics, and local media references. It prints a JSON summary and exits nonzero on errors.

Fix every error. Review warnings, especially possible canvas overflow; intentional bleed is allowed by some designs, so warnings require judgment rather than automatic rewriting. Also inspect long text, contrast, alignment, and layering against the spec. These checks do not replace rendered visual review.

### 5. Export PPTX through the bundled WASM

Requirements:

- Node.js 18 or newer;
- Python 3 with PyYAML (`python -m pip install PyYAML` if missing);
- the bundled `assets/wasm/pptd_wasm_bg.wasm` and Node adapter.

Run:

```bash
python scripts/export_pptx.py \
  /absolute/path/deck/deck.pptd \
  --output /absolute/path/deck/deck.pptx
```

Options:

- `--transition none` disables slide transitions; the default is `fade`.
- `--force` replaces an existing output file.
- `--wasm PATH` overrides the bundled binary only when deliberately testing a compatible build.

A project directory is accepted when it contains exactly one `.pptd`. Export is offline for local media; remote image URLs require network access. The writer does not embed fonts, so use fonts available on the intended playback machine.

The command validates the deck, invokes the WASM writer, writes schema-ordered slide transitions, checks PPTX ZIP integrity, and prints a JSON summary. Treat export errors as deck or toolchain errors; there is no browser fallback.

### 6. Deliver accurately

Link the project directory, `.pptd`, `pages/`, `media/` when present, and generated `.pptx` using absolute local paths. Mention unresolved validation warnings or environment limitations. ZIP and XML verification establish package integrity, not guaranteed rendering or playback compatibility in PowerPoint, WPS, or Keynote.
