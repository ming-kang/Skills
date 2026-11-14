# PPTD tables

Read the style precedence and merged-grid rules before authoring. Shared types are in [../types.md](../types.md); cell text follows the same [text grammar](text.md#rich-text-rules), including entities, shorthand paragraphs and formulas.

#### 2. Table Cell Styles

**Priority chain:**
1. Rich-text semantic tags such as `<u>`, `<sup>`, `<strong>` in [Cell.text](#cell)
2. Inline properties set in `<span style="...">`
3. Paragraph properties set in `<p style="...">`
4. [Cell](#cell) inline fields
5. The [TextStyleConfig](../pptd.md#textstyleconfig) referenced by [Cell.textStyle](#cell) (**applies only to text fields**; does not include `fill` / `border` / `align`)
6. Position-category styles of [TableStyleConfig](#tablestyleconfig)
   - On row vs column conflicts, [TableStyleConfig.rowOverColumn](#tablestyleconfig) decides the winner; default `true` = row wins
   - Row categories: `TableStyleConfig.firstRowStyle` / `TableStyleConfig.lastRowStyle`
   - Column categories: `TableStyleConfig.firstColumnStyle` / `TableStyleConfig.lastColumnStyle`
7. [TableStyleConfig.bodyStyles](#tablestyleconfig): applies to data rows other than the first and last rows, cycled by data-row index
8. [TableStyleConfig.cellStyle](#tablestyleconfig): the baseline cell style for the whole table
9. Default values

| Property | Default value |
|---|---|
| color | `#000000` |
| backgroundColor | Not applied |
| fontSize | Auto-adapts based on cell height |
| fontFamily | `"MiSans"` |
| bold | `false` |
| italic | `false` |
| lineHeight | `1` |
| lineHeightPx | Not applied |
| letterSpacing | `0` |
| marginTop | `0` |
| fill | Not applied (transparent) |
| border | `{style: solid, width: 1, color: "#000000"}` |
| align | `["center", "middle"]` |

#### CellStyle

```ts
interface CellStyle extends TextStyleConfig {
  // —— Inherits all properties of TextStyleConfig ——
  //   color / fontSize / fontFamily / bold / italic / backgroundColor / lineHeight / lineHeightPx / letterSpacing / marginTop

  // —— CellStyle-specific ——
  fill?: Fill;                              // background fill
  border?: BorderSpec;                      // border
  align?: Alignment;                        // text alignment
}
```

> Unset fields fall back along the inheritance chain (see [Style Priority and Default Values](../pptd.md#style-priority-and-default-values) for details)

#### TableStyleConfig

```ts
interface TableStyleConfig {
  // —— Cell style: applied to every cell ——
  cellStyle?: CellStyle;

  // —— Row category overrides ——
  firstRowStyle?: CellStyle;  // first-row style
  lastRowStyle?: CellStyle;  // last-row style

  // —— Column category overrides ——
  firstColumnStyle?: CellStyle;
  lastColumnStyle?: CellStyle;

  // —— Alternating row styles ——
  bodyStyles?: CellStyle[];  // data rows other than the first/last row apply these cyclically by data-row index

  // —— Cross-category rule ——
  rowOverColumn?: boolean;            // default: true; whether the row style wins when a cell is covered by both row and column rules
}
```
> **Row/column style rules**: category styles such as `firstRowStyle` / `lastRowStyle` / `firstColumnStyle` / `lastColumnStyle` mean **apply the style independently to every matching cell**, not apply the style to the first row/last column as a whole
> - Writing `firstRowStyle.border: {style: solid, width: 2}` → **every cell of the first row** gets a border on all four sides
> - To add an outer frame to the first row as a whole, use per-side BorderSpec: `border: [<top line>, null, <bottom line>, null]`, then set borders separately on the first-column and last-column cells of the first row


> For fallback rules, see [Style Priority and Default Values](../pptd.md#style-priority-and-default-values)

### Table (table)

```ts
interface Table extends ElementBase {
  elementType: "table";
  columnWidths: number[];              // array of column-width ratios (not px; relative to the bounds width)
  rowHeights: number[];                // array of row-height ratios (not px; relative to the bounds height)
  rows: Cell[][];                      // 2-D array; merged regions are declared with rowSpan/colSpan, occupied positions are skipped in the array
  style?: string | TableStyleConfig;   // references theme.tableStyles, written as "$key" (e.g. "$default"), or an inline TableStyleConfig object
  fill?: Fill;                         // default: not applied; table-level fill (applied to the whole table, can be overridden by cell fill)
  shadow?: Shadow;                     // default: not applied
}
```

> **PowerPoint limitation:** native tables cannot be rotated/flipped as a whole; whole-table global opacity including text and borders is also not supported. When whole rotation/flip/opacity is needed, render as an image first and treat it as an [Image](image.md#image-image) element.

> **Constraint:** each item of `columnWidths` and `rowHeights` is within `[0, 1]`, and the elements of each sum to 1.

#### Cell

```ts
interface Cell {
  // —— Content ——
  text?: string;             // default: empty cell; rich text string (written as a block scalar), rules same as TextContent.text
  textStyle?: string;        // references theme.textStyles, written as "$key" (e.g. "$body")

  // —— Text styles (when unset, fall back along the inheritance chain) ——
  color?: Color;
  fontSize?: number;
  fontFamily?: FontFamily;
  bold?: boolean;
  italic?: boolean;
  backgroundColor?: Color;             // text background color (e.g., text highlight)
  lineHeight?: number;                 // line-height multiple
  lineHeightPx?: number;               // fixed line height (px)
  letterSpacing?: number;
  marginTop?: number;

  // —— Cell styles (when unset, fall back along the inheritance chain) ——
  fill?: Fill;                         // background fill; supports solid / gradient / image
  border?: BorderSpec;
  align?: Alignment;

  // —— Merging ——
  rowSpan?: number;                    // default: 1
  colSpan?: number;                    // default: 1
}
```

**Basic example (using theme styles):**

```yaml
- elementId: table-basic
  elementType: table
  bounds: [80, 120, 800, 280]
  columnWidths: [0.3, 0.35, 0.35]
  rowHeights: [0.33, 0.33, 0.34]
  style: "$default"
  rows:
    - - text: "Metric"
      - text: "2023"
      - text: "2024"
    - - text: "Revenue (100M CNY)"
      - text: "82.5"
      - text: "96.3"
    - - text: "Net profit (100M CNY)"
      - text: "12.1"
      - text: "15.8"
```

> **Merged-cell rules:** `rowSpan` / `colSpan` declare the merge range; **cells covered by the merged region are omitted from the `rows` array, with no `null` placeholder needed**. For example, after a top-left 2×2 merge, row 0's colSpan=2 covers (0,1), so that row only has two items ((0,0) merged cell + (0,2)); row 1 has (1,0) and (1,1) occupied by the merge, so it only has one item, (1,2).

```yaml
- elementId: table-merged
  elementType: table
  bounds: [100, 100, 600, 400]
  columnWidths: [0.33, 0.33, 0.34]
  rowHeights: [0.33, 0.33, 0.34]
  rows:
    # Row 0: top-left 2×2 merge + C1. The merged (0,1) is omitted
    - - text: "Merged cell"
        fill: {type: solid, color: "$accent"}
        rowSpan: 2
        colSpan: 2
      - text: "C1"
    # Row 1: (1,0) and (1,1) are occupied by the merge → only C2 remains
    - - text: "C2"
    # Row 2: full three columns
    - - text: "A3"
      - text: "B3"
      - text: "C3"
```

---
