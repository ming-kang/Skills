# Creation Guide

Focused reference for creating new `.docx` files with C# + OpenXML SDK. Use this after the shared Bash-first contract in [`../SKILL.md`](../SKILL.md). For editing existing documents, use [`EditingGuide.md`](./EditingGuide.md).

## 1. Build and Validation Workflow

### 1.1 Required Build Contract

**Must use the supported Bash CLI build command** (`<skill-path>/scripts/docx build [out]`), do not execute `dotnet build && dotnet run` separately (skips validation and local workspace handling).

Run from the task directory:

```bash
cd <task-directory>
<skill-path>/scripts/docx env
<skill-path>/scripts/docx init
<skill-path>/scripts/docx build ./output.docx
```

Relative output paths resolve from the task root. On Windows Git Bash, `/c/...` and `C:\...` output paths normalize to the same absolute location before shell checks.
Successful build runs use visible workspaces named `docx-task-<timestamp>-<pid>[-N]` under `./.docx-tmp/` and remove them again by default after validation passes.

### 1.2 Program.cs Output Path Convention (Critical)

**Program.cs must get output path from command line arguments**, otherwise the build script cannot find the generated file:

```csharp
using System.IO;

// Correct - use the CLI-provided output path, fall back to a local file only when run manually
string outputFile = Path.GetFullPath(
    args.Length > 0 ? args[0] : Path.Combine(Environment.CurrentDirectory, "output.docx")
);

// Wrong - hardcoded path breaks the local build contract
string outputFile = "my_document.docx";  // Script can't find file!
```

### 1.3 Build Pipeline

| Step | Action | Notes |
|------|--------|-------|
| 1. Compile | `dotnet build` | Provides fix suggestions on failure |
| 2. Generate | `dotnet run -- <output path>` | Path passed via command line args |
| 3. Auto-fix | `validate_all.py` | Fixes element ordering and runs business-rule checks |
| 4. OpenXML validation | `dotnet validator/Validator.dll` | Mandatory local validator path |
| 5. Statistics | Character + word count | Optional (requires pandoc) |

**Validation is mandatory**: on failure, the file is kept but warnings are shown. Read the error messages and fix the document instead of bypassing the pipeline.

### 1.4 Preflight Existing Inputs

Use preflight for external templates or existing `.docx` inputs before editing or template-fill work. It normalizes only the `fixable` case and leaves `invalid` inputs untouched so the visible debug workspace can be inspected.

```bash
cd <task-directory>
<skill-path>/scripts/docx preflight ./incoming.docx
```

Preflight is an earlier safety screen, not a replacement for final validation.

### 1.5 Validate Existing Documents

```bash
cd <task-directory>
<skill-path>/scripts/docx validate ./report.docx
```

### 1.6 Content Verification (Mandatory)

**pandoc is the SOURCE OF TRUTH.** OpenXML validator checks structure; pandoc shows actual visible content.

Before delivery, verify with pandoc:
- `pandoc <generated-file>.docx -t plain` - check text completeness
- For revisions/comments: add `--track-changes=all` to verify marker positions

**Critical**: `comments.xml` exists != comments visible. Count mismatch means `doc_tree` was not saved. Use [`EditingGuide.md`](./EditingGuide.md) sections `1.5 Verification` and `3.2 Verification Failed` if the editing-visible output does not match expectations.

---

## 2. Delivery Standards

### 2.1 Delivery Standard

**Generic styling and mediocre aesthetics = mediocre delivery.**

Deliver studio-quality Word documents with deep thought on content, functionality, and styling. Users often do not explicitly request advanced features (covers, TOC, backgrounds, back covers, footnotes, charts). Understand the scenario and extend it professionally.

### 2.2 Language Consistency

**Document language = user conversation language** (including filename, body text, headings, headers, TOC hints, chart labels, and every other visible string).

### 2.3 Headers and Footers

Most documents **must** include headers and footers. The specific style should match the document's design.

- **Header**: typically document title, company name, or chapter name
- **Footer**: typically page numbers (`X / Y`, `Page X`, `- X -`, etc.)
- **Cover/Back cover**: use `TitlePage` to hide header/footer on the first page

### 2.4 Professional Elements

Create documents that exceed user expectations and proactively add professional elements.

**Cover and visual treatment:**
- Formal documents (proposals, reports, financials, bids, contracts) and creative deliverables (invitations, greeting cards) should usually have **cover and back cover**
- Covers should have designer-quality background images
- Body pages can optionally use subtle backgrounds when it improves the result

**Structure:**
- Long documents (3+ sections) should add a TOC and must add a refresh hint after the TOC

**Data presentation:**
- Use charts instead of plain text lists when comparing data or showing trends
- Tables should use light gray headers or a three-line style, not Word default blue

**Links and references:**
- URLs must be clickable hyperlinks
- Multiple figures/tables should use numbering and cross-references (`see Figure 1`, `as shown in Table 2`)
- Academic/legal/data-analysis citation scenarios should implement correct click-to-jump references with matching footnotes/endnotes

### 2.5 TOC Refresh Hint

Word TOC is field code, so page numbers may be inaccurate when generated. **Add subtle gray hint text after the TOC** telling the user to refresh it manually on first open.

Example:

```text
Table of Contents
─────────────────
Chapter 1 Overview .......................... 1
Chapter 2 Methods ........................... 3
...

(Hint: On first open, right-click the TOC and select "Update Field" to show correct page numbers)
```

Hint requirements:
- visually subtle
- smaller font size
- should not compete with the actual TOC entries
- language must match the user conversation language

### 2.6 Only When Explicitly Requested

| Feature | Reason |
|---------|--------|
| Watermark | Changes visual state. **SDK limitation**: VML watermark classes do not serialize correctly; must write raw XML to the header |
| Document protection | Restricts editing |
| Mail merge fields | Requires a data source |

### 2.7 Chart Selection Strategy

**Default to native Word charts** - editable, small file size, professional.

| Chart Type | Method | Notes |
|------------|--------|-------|
| Pie chart | **Native** | `Example.cs` -> `AddPieChart()` |
| Bar chart | **Native** | `Example.cs` -> `AddBarChart()` |
| Line chart | **Native** | Reference bar chart structure, use `c:lineChart` |
| Horizontal bar | **Native** | Reference bar chart structure, use `barDir="bar"` |
| Heatmap, 3D, radar | matplotlib | Word native does not support these |
| Complex statistics (box plot, etc.) | matplotlib | Word native does not support these |

Native charts are preferred, but matplotlib is acceptable for data-analysis scenarios that need unsupported visual types.

### 2.8 Inserting Images and Charts

Any PNG (matplotlib charts, backgrounds, photos) must be inserted using `AddInlineImage()`:

```csharp
AddInlineImage(body, mainPart, "/path/to/image.png", "Description", docPrId++);
```

Critical points:
- chart labels and titles must match document language
- build output should show `X images`; if it shows `0`, the images were not inserted

### 2.9 Content Constraints

#### Word and Page Count Requirements

| User Request | Execution Standard |
|--------------|-------------------|
| Specific word count (for example `3000 words`) | Actual output within +/-20% |
| Specific page count (for example `5 pages`) | Exact match |
| Range (for example `2000-3000 words`) | Within range |
| Minimum (for example `at least 5000 words`) | No more than 2x the requirement |

**Forbidden**: padding word count with excessive bullet lists. Maintain information density.

#### Outline Adherence

- **User provides outline**: follow strictly, no additions, deletions, or reordering
- **No outline provided**: use a standard structure that matches the document type
  - Academic: Introduction -> Literature -> Methods -> Results -> Discussion -> Conclusion
  - Business: Executive Summary -> Analysis -> Recommendations
  - Technical: Overview -> Principles -> Usage -> Examples -> FAQ

#### Scene Completeness

Think one step ahead of the user and complete the elements the scenario obviously needs.

- **Exam paper** -> name/class/ID fields, point allocation, grading section
- **Contract** -> signature and seal areas for both parties, date, contract number, attachment list
- **Meeting minutes** -> attendees, absentees, action items with owners, next meeting time

### 2.10 Design Philosophy

#### Color Scheme

Use **low saturation tones** and avoid Word default blue plus matplotlib default high saturation.

Suggested directions:

| Style | Palette | Suitable Scenarios |
|-------|---------|-------------------|
| Morandi | Soft muted tones | Artistic, editorial |
| Earth tones | Brown, olive, natural | Environmental, organic |
| Nordic | Cool gray, misty blue | Minimalist, tech |
| Japanese Wabi-sabi | Gray, raw wood, zen | Traditional, contemplative |
| French elegance | Off-white, dusty pink | Luxury, feminine |
| Industrial | Charcoal, rust, concrete | Manufacturing, engineering |
| Academic | Navy, burgundy, ivory | Research, education |
| Ocean mist | Misty blue, sand | Marine, wellness |
| Forest moss | Olive, moss green | Nature, sustainability |
| Desert dusk | Ochre, sandy gold | Warm, regional |

**Color scheme must stay consistent within the same document.**

#### Layout

Use white space (margins, paragraph spacing), clear hierarchy (H1 > H2 > body), and proper padding so text does not touch borders.

#### Pagination Control

Word uses flow layout, not fixed pages. Control pagination with these properties:

| Property | XML | Effect |
|----------|-----|--------|
| Keep with next | `<w:keepNext/>` | Heading stays on the same page as the following paragraph |
| Keep lines together | `<w:keepLines/>` | Paragraph will not break across pages |
| Page break before | `<w:pageBreakBefore/>` | Force a new page (useful for H1) |
| Widow/orphan control | `<w:widowControl/>` | Prevent single lines at top/bottom of page |

```csharp
new ParagraphProperties(
    new ParagraphStyleId { Val = "Heading1" },
    new PageBreakBefore(),
    new KeepNext(),
    new KeepLines()
)
```

Table pagination:

```csharp
new TableRowProperties(
    new CantSplit { Val = false }
)

new TableRowProperties(
    new TableHeader()
)
```

---

## 3. SDK Fundamentals

### 3.1 Schema Compliance

OpenXML has strict element ordering requirements. **Wrong order = Word cannot open the file.**

#### Required Styles

```csharp
styles.Append(new Style(
    new StyleName { Val = "Normal" },
    new StyleParagraphProperties(
        new SpacingBetweenLines { After = "200", Line = "276", LineRule = LineSpacingRuleValues.Auto }
    ),
    new StyleRunProperties(
        new RunFonts { Ascii = "Calibri", HighAnsi = "Calibri" },
        new FontSize { Val = "22" },
        new FontSizeComplexScript { Val = "22" }
    )
) { Type = StyleValues.Paragraph, StyleId = "Normal", Default = true });
```

#### Element Order Rules

Most ordering issues are auto-fixed by `fix_element_order.py`. Key rules:

| Parent | Key Rule |
|--------|----------|
| `sectPr` | `headerRef` -> `footerRef` must come before `pgSz` -> `pgMar` |
| `Table` | Must have `tblGrid` between `tblPr` and `tr` |

#### Tables Must Have `tblGrid`

```csharp
var table = new Table();
table.Append(new TableProperties(...));
table.Append(new TableGrid(
    new GridColumn { Width = "4680" },
    new GridColumn { Width = "4680" }
));
table.Append(new TableRow(...));
```

Missing `tblGrid` is a document-corrupting mistake.

#### Table Column Width Consistency

Main cause of skewed tables: `gridCol` width in `tblGrid` does not match the cell's `tcW` width.

```csharp
table.Append(new TableGrid(
    new GridColumn { Width = "3600" },
    new GridColumn { Width = "5400" }
));

var row = new TableRow(
    new TableCell(
        new TableCellProperties(
            new TableCellWidth { Width = "3600", Type = TableWidthUnitValues.Dxa }
        ),
        new Paragraph(new Run(new Text("Content")))
    ),
    new TableCell(
        new TableCellProperties(
            new TableCellWidth { Width = "5400", Type = TableWidthUnitValues.Dxa }
        ),
        new Paragraph(new Run(new Text("Content")))
    )
);
```

| Rule | Reason |
|------|--------|
| gridCol count = table column count | Otherwise column width calculation fails |
| gridCol.Width = tcW.Width | Mismatch causes skewing |
| All rows in the same column use the same tcW | Maintains column width consistency |

#### Value Limits

- `paraId` must be < `0x80000000` for comment paragraph IDs

### 3.2 Creation vs Editing

| Task | Method | Why |
|------|--------|-----|
| Create new document | C# OpenXML SDK | Handles package structure, relationships, and content types automatically |
| Edit existing document | Python + lxml | Transparent, low-level control |

For creation work, stay in this guide plus `Example.cs` / `CJKExample.cs`. For editing work, switch to [`EditingGuide.md`](./EditingGuide.md).

---

## 4. Template and Example References

### 4.1 Example.cs

**Read the entire file to understand the overall structure**, not just isolated helper functions. The file demonstrates how sections connect (cover -> TOC -> body -> back cover).

The content values inside Example are placeholders only; the structure is what matters.

| What to Learn | What NOT to Learn |
|---------------|-------------------|
| Section division (cover -> TOC -> body -> back cover) | Specific color values |
| Floating background insertion code | Placeholder business copy |
| Chart creation API calls | Hardcoded wording/data |
| Style definition structure | The example's exact aesthetic |

Do not copy the example's color scheme directly. Redesign it for the current scenario.

Common functions worth locating in the source:
- `AddStyles()`
- `AddCoverSection()`
- `AddTocSection()`
- `AddContentSection()`
- `AddBackcoverSection()`
- `CreateFloatingBackground()`
- `AddInlineImage()`
- `CreateDataTable()`
- `AddPieChart()`
- `AddBarChart()`
- `CreatePageNumberField()`
- `CreateTotalPagesField()`
- `AddFootnote()`
- `CreateCrossReference()`

### 4.2 CJKExample.cs

**CJK documents should read `CJKExample.cs` instead of `Example.cs`** if the task is primarily Chinese or other CJK-heavy output.

It handles:
- quote escaping (`""` -> `\u201c` `\u201d`)
- CJK font configuration (`SimHei`, `Microsoft YaHei`)
- paragraph indentation for CJK text

Structure is parallel to `Example.cs`; you usually do not need to read both for the same task.

---

## 5. Content Elements

### 5.1 Field Codes

PAGE / NUMPAGES / DATE / TOC structure:

`FieldChar(Begin)` -> `FieldCode(" PAGE ")` -> `FieldChar(Separate)` -> `Text` -> `FieldChar(End)`

Results are cached; WPS does not support `UpdateFieldsOnOpen`.

### 5.2 Bookmarks and Cross-References

Bookmarks mark positions with `BookmarkStart` / `BookmarkEnd`. Cross-references link via REF fields such as `" REF bookmarkName \\h "`.

Pitfall: deleting bookmarked text deletes the bookmark and causes `Error! Reference source not found`.

---

## 6. Visual Design

### 6.1 Background Image Design

Cover/back cover should have backgrounds. Background images should keep center white space, use low-saturation colors, and contain **no text**. Add the text in Word so it stays editable.

#### Design Flow

1. Read `scripts/generate_backgrounds.py` or `scripts/generate_inkwash_backgrounds.py` for HTML/CSS techniques
2. Pick a direction that matches the document scenario
3. Create original HTML/CSS for the current job instead of cloning an old design
4. Helper scripts write local PNGs to the current directory unless you pass an output directory or set `DOCX_ASSET_OUTPUT_DIR`

#### Style Reference

| Style | Key Elements | Scenarios |
|-------|--------------|-----------|
| MUJI | Thin borders + white space | Minimalist, Japanese, lifestyle |
| Bauhaus | Scattered geometric shapes | Art, design, creative |
| Swiss Style | Grid lines + accent bars | Professional, corporate |
| Soft Blocks | Soft color rectangles, overlapping transparent layers | Warm, education, healthcare |
| Rounded Geometry | Rounded rectangles, pill shapes | Tech, internet, youthful |
| Frosted Glass | Blur + transparency + subtle borders | Modern, premium, tech |
| Gradient Ribbons | Soft gradient ellipses + small dots | Feminine, beauty, soft |
| Dot Matrix | Regular dot pattern texture | Technical, data, engineering |
| Double Border | Nested borders + corner decorations | Traditional, formal, legal |
| Waves | Bottom SVG waves + gradient background | Ocean, environmental, flowing |
| Warm Natural | Earth tones + organic shapes | Environmental, agriculture, natural |

Technical note: Playwright generates `794x1123px` (`device_scale_factor=2`). Insert the result as a floating anchor with `BehindDoc=true`. See `CreateFloatingBackground()` in `Example.cs`.

### 6.2 Letterhead

For formal business letters, consider a letterhead in the header area:
- full letterhead on the first page
- simplified or hidden on subsequent pages
- use `TitlePage` to enable a different first-page header

### 6.3 Two-Column Layout

Use `sectPr` with `Columns`. It affects the entire section until the next `sectPr`.

---

## 7. Special Content

### 7.1 Math Formulas (OMML)

Core pattern: `<m:e>` is the universal content container.

- Text should be `<m:r><m:t>text</m:t></m:r>`
- Root should be `<m:oMath>` (inline) or `<m:oMathPara>` (display)
- Do not nest `<m:oMath>` inside another `<m:oMath>`

| Element | Structure |
|---------|-----------|
| Fraction | `<m:f><m:num><m:e>...</m:e></m:num><m:den><m:e>...</m:e></m:den></m:f>` |
| Subscript | `<m:sSub><m:e>base</m:e><m:sub><m:e>...</m:e></m:sub></m:sSub>` |
| Superscript | `<m:sSup><m:e>base</m:e><m:sup><m:e>...</m:e></m:sup></m:sSup>` |
| Radical | `<m:rad><m:deg><m:e>n</m:e></m:deg><m:e>radicand</m:e></m:rad>` |
| Matrix | `<m:m><m:mr><m:e>cell</m:e><m:e>cell</m:e></m:mr></m:m>` |
| Nary | `<m:nary><m:sub><m:e>...</m:e></m:sub><m:sup><m:e>...</m:e></m:sup><m:e>body</m:e></m:nary>` |
| Delimiter | `<m:d><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr><m:e>...</m:e></m:d>` |
| Equation array | `<m:eqArr><m:e>eq1</m:e><m:e>eq2</m:e></m:eqArr>` |

Matrix trap: use `<m:e>` for cells, not `<m:mc>`.

### 7.2 Curly Quotes in C# Strings

C# treats `"` as a string delimiter. If curly quotes are needed in output, use Unicode escapes.

```csharp
// Wrong
new Text("请点击"确定"按钮")

// Correct
new Text("请点击\u201c确定\u201d按钮")
```

| Character | Unicode | Usage |
|-----------|---------|-------|
| left double quote | `\u201c` | Opening quote |
| right double quote | `\u201d` | Closing quote |
| left single quote | `\u2018` | Opening single |
| right single quote | `\u2019` | Closing single |

Do not use verbatim strings `@""` when you need `\u` escapes.

### 7.3 Units

- Twips = 1/20 pt (`11906` = A4 width)
- Half-points for font size (`24` = 12pt)
- EMU = `914400` per inch

---

## 8. Page Layout

### 8.1 Image Size

`wp:extent` and `a:ext` `Cx/Cy` must match. For proportional scaling, read the PNG header (bytes 16-23) and calculate `cy = cx * height / width`.

### 8.2 Pagination Control

Add `KeepNext` to title/chart paragraphs to prevent orphaned titles or title-caption separation.

### 8.3 Section Breaks

`sectPr` inside `pPr` marks the last paragraph of a section. Avoid `PageBreak` + `Continuous`, which can create blank pages. Use `NextPage`.

### 8.4 Table of Contents (TOC)

WPS does not support `UpdateFieldsOnOpen`, so pre-populate TOC entries using **field code structure**:

`FieldChar(Begin)` -> `FieldCode(" TOC ...")` -> `FieldChar(Separate)` -> placeholder entries -> `FieldChar(End)`

Do not simulate a TOC with static paragraphs. It must be a real field code so users can refresh it.

Parameters:
- `\o "1-3"` - heading levels
- `\h` - hyperlinks
- `\z` - hide page numbers in web view
- `\u` - outline level

Headings must use built-in `Heading1` / `Heading2` styles.

### 8.5 Alignment and Typography

- CJK body: justify + 2-char indent
- English body: left align
- Table numbers: right align
- Headings: no indent

---

## 9. Page Elements

### 9.1 Headers and Footers

```csharp
var headerPart = mainPart.AddNewPart<HeaderPart>();
var headerId = mainPart.GetIdOfPart(headerPart);

headerPart.Header = new Header(
    new Paragraph(
        new ParagraphProperties(
            new ParagraphStyleId { Val = "Header" },
            new Justification { Val = JustificationValues.Center }
        ),
        new Run(new Text("Document Title"))
    )
);

var footerPart = mainPart.AddNewPart<FooterPart>();
var footerId = mainPart.GetIdOfPart(footerPart);

var footerPara = new Paragraph(
    new ParagraphProperties(
        new Justification { Val = JustificationValues.Center }
    )
);
footerPara.Append(new Run(new FieldChar { FieldCharType = FieldCharValues.Begin }));
footerPara.Append(new Run(new FieldCode(" PAGE ")));
footerPara.Append(new Run(new FieldChar { FieldCharType = FieldCharValues.Separate }));
footerPara.Append(new Run(new Text("1")));
footerPara.Append(new Run(new FieldChar { FieldCharType = FieldCharValues.End }));
footerPara.Append(new Run(new Text(" / ") { Space = SpaceProcessingModeValues.Preserve }));
footerPara.Append(new Run(new FieldChar { FieldCharType = FieldCharValues.Begin }));
footerPara.Append(new Run(new FieldCode(" NUMPAGES ")));
footerPara.Append(new Run(new FieldChar { FieldCharType = FieldCharValues.Separate }));
footerPara.Append(new Run(new Text("1")));
footerPara.Append(new Run(new FieldChar { FieldCharType = FieldCharValues.End }));
footerPart.Footer = new Footer(footerPara);

new SectionProperties(
    new HeaderReference { Type = HeaderFooterValues.Default, Id = headerId },
    new FooterReference { Type = HeaderFooterValues.Default, Id = footerId },
    new PageSize { Width = 11906, Height = 16838 },
    new PageMargin { Top = 1440, Right = 1440, Bottom = 1440, Left = 1440, Header = 720, Footer = 720 }
)
```

Header/footer reference types:

| Type | HeaderFooterValues | Purpose |
|------|--------------------|---------|
| Default | `.Default` | Odd pages or all pages |
| Even | `.Even` | Even pages |
| First | `.First` | First page |

Use `TitlePage()` for different first page behavior and `<w:evenAndOddHeaders/>` for different odd/even pages.

### 9.2 Footnotes and Endnotes

FootnotesPart / EndnotesPart must include the separator entries before any user notes:

```xml
<w:footnote w:type="separator" w:id="-1">
  <w:p><w:r><w:separator/></w:r></w:p>
</w:footnote>
<w:footnote w:type="continuationSeparator" w:id="0">
  <w:p><w:r><w:continuationSeparator/></w:r></w:p>
</w:footnote>
```

Missing these causes Word to fail to render the notes correctly.

### 9.3 Lists

Lists require `NumberingDefinitionsPart` with `AbstractNum` + `NumberingInstance`. Apply through `NumberingProperties` on the paragraph.

Formats include `Decimal`, `UpperLetter`, `LowerRoman`, `Bullet`, and `ChineseCounting`.

### 9.4 Hyperlinks

Use a real `<w:hyperlink>` element, not plain text:

```csharp
var relId = mainPart.AddHyperlinkRelationship(new Uri("https://example.com"), true).Id;
paragraph.Append(new Hyperlink(new Run(
    new RunProperties(new Color { Val = "0563C1" }, new Underline { Val = UnderlineValues.Single }),
    new Text("Click here")
)) { Id = relId });
```

### 9.5 Charts and Visualization

| Requirement | Preferred | Alternative |
|-------------|-----------|-------------|
| Data charts | Word native | matplotlib PNG |
| Flowcharts | DrawingML shapes | Table layout |
| Illustrations | Image generation | Image search |

For Word charts, use `NumberLiteral` rather than Excel workbooks. For matplotlib, use `dpi=300` and ensure labels match document language.

---

## 10. XML Quick Reference

### 10.1 Text Formatting (`rPr`)

```xml
<w:r>
  <w:rPr>
    <w:rFonts w:ascii="Times New Roman" w:eastAsia="SimSun"/>
    <w:sz w:val="24"/>
    <w:b/><w:i/><w:u w:val="single"/>
    <w:color w:val="FF0000"/>
  </w:rPr>
  <w:t>text</w:t>
</w:r>
```

Common font sizes:
- `21` = 10.5pt
- `24` = 12pt
- `28` = 14pt
- `32` = 16pt
- `44` = 22pt

### 10.2 Track Changes Structure

```xml
<w:ins w:id="1" w:author="..." w:date="...">
  <w:r><w:rPr>...</w:rPr><w:t>text</w:t></w:r>
</w:ins>

<w:del w:id="2" w:author="..." w:date="...">
  <w:r><w:rPr>...</w:rPr><w:delText>text</w:delText></w:r>
</w:del>
```

Both `<w:ins>` and `<w:del>` wrap `<w:r>`. Deletions use `<w:delText>`.

### 10.3 Schema Constraints

| Rule | Requirement |
|------|-------------|
| RSID values | 8-digit uppercase hex: `00A1B2C3` |
| Whitespace | `xml:space="preserve"` for leading/trailing spaces |
| Revision structure | `<w:ins>` / `<w:del>` wrap `<w:r>` and require `w:id` |
