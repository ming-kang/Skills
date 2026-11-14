# PPTD format contract

PPTD v2 is a private YAML presentation DSL, exported one-way to PPTX by the bundled writer. This file defines the common contract; the linked files define the element-specific fields. Do not substitute another schema.

## Reading index

Read this file for every project. Then load only the types and elements you will author:

| Need | Contract |
|---|---|
| Colors, font mappings, alignment, borders, shadows, gradients, image fills/crop | [types.md](types.md) |
| Text boxes, rich text, formulas | [elements/text.md](elements/text.md) |
| Preset/custom vector shapes | [elements/shape.md](elements/shape.md); names/adjustments in [shapes.md](shapes.md) |
| Lines and connectors | [elements/line.md](elements/line.md) |
| Images and clipping | [elements/image.md](elements/image.md) |
| Font Awesome vector icons | [elements/icon.md](elements/icon.md) |
| Tables, merged cells, table styles | [elements/table.md](elements/table.md) |
| Charts | [elements/chart.md](elements/chart.md), using its own reading index |
| Element animations | [animations.md](animations.md) |

Font availability, licensing and export options are in [fonts.md](fonts.md), not inferred from a family name.

## Conventions

- Use **YAML 1.2** and JSON-compatible mappings, arrays and scalars. Quote special strings (`:`, `#`, `{`, `}`); use `|` block scalars for rich text and LaTeX so their escapes survive parsing.
- Geometry is in **px**, with origin `(0, 0)` at the top left. `bounds` is `[x, y, width, height]`; width and height must be positive finite numbers. Positions may intentionally bleed beyond the canvas, but validation warns.
- Presentation sizes: 16:9 `[960, 540]`, 4:3 `[720, 540]`. Poster defaults: 16:9 `[1280, 720]`, 9:16 `[720, 1280]`, 4:3 `[1280, 960]`, 3:4 `[960, 1280]`, 1:1 `[1080, 1080]`.
- The private writer maps `fontSize: 18` to **18pt** in PPTX (1px = 1pt for text size).
- Later entries in `Page.elements` are above earlier ones. IDs must be unique within their page; animations target those IDs.
- TS interfaces below describe fields. `// default:` states omission behavior; constraints apply even when a default is not listed.

### Style Priority and Default Values

Unset fields fall back along each element's documented chain, not a universal merge. See the text, table and chart contracts for precedence and defaults. `lineHeight` is a multiple; `lineHeightPx` is fixed px and wins if both are set. Rich-text semantic tags outrank inline style fields.

## Project paths

```text
deck/
  deck.pptd
  pages/
    01-cover.page
    02-content.page
  media/                  # when used
```

Load the project through its `.pptd` manifest, never an individual `.page`. Both CLIs also accept a directory containing exactly one manifest.

Page paths, image paths and custom-font paths are **relative to the manifest directory**, not to the `.page`. Every referenced local file must remain inside it, including through symlinks; absolute paths and `..` escapes are invalid. Remote `Image.src` and image-fill `src` may be HTTP(S) URLs; supported PNG/JPEG/GIF/SVG types are identified from bytes. Localize remote media before calling the editable project self-contained.

## Manifest (.pptd)

### Presentation

```ts
interface Presentation {
  version: "v2";              // required
  title?: string;
  metadata?: PresentationMetadata; // document properties written into the .pptx
  size: [number, number];      // required: positive finite width and height
  theme?: Theme;
  customFonts?: CustomFont[];
  pages: string[];             // required: non-empty ordered list, no duplicate paths
}

interface PresentationMetadata {
  title?: string;              // defaults to Presentation.title
  author?: string;
  company?: string;
  subject?: string;
  copyright?: string;
}
```

```yaml
version: v2
title: Annual Review
metadata:
  author: "Strategy Team"
  company: "Acme"
size: [960, 540]
theme:
  colors:
    primary: "#2563EB"
    text: "#1F2937"
  textStyles:
    title: {fontSize: 40, color: "$primary"}
    body: {fontSize: 18, color: "$text", lineHeight: 1.6}
  tableStyles:
    default:
      firstRowStyle:
        fill: {type: solid, color: "$primary"}
        color: "#FFFFFF"
        bold: true
      bodyStyles:
        - {fill: {type: solid, color: "#F8FAFC"}}
        - {fill: {type: solid, color: "#FFFFFF"}}
pages:
  - pages/01-cover.page
  - pages/02-content.page
```

### Theme

```ts
interface Theme {
  colors?: Record<string, Color>;
  textStyles?: Record<string, TextStyleConfig>;
  tableStyles?: Record<string, TableStyleConfig>; // defined in elements/table.md
}
```

Reference theme entries with `$key`: a color field uses `theme.colors`; `TextContent.style` / `Cell.textStyle` use `theme.textStyles`; `Table.style` uses `theme.tableStyles`. References must exist; color references must not cycle. Table styles can also be inline mappings.

### TextStyleConfig

```ts
interface TextStyleConfig {
  color?: Color;
  fontSize?: number;
  fontFamily?: FontFamily;
  bold?: boolean;
  italic?: boolean;
  backgroundColor?: Color;
  lineHeight?: number;
  lineHeightPx?: number;
  letterSpacing?: number;
  marginTop?: number;
}
```

### CustomFont

```ts
interface CustomFont {
  family: string; // must match the source file's actual family metadata
  src: string;    // project-relative TTF/TTC/OTF/EOT or Google Fonts CSS HTTPS URL
}
```

Local TTCs may contain style-linked faces. Google CSS must supply a complete normal/default-weight TrueType face, not a `text=` subset; downloads are cached. The exporter embeds eligible static TrueType/EOT faces with correct style bindings. Variable/CFF/restricted faces remain external with warnings; see [fonts.md](fonts.md).

## Page (.page)

### Page

```ts
interface Page {
  pageType?: "cover" | "table_of_contents" | "chapter" | "content" | "final" | string;
  // optional category label; does not affect rendering
  background?: Fill;           // default: white solid fill
  notes?: string;              // optional plain-text speaker notes
  elements: Element[];         // required; later entries are on top
  animations?: Animation[];    // optional; see animations.md
}
```

```yaml
pageType: cover
background: {type: solid, color: "$primary"}
elements:
  - elementId: title
    elementType: text
    bounds: [100, 200, 760, 80]
    content:
      style: "$title"
      align: [center, middle]
      text: Hello World
```

## Elements

### ElementBase

```ts
interface ElementBase {
  elementId: string; // non-empty, unique within the page
  elementType: "text" | "shape" | "line" | "image" | "icon" | "table" | "chart";
  bounds: [number, number, number, number]; // [x, y, width, height]
}
type Element = Text | Shape | Line | Image | Icon | Table | Chart;
```

Only set rotation, opacity, flips, fills, borders and shadows where the corresponding element contract supports them. Native table/chart limitations and advanced-chart SVG behavior are documented with those elements.
