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

The exporter is one-way: **PPTD → PPTX**. There is no PPTX importer, editor, renderer, or image exporter. To edit or replicate an existing `.pptx`, ask for a PDF or page images and rebuild it as PPTD. The pipeline performs structural and PPTX package checks, not rendered visual QA, and does not embed fonts.

`references/pptd.md` is the authoritative format contract. Do not invent fields or substitute another YAML schema.

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
| Font selection | `references/fonts.md` |
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
- Add speaker notes only when requested. Add element animations only when requested or clearly useful for a live presentation; slide-level fade is handled during export.

For self-directed design, decide each page's reader task before laying it out. Use relevant images as evidence or explanation, not as decoration quotas. Prefer user-supplied sources, then authoritative sources, and keep factual source links where appropriate.

### 4. Validate and export

Export requires Node.js 18+ and Python 3 with PyYAML (`python -m pip install PyYAML` if missing). Run:

```bash
python scripts/export_pptx.py \
  /absolute/path/deck/deck.pptd \
  --output /absolute/path/deck/deck.pptx
```

Use `python3` when that is the available command. A project directory is accepted when it contains exactly one `.pptd`.

- `--transition none` disables slide transitions; the default is `fade`.
- `--force` replaces an existing output file.

The command performs structural validation, invokes the bundled WASM writer, writes schema-ordered slide transitions, checks PPTX ZIP integrity, and prints a JSON summary. Fix every validation error. Review canvas-overflow warnings with judgment because intentional bleed is allowed; also inspect long text, contrast, alignment, and layering against the spec.

For PPTD-only delivery or a standalone structural check, run:

```bash
python scripts/validate_pptd.py /absolute/path/deck/deck.pptd
```

Export is offline for local media; remote image URLs require network access. Use fonts available on the intended playback machine.

### 5. Deliver accurately

Link the project directory and generated `.pptx` using absolute local paths; link the `.pptd` directly when useful. Mention unresolved validation warnings or environment limitations, and do not present package verification as proof of identical rendering or playback in PowerPoint, WPS, or Keynote.
