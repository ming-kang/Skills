# PPTD text

Shared types are in [../types.md](../types.md).

#### 1. Text Styles Inside a Text Box

**Priority chain:**
1. Rich-text semantic tags such as `<u>`, `<sup>`, `<strong>` in [Text.content.text](#textcontent)
2. Inline properties set in `<span style="...">`
3. Paragraph properties set in `<p style="...">`
4. **Style fields set directly on [Text.content](#textcontent)** (distinct from the theme style referenced by `style`; including `color`, `fontSize`, `fontFamily`, `bold`, `italic`, `backgroundColor`, `lineHeight`, `lineHeightPx`, `letterSpacing`, `marginTop`)
5. The [TextStyleConfig](../pptd.md#textstyleconfig) theme style referenced by [Text.content.style](#textcontent)
6. Default values:

| Property | Default value |
|---|---|
| color | `#000000` |
| backgroundColor | Not applied |
| fontSize | `18` |
| fontFamily | `"MiSans"` |
| bold | `false` |
| italic | `false` |
| lineHeight | `1` |
| lineHeightPx | Not applied |
| letterSpacing | `0` |
| marginTop | `0` |

### Text (text box)

```ts
interface Text extends ElementBase {
  elementType: "text";
  rotation?: number;                  // default: 0; degrees, clockwise rotation
  opacity?: number;                   // default: 1; constraint: [0, 1]
  flip?: [boolean, boolean];          // default: [false, false]; [horizontal flip, vertical flip]
  content: TextContent;
}
```

#### TextContent

```ts
interface TextContent {
  text: string;                                // rich text string (block scalar)
  style?: string;                              // references theme.textStyles, written as "$key" (e.g. "$title")

  // —— Style fields (when unset, fall back along the inheritance chain) ——
  color?: Color;
  fontSize?: number;
  fontFamily?: FontFamily;
  bold?: boolean;                              // bold: true=on, false/unset=off
  italic?: boolean;                            // italic: true=on, false/unset=off
  backgroundColor?: Color;                     // text background color (e.g., text highlight)
  lineHeight?: number;                         // line-height multiple
  lineHeightPx?: number;                       // fixed line height (px)
  letterSpacing?: number;
  marginTop?: number;

  // —— Layout fields ——
  textDirection?: "horizontal" | "vertical";   // default: "horizontal"
  wrap?: boolean;                              // default: true; when false, no wrapping, and the part beyond bounds.width overflows the element boundary; explicitly setting false is recommended for single-line text
  align?: Alignment;                           // default: ["left", "top"]

  // —— Visual decoration (unset = not applied) ——
  gradient?: GradientFill;                     // text gradient (applied to the text itself)
  shadow?: Shadow;                             // text shadow
}
```

**Examples:**

```yaml
# Basic: theme style + plain text
- elementId: title-1
  elementType: text
  bounds: [100, 50, 760, 80]
  content:
    style: "$title"
    align: [center, middle]
    text: Annual Work Summary

# Rich text + inline property overrides
- elementId: body-1
  elementType: text
  bounds: [100, 200, 600, 200]
  content:
    fontSize: 20
    color: "$text"
    lineHeight: 1.6
    align: [left, top]
    text: |
      <p><strong>Key achievement</strong>: completed <span style="color:$primary;">3</span> key projects</p>
      <p style="text-align:right"><span style="font-size:14px; color:#6b7280;">—— FY2024</span></p>

# Text gradient + shadow
- elementId: hero-text
  elementType: text
  bounds: [100, 100, 760, 120]
  content:
    align: [center, middle]
    gradient:
      type: gradient
      gradientType: linear
      angle: 90
      stops:
        - {position: 0, color: "$primary"}
        - {position: 1, color: "$accent"}
    shadow:
      blur: 6
      color: "#00000040"
      offset: [0, 3]
    text: |
      <p><span style="font-size:64px;">FUTURE</span></p>
```

#### Rich Text Rules

The exporter applies one text grammar to both shorthand and tagged text:

- The tags listed below are markup; other tag-like strings (for example `List<T>`) stay literal.
- Known HTML entities, including numeric references and `&nbsp;`, are decoded consistently. Unknown `&name;` and bare ampersands stay literal; use `&amp;amp;` to display the text `&amp;` itself.
- Loose top-level text is wrapped as one paragraph per line. Inline styles work without an explicit `<p>`; text before/after a paragraph or list is preserved. Formatting whitespace between blocks is ignored.
- Close markup tags and quote attribute values. Mismatched/unclosed tags and duplicate attributes fail with the page/element location instead of being guessed. Escape a literal tag-shaped comparison such as `<b and c>` with `&lt;`.
- Formula delimiters cannot be split by markup. Newlines inside a complete `\(...\)` expression remain LaTeX whitespace, not paragraph breaks. The exporter reuses this parsed text for font selection and formula conversion; source files are never rewritten.

`TextContent.text` and `Cell.text` follow the rich text rules below for paragraph splitting and for setting paragraph or inline styles.

**Supported tags**

| Tag | Description | Example |
|------|------|------|
| `<p>` | Paragraph; may carry paragraph styles | `<p>paragraph</p>` |
| `<span>` | Inline style; use this tag to set inline styles | `<span style="color:#f00">red</span>` |
| `<strong>` | Bold | `<strong>important</strong>` |
| `<em>` | Italic | `<em>emphasis</em>` |
| `<u>` | Underline | `<u>underline</u>` |
| `<s>` | Strikethrough | `<s>deleted</s>` |
| `<sup>` | Superscript | `E=mc<sup>2</sup>` |
| `<sub>` | Subscript | `H<sub>2</sub>O` |
| `<a>` | Hyperlink; supports `https://`, `http://`, `mailto:`; once set, the hyperlink text style (blue with underline) is applied automatically | `<a href="https://x.com">link</a>` |
| `<ul>` | Unordered list | `<ul><li>item</li></ul>` |
| `<ol>` | Ordered list | `<ol><li>first item</li></ol>` |
| `<li>` | List item; must be used together with `<ul>` or `<ol>` | — |

**style attribute mapping**

`<p>`, `<li>`, and `<span>` may use `style="..."`. Color-type values may all use theme references (e.g. `$primary`), resolved per the [Color](../types.md#color) rules.

1. **Paragraph styles (only `<p>` supports them)**

| Property | Description | Values | Example |
| --- | --- | --- | --- |
| `text-align` | Paragraph horizontal alignment | `left` / `center` / `right` / `justify` / `distributed` | `<p style="text-align:center">…</p>` |
| `line-height` | Line height; **unitless** is treated as a `lineHeight` multiple, **with `px`** as a `lineHeightPx` fixed value | number (e.g. `1.5`) or px string (e.g. `24px`) | `<p style="line-height:1.6">…</p>` |
| `margin-top` | Spacing before the paragraph | px string (e.g. `8px`) | `<p style="margin-top:8px">…</p>` |
| `margin-left` | Left margin | px string (e.g. `12px`) | `<p style="margin-left:12px">…</p>` |
| `margin-right` | Right margin | px string (e.g. `12px`) | `<p style="margin-right:12px">…</p>` |

> Do not set `letter-spacing` on `<p>`; to set letter spacing uniformly, use `content.letterSpacing` or `Cell.letterSpacing`.

2. **List-item styles (only `<li>` supports them)**

| Property | Description |
| --- | --- |
| `text-align` | List-item horizontal alignment |
| `line-height` | Line height; value rules same as `<p>` |
| `letter-spacing` | Letter spacing |
| `margin-top` | Spacing before the paragraph |
| `margin-left` | Left margin |
| `list-style` | List style shorthand |
| `list-style-type` | List marker type |
| `list-style-position` | List marker position |
| `list-style-image` | List marker image |

3. **Inline styles (only `<span>` supports them)**

Styles apply only to the text inside that `<span>`.

| Property | Description | Values | Example |
| --- | --- | --- | --- |
| `color` | Text color | [Color](../types.md#color) (HEX6 / HEX8 / theme reference) | `<span style="color:$primary">…</span>` |
| `font-size` | Font size | px string (e.g. `24px`) | `<span style="font-size:24px">…</span>` |
| `font-family` | Font family | Font name (e.g. `Arial`, `'Arial, 微软雅黑'`) | `<span style="font-family:Arial">…</span>` |
| `background-color` | Text background color | [Color](../types.md#color) (HEX6 / HEX8 / theme reference) | `<span style="background-color:$accent">…</span>` |


```yaml
content:
  align: [left, top]
  lineHeight: 1.2
  text: |
    <p><span style="font-size:32px; color:$primary;">Main Title</span><span style="font-size:18px; color:$secondary;">Subtitle</span></p>
    <p style="text-align:center; line-height:1.8">This paragraph is center-aligned with 1.8x line height</p>
    <p style="text-align:right">This paragraph is right-aligned; line height inherits the default 1.2</p>
```
**Plain-text shorthand**

`content.text` may use plain text directly:
- Single line: `text: "Hello"` ≡ `text: "<p>Hello</p>"`
- Multi-line (block scalar):
  ```yaml
  text: |
    First line
    Second line
  ```
  ≡ `<p>First line</p><p>Second line</p>`
- `<br/>` may be used for a line break within a paragraph, but it is not guaranteed to be preserved on re-conversion after editing. When stable line breaks are needed, use multiple `<p>`.

**LaTeX formulas**

Rich text supports embedding LaTeX formulas with the `\(...\)` delimiters:
- May form their own paragraph, or be mixed with other text inside a `<p>`.
- Rich text tags are **not allowed** inside a formula.
- A formula **only inherits** the `color` and `font-size` styles from its context; other text styles are not passed through.
- A `<p>` tag can wrap a LaTeX formula to control the alignment
- Local export uses strict KaTeX → MathML → editable OMML for both text boxes and table cells; legacy `data-math-node`/`data-tex` spans are restored to literal delimiters in memory. Unknown/unmapped constructs and callback failures are errors, never silently flattened or handed to the writer's incomplete fallback.
- Ordinary fractions/scripts/radicals/matrices/delimiters/accents/limits are supported. Ruled arrays, unmapped explicit script levels and negative spacing currently require an equivalent supported expression; do not imply an unsupported construct was preserved.

```yaml
content:
  text: |
    <p>Pythagorean theorem: \(a^2 + b^2 = c^2\)</p>
    <p>\(\int_0^1 x^2 \mathrm{d}x = \frac{1}{3}\)</p>
```

---
