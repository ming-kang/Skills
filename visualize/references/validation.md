# Validate an SVG

Use the `scripts/validate_svg.py` bundled with this skill. It requires Python 3.10+ and no third-party packages. Replace `SKILL_DIR` below with the directory containing `SKILL.md`; do not assume the current directory is the installed skill.

```bash
python SKILL_DIR/scripts/validate_svg.py diagram.svg
python SKILL_DIR/scripts/validate_svg.py -q output-directory/
python SKILL_DIR/scripts/validate_svg.py --strict --json diagram.svg other.svg
```

Files, directories, and quoted glob patterns are accepted. Directories are searched recursively; duplicate files are checked once. A missing file, unmatched pattern, or empty directory is an error.

- Default: report all checks; exit 1 for errors, 0 otherwise.
- `-q` / `--quiet`: print only warnings and errors; clean input is silent.
- `--strict`: also exit 1 when warnings remain. Useful for maintained templates.
- `--json`: emit one report containing `files`, `summary`, and `strict`; each file includes `path`, `status`, counts, and structured `checks`. This is separate from quiet mode.
- `--no-color`: disable terminal color; redirected output is already uncolored.

## Findings and fixes

| Check | Meaning / action |
|---|---|
| XML / SVG root / viewBox | Use well-formed UTF-8 XML, the SVG namespace, and four finite viewBox numbers with positive width and height. |
| Accessibility | Put non-empty `<title>` and `<desc>` first. Describe the relationships, not only the diagram's filename. |
| References and assets | Keep resources inline or use local `#id` references. IDs must be unique and local targets must exist. |
| Marker / background / flat style | Use the scaffold's open chevron, an opaque white canvas, and no gradients or filters. |
| Box overlap / connector collisions | Separate unrelated nodes and route connections through clear gutters. Only intentional containers may contain nodes. |
| Canvas bounds | Keep shapes and connector paths inside the viewBox. Small marks are checked too. |
| Text fit / label collisions / text bounds | Resize nodes, shorten labels, or move captions. For fixed-size timeline bars, move the label rather than changing the represented duration. |
| SVG values | Correct malformed numbers, negative sizes, or invalid hex colors. These are diagnostics, not Python tracebacks. |
| Unsupported geometry | Inspect with a browser or simplify the unsupported construct; skipped geometry has not been verified. |

Text measurements are conservative estimates, so text findings are warnings. The validator checks approximate vertical fit and curved-shape containment as well as width. Palette findings are advisory; deliberate brand colors still need a visual review.

## Geometry and CSS coverage

The checker understands rectangles, circles, ellipses, polygons, and SVG path commands `M/L/H/V/C/S/Q/T/A/Z`. Curves use their trajectories, not straight chords. It resolves numeric, pixel, percentage, and absolute-unit geometry, ordinary presentation attributes, inline CSS, and type/class/ID selectors with descendant or child combinators, inheritance, and `!important`.

Transforms, clipping/masks, nested SVGs, `<use>`, `<foreignObject>`, positioned text runs, unsupported units, and advanced CSS constructs require browser measurement. The report exposes these limits. Stroke bounds use half-width padding; miter joins and marker extents still need rendered inspection. Font metrics are estimates and do not include custom letter/word spacing. It is not a complete SVG/CSS rendering engine.

`svgkit` adds semantic `data-role` attributes. For manual SVG, use `panel` or `container` on intentional groups, `node` on routing obstacles, `connector` on markerless connections, `data-mark` on fixed-size chart marks, and `node-part` on a compound shape's decorative pieces. Text roles distinguish `node-text`, `arrow-label`, `container-label`, and `legend-label`. Roles do not exempt content from syntax or canvas-bound checks.

## Rendered inspection

When a renderer is available, inspect the image at its intended display size. Read every label, trace each edge, and check arrowheads, layer order, container headers, legends, and Chinese text. Preserve the graph's meaning when changing layout. A clean report does not prove that a diagram is semantically correct or visually readable.
