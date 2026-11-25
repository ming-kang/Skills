# PPTD

Create, edit, replicate, validate and export presentations through a private YAML DSL and its bundled WASM writer. Default delivery is a **self-contained editable PPTD project + matching .pptx**, with fade transitions.

The workflow needs **Node.js 26+** (`node --version`); use an existing version manager or the current official Node.js installer/archive when the system Node is older. Optional local rendering or inspection tools supply visual and structural review. Export is one-way (`PPTD → PPTX`)—rebuild existing `.pptx` files from PDF, page images, or structural inspection.

## Install and use

```bash
npx skills add ming-kang/skills
```

Describe the audience, content, page count, language and design direction:

```text
Make an 8-page product-launch deck with a dark visual style.
Replicate this report as editable PPTD and PPTX.
Redo only the section dividers in my deck.pptd.
Use the pine-green-strategy preset for this consulting deck.
```

All **44 named presets and seven scenario guides** are available. Self-directed design uses a scenario guide; an explicitly named preset uses its signature and linked category baseline/shared file. The [preset index](../pptd/references/design_system/README.md) routes to only the relevant material.

## Project and format

```text
deck/
  deck.pptd
  pages/                 # one .page per slide
  media/                 # referenced local assets
  deck.pptx              # generated
```

Paths are relative to the manifest, and local files must stay inside its directory. Local image type is detected from bytes rather than filename extension; HTTP(S) and bounded `data:` image URLs are also supported. [references/pptd.md](../pptd/references/pptd.md) is the short common contract and reading index; shared types, individual elements and animations load on demand. No fields, constraints or examples were dropped from the element contracts.

## Export and validate

Run from the installed skill folder (repository copy: `pptd/`):

```bash
node scripts/export.mjs /absolute/path/deck/deck.pptd -o /absolute/path/deck/deck.pptx
node scripts/validate.mjs /absolute/path/deck/deck.pptd
```

A directory with exactly one manifest is also accepted.

| Option | Purpose |
|---|---|
| `--force` | Replace an existing output; failed exports preserve it |
| `--transition none` | Disable the default fade |
| `--font-dir PATH` | Search a local font directory; repeatable |
| `--no-embed-fonts` | Deliberately leave fonts external |
| `--offline` | Forbid remote media and uncached Google Fonts requests |
| `--wasm PATH` | Explicitly test a compatible alternative writer |

`manifest.metadata` (`title` / `author` / `company` / `subject` / `copyright`) is written to the file's document properties; `title` alone falls back to `manifest.title`.

`validate.mjs` accepts `--check-fonts`, repeatable `--font-dir PATH` (with `--check-fonts`) and `--offline`: it resolves the same font selection as export and reports substitution, missing-style, non-embeddable and missing-glyph warnings in both stderr and JSON output without building a `.pptx`.

Export validates YAML/schema/paths, IDs, geometry, table grids, charts, animations, formulas and image bytes; prepares assets; runs WASM; patches font styles/table image fills/transitions; then checks XML, relationships, content types, slide count and ZIP CRC. Stdout is a JSON summary; warnings go to stderr. Fix errors and review substitutions/unavailable styles rather than calling them exact matches.

Bundled/local/cached fonts and local media work offline. For portable decks without a corporate font requirement, prefer explicit bundled families such as `{latin: Liter, ea: Noto Sans SC}` over unavailable system defaults. Localize remote images and authorized font sources before calling the **editable project** portable: a cache or PPTX embedding does not localize source references.

## Editable capabilities and limits

- **Icons:** offline Font Awesome Free `fas`/`far`/`fab` outlines become native vectors; unknown names fail.
- **Fonts:** complete licensed Latin families and Noto Sans SC are bundled in lossless gzip storage; original font bytes are unchanged. Installed/project fonts and Google Fonts CSS are supported; eligible static TTF/TTC/EOT faces retain family identity and regular/bold/italic/bold-italic bindings. Variable/CFF/restricted faces remain external with warnings. Embedding permission does not authorize distributing loose system fonts. Full system CJK fonts can add tens of megabytes, so explicit bundled families are usually smaller and more portable. See [fonts.md](../pptd/references/fonts.md).
- **Text and formulas:** one text grammar preserves entities, literal comparisons such as `p<0.05`, inline styles outside paragraphs, and text beside blocks. Inline CSS is a closed contract: unsupported declarations (`letter-spacing`, `text-decoration`, …) fail with the supported property list instead of being dropped, `$theme` colors are resolved before export, and `<br>` becomes a paragraph split because the writer has no soft line break. Literal `\(...\)` in text/table cells becomes editable OMML through local KaTeX → MathML conversion, including multiline expressions. Fractions, scripts, radicals, ordinary matrices, delimiters, accents and limits are supported; malformed markup/unmapped constructs fail instead of invoking an incomplete fallback. Source files stay unchanged.
- **Tables:** editable native cells, merged grids, style inheritance and image fills.
- **Charts:** ordinary charts remain native. `heatmap`, `treemap`, `sunburst`, `sankey` become SVG pictures with source data retained in PPTD and SVG metadata—not native “Edit Data” worksheets. Selected glyph paths preserve labels; unsupported complex/bidi shaping fails. Frames remain native shapes and share animations. SVG-capable playback is required; no PNG fallback is bundled.

## Conditional inspection and visual review

Use whatever inspection and rendering tools the current environment already provides; installing an office suite is not a requirement for export. PowerPoint, LibreOffice, existing PDF/PNG preview tools and structural package inspection are examples, not mandatory choices. One optional bundled path is:

```bash
python scripts/render_slides.py /absolute/path/deck/deck.pptx \
  -o /absolute/path/deck/.qa-images --if-available
```

The helper auto prefers Windows PowerPoint, otherwise LibreOffice, and both export PDF before optional PyMuPDF rasterization because direct PowerPoint PNG export may substitute embedded fonts. Office, Python and PyMuPDF are not export dependencies. PowerPoint is useful for font-fidelity checks when already available. LibreOffice may substitute embedded fonts—especially CJK—so treat its PNGs as layout/structure QA rather than final font acceptance. The JSON result includes `pdfFonts` and a font-substitution warning when applicable. If the helper is unavailable, use another existing local inspection route rather than treating a new dependency as mandatory.

`rendered` supplies page PNGs to inspect, not an acceptance verdict. Fix source, export and render again. `skipped` means dependencies are unavailable and must be disclosed; an available renderer's failure is not a pass. `--force` replaces only the helper's managed prior output. Source files, unrelated output and other Office presentations are protected.

Package checks and PNG existence do not prove visual quality or identical rendering/playback in PowerPoint, WPS or Keynote.

## Development and attribution

The [development notes](../tools/pptd/README.md) describe module ownership, asset builds and regression checks. The writer and adapter are version-locked; see [assets/wasm/README.md](../pptd/assets/wasm/README.md). JavaScript is self-contained under [assets/vendor/](../pptd/assets/vendor/README.md), with only required chart/font containers bundled.

This is an independent, unofficial project. Repository-authored code is [MIT](../LICENSE); third-party [renderer/parser licenses](../pptd/assets/vendor/licenses/), [Font Awesome attribution](../pptd/assets/icons/README.md) and [font licenses](../pptd/assets/fonts/README.md) remain intact. Product names and trademarks belong to their owners.
