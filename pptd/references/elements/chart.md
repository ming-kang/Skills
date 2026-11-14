# PPTD charts

## Reading index

Read [Chart](#chart), [ChartData](#chartdata), [General Rules](#general-rules) and [style precedence](#3-chart-styles) first. Then read only the series and components you use. Shared colors/fonts/borders/fills are in [../types.md](../types.md).

| Need | Sections |
|---|---|
| Cartesian charts | [bar](#bar), [line](#line), [area](#area), [scatter](#scatter), [bubble](#bubble), [candlestick](#candlestick); [AxisConfig](#axisconfig) |
| Composition / profiles | [pie](#pie), [radar](#radar); [SpokeAxisConfig](#spokeaxisconfig) |
| Changes / advanced SVG charts | [waterfall](#waterfall), [heatmap](#heatmap), [treemap](#treemap), [sunburst](#sunburst), [sankey](#sankey) |
| Titles / legends / labels / markers / defaults | [TitleConfig](#titleconfig), [LegendConfig](#legendconfig), [DataLabelConfig](#datalabelconfig), [MarkerConfig](#markerconfig), [SeriesDefaults](#seriesdefaults) |
| Mapping / mixing / color recipes | [Field Quick Reference](#field-quick-reference) |
| Worked YAML | [Examples](#examples), only if needed |

#### 3. Chart Styles

Charts involve multiple kinds of styles (series body colors, fonts, data labels, axis/legend visibility, etc.), each with its own independent priority chain, explained below.

**3.1 Series body color priority chain:**
1. A series' explicit `fill` / `lineColor` / `areaColor` (field names differ per type; see [Color Mechanism](#52-color-mechanism))
2. The same-named field for the corresponding type in [Chart.seriesDefaults](#seriesdefaults)
3. The writer's native default color cycle (`#1783FF`, `#68B8A8`, `#C9A86A`, `#8C84C9`, …). Theme tokens apply only where explicitly referenced; arbitrary `Theme.colors` entries are not an automatic series palette.

> [scatter](#scatter) is an exception: marker color resolves as `marker.fill > series.fill > theme color cycle`; marker.border likewise takes precedence over series.border.
>
> For each type's specific color fields, derivation rules, and role mappings, see [§5.2 Color Mechanism](#52-color-mechanism).

**3.2 Font priority chain:**
1. Sub-component `fontFamily` ([TitleConfig](#titleconfig) / [LegendConfig](#legendconfig) / [DataLabelConfig](#datalabelconfig) / [AxisConfig.label](#axisconfig) / [SpokeAxisConfig.label](#spokeaxisconfig))
2. [Chart.fontFamily](#chart)
3. Theme default ([Theme](../pptd.md#theme) or the PPTX master font)

**3.3 dataLabels priority chain:**
1. `series[i].dataLabels`
2. [Chart.dataLabels](#chart) (global default)
3. Not shown (equivalent to `show: false`)

> Sub-fields follow a **one-level shallow merge**: `series.dataLabels` only overrides the sub-fields it explicitly provides; unprovided ones fall back from [Chart.dataLabels](#chart); if neither provides them, the per-type default applies (see [dataLabels.content value quick reference](#55-datalabelscontent-value-quick-reference)).

**3.4 `seriesDefaults` merge rules:**

[Chart.seriesDefaults](#seriesdefaults)`[type]` provides common defaults for all series of that type, merged with each series via a **one-level deep merge**:
- **Scalar fields** (string / number / boolean): the series' explicit value overrides defaults
- **Object fields** (`marker` / `dataLabels` / `border` / `upBars` / `downBars` / `totalBars` / gradient `fill` objects, etc.): recursive one-level shallow merge — same-named fields of defaults and series are spread respectively, with sub-fields overridden by the nearest source
- **Array fields** (`fill: []` / `colorScheme: []`): the series replaces defaults as a whole, with no element-level merging
- `type` and `encode` are not allowed inside seriesDefaults
- Only multi-series types support seriesDefaults: `bar / line / area / scatter / bubble / candlestick / radar`

Counterintuitive example:
```yaml
seriesDefaults:
  bar: {marker: {shape: circle, size: 8}}
series:
  - type: bar
    marker: {size: 12}     # after merge: {shape: circle, size: 12}, not {size: 12}
```

**3.5 `boolean | Config` field convention:**

Fields of the form `boolean | XxxConfig` (`marker` / `legend` / `AxisConfig.label / axisLine / gridLine` / `SpokeAxisConfig.label / axisLine / gridLine` / `colorbar`) uniformly follow:
- `false` = off
- `true` = on with default configuration
- Object `{...}` = on + custom configuration

> **The only exception**: [scatter.marker](#scatter) cannot be `false` (a scatter plot without a marker has nothing to render).

---

### Chart (charts)

PPTD v2's chart element follows the ECharts philosophy: **the chart top level carries no `type` field**; each `series[i].type` determines its own form. 13 series types are supported in total, laid out flat by type name, all equal in status:

`bar` / `line` / `area` / `scatter` / `bubble` / `candlestick` / `pie` / `radar` / `waterfall` / `heatmap` / `treemap` / `sunburst` / `sankey`

> **Local PPTX export:** `heatmap`, `treemap`, `sunburst`, and `sankey` use the bundled browser-free SVG renderer. They become SVG pictures, not native PowerPoint chart objects; the other types retain the WASM writer's native chart path. Keep the normal `chart` schema below: rendering is automatic, the `.page` source stays unchanged, and the chart definition is retained in the SVG's `pptd:source` metadata. The four advanced types each require a single series. Like native charts, series without an explicit `fill` use the writer's default color cycle (`#1783FF`, `#68B8A8`, `#C9A86A`, `#8C84C9`, …); `Theme.colors` tokens apply where referenced. The chart's `fill`, `border`, and `shadow` are exported as native rectangles around the picture and share its animations. Labels without an explicit `color` are white or dark depending on the fill beneath them. Export errors include the page and element ID; they are never replaced silently with a bar chart. SVG-capable playback software is required, with no PNG fallback.

Each type declares its **series constraint** on the first line of its own subsection: the maximum count allowed within the same chart + which other types it may coexist with.

#### Chart

```ts
interface Chart extends ElementBase {
  elementType: "chart";

  data: ChartData;                            // required
  series: SeriesConfig[];                     // required; constraint: length ≥ 1
  seriesDefaults?: SeriesDefaults;            // default: not applied; common defaults grouped by series.type, merged with each series

  // —— Cartesian coordinate system (conditionally effective by series.type, see §5.3) ——
  xAxis?: AxisConfig | AxisConfig[];          // default: auto-adapt to data; in array form, referenced via series[i].xAxisIndex
  yAxis?: AxisConfig | AxisConfig[];          // default: auto-adapt to data; in array form, referenced via series[i].yAxisIndex
  barWidth?: number;                          // default: adaptive; constraint: (0, 1]; bar width / category slot width ratio
  barGap?: number;                            // default: 0 (flush); constraint: [0, 1); gap between bars when multiple bar series are grouped
  categoryGap?: number;                       // default: 0.2; constraint: [0, 1); blank ratio between category slots

  // —— Radar coordinate system (radar series only) ——
  spokeAxis?: SpokeAxisConfig;                // default: auto-adapt to data; spoke axes + spider grid

  // —— Global components ——
  title?: string | TitleConfig;               // default: no title
  legend?: boolean | LegendConfig;            // default: varies by type (see the default-value table in [LegendConfig](#legendconfig))
  dataLabels?: DataLabelConfig;               // default: not applied; global default, can be overridden by series.dataLabels
  fontFamily?: FontFamily;                    // default: falls back along the theme/master fonts

  // —— Chart frame (controls the rectangular container of the whole chart element, independent of series colors) ——
  fill?: Fill;                                // default: not applied
  border?: Border;                            // default: not applied
  shadow?: Shadow;                            // default: not applied
}

type SeriesConfig =
  | BarSeries | LineSeries | AreaSeries | ScatterSeries | BubbleSeries
  | CandlestickSeries | PieSeries | RadarSeries | WaterfallSeries
  | HeatmapSeries | TreemapSeries | SunburstSeries | SankeySeries;
```

> `fill` / `border` / `shadow` control the **chart element's rectangular frame** (acting on the whole chart container), independent of the series body colors.
>
> **PowerPoint limitation:** native charts cannot be rotated/flipped as a whole; there is also no single global opacity property covering "the whole chart including title, axes, legend, labels, and series". When whole rotation/flip/opacity is needed, render as an image first and treat it as an [Image](image.md#image-image) element.

#### ChartData

```ts
interface ChartData {
  cols: string[];                                   // column names; constraint: unique, non-empty strings
  rows: (number | string | boolean | null)[][];     // booleans are for waterfall isTotal; each row's length = cols.length
}
```

> **Data integrity constraints** (validated by the checker):
> - Duplicate column names in `cols` → `DuplicateColumnError`
> - `cols` contains an empty string → `EmptyColumnError`
> - `rows[i].length !== cols.length` → `RowLengthError`
> - A column name referenced by encode is not in `cols` → `UnknownColumnError`
> - It is legal for the same column to be referenced by multiple series (e.g., the same y column drawn once by bar and once by line)
> - When a column value of a numeric channel (`y` / `value` / `open` / `high` / `low` / `close` / `size` / `flow`) is a string, it is parsed as a number; on failure, `NonNumericValueError` is raised
>
> **How to write missing cells**: fill with `null`, e.g. `[null, null, 2, 3]`. Consecutive commas `[, , 2, 3]` are **not recommended** — strict YAML parsers will error.

#### General Rules

1. **The `fill` type of series**: `Color | GradientFill`; a string is treated as a solid [Color](../types.md#color) (HEX8 or a `$xxx` theme reference), an object as [GradientFill](../types.md#fill) (with `type: "gradient"`); some types support the `(Color | GradientFill)[]` array form (cycled by slice/node). **Series-level fill does not support [ImageFill](../types.md#fill)**.
2. **Type mixing**: which types a chart's `series[]` may contain is determined by the "series constraint" on the first line of each type's section; the checker validates accordingly.
3. **Conditionally effective top-level fields**: `xAxis` / `yAxis` / `barWidth` / `barGap` / `categoryGap` / `spokeAxis` are **coordinate-system-level** configurations, conditionally effective based on the `series[].type` set (see [5.3 Applicability of chart top-level fields](#53-applicability-of-chart-top-level-fields) for details).
4. **[Color](../types.md#color) theme reference scope**: all fields of type `Color` (including every Color position inside nested arrays and objects) support `$xxx` theme references — e.g. `upBars: {fill: "$success"}`, `colorScheme: ["$bg", "$primary"]`, `fill: ["$primary", "$accent"]`.
5. **Omission semantics of optional object-type fields**: all **object-type** fields marked with `?` (`xAxis` / `yAxis` / `spokeAxis` / `colorScale` / `marker` / `dataLabels`, etc.): when omitted, they are equivalent to an empty configuration `{}` of that object, and all sub-fields take their own default values — i.e., "axes/grids/labels etc. still render by default, just with automatically inferred parameters". This differs from `fill` / `border` / `shadow` of [ElementBase](../pptd.md#elementbase) (where omission means **not applied**).

> **bar / waterfall direction**: determined by the axis type — vertical (default) when `xAxis.type === "category"`, horizontal when `yAxis.type === "category"`. `axis.type` is inferred from the data column by default (string → category, number → value); when a numeric column needs to be used as categories (e.g. years), override explicitly with `axis.type: "category"`. In the horizontal case, `encode.x` references the numeric column and `encode.y` the category column, and `numberFormat` is written on the side where the value axis is. For scatter / bubble, both x and y are numeric channels, with no notion of direction.

---

#### TextStyle

```ts
interface TextStyle {
  color?: Color;            // default: falls back along the inheritance chain (theme text color / PPTX master)
  fontSize?: number;        // default: auto-adapts to chart size
  fontFamily?: FontFamily;  // default: falls back along the inheritance chain to Chart.fontFamily or the theme font
}
```

> The common trio of text styles, inherited and reused by [TitleConfig](#titleconfig) / [LegendConfig](#legendconfig) / [DataLabelConfig](#datalabelconfig) / [AxisConfig](#axisconfig).label / [SpokeAxisConfig](#spokeaxisconfig).label; for the font priority chain, see [§3.2](#3-chart-styles).

#### LineStyleConfig

```ts
interface LineStyleConfig {
  style?: "solid" | "dash" | "dot";    // default: "solid"
  color?: Color;                       // default: falls back to the theme
  width?: number;                      // default: 1
}
```

> Generic line style, reused by the `axisLine` / `gridLine` of [AxisConfig](#axisconfig) / [SpokeAxisConfig](#spokeaxisconfig).

#### TitleConfig

```ts
interface TitleConfig extends TextStyle {
  text: string;                        // required
  // fontSize auto-adapts to chart size by default
}
```

#### LegendConfig

```ts
interface LegendConfig extends TextStyle {
  show?: boolean;                      // default: varies by type (see the table below)
  position?: "top" | "bottom" | "left" | "right";  // default: "bottom"
}
```

`show` defaults by type:

| type | Default |
|---|---|
| bar / line / area / scatter / bubble / candlestick / pie / radar | `true` |
| waterfall | `false` |
| treemap / sunburst / sankey | `false` (names and values are already shown on the chart) |
| heatmap | Does not use `chart.legend` (controlled by [series.colorbar](#heatmap)) |

> `legend: false` or `legend: {show: false}` turns it off, **effective for all 13 types**; `legend: true` or the object form only has a visual effect for the types marked applicable in the table above.

#### DataLabelConfig

```ts
interface DataLabelConfig extends TextStyle {
  show?: boolean;                      // default: false
  content?: "value" | "percentage" | "category";  // default: varies by type (see [5.5 value quick reference](#55-datalabelscontent-value-quick-reference))
  numberFormat?: string;               // default: no formatting; Excel number-format string (see below)
}
```

> **numberFormat standard**: takes a subset of Excel number-format strings — `0` (integer) / `0.0` (one decimal) / `0%` (percentage) / `0.0%` (percentage with decimals) / `#,##0` (thousands separator) / `0.0E+00` (scientific notation). Advanced syntax such as `[Red]` color sections, negative sections, and conditional formatting is **not supported**.

#### MarkerConfig

```ts
interface MarkerConfig {
  shape?: "circle" | "rect" | "diamond" | "triangle";  // default: "circle"
  fill?: Color | GradientFill;         // default: follows the series body color
  border?: Border;                     // default: not applied
  size?: number;                       // default: auto-adapts to chart size; unit px
}
```

> The `rect` naming is consistent with the [shapes.md](../shapes.md) shape library.

#### AxisConfig

```ts
interface AxisConfig {
  show?: boolean;                      // default: true
  type?: "category" | "value";         // default: inferred from the data column (string → category, number → value)
  min?: number;                        // default: auto-adapt to data; only effective for value axes
  max?: number;                        // default: auto-adapt to data; only effective for value axes
  reverse?: boolean;                   // default: false; true = reverse the axis direction (maximum at the origin side)
  title?: string | TitleConfig;        // default: no title; the string form is recommended, use the object only for special styling
  label?: boolean | (TextStyle & {     // default: true; tick labels
    numberFormat?: string;             // default: no formatting; only effective for value axes
  });
  axisLine?: boolean | (LineStyleConfig & {  // default: true
    arrow?: boolean | "start" | "end" | "both";  // default: false; true is equivalent to "end"
  });
  gridLine?: boolean | LineStyleConfig;     // default: true
}
```

#### SeriesDefaults

```ts
interface SeriesDefaults {
  bar?: Partial<Omit<BarSeries, "type" | "encode">>;
  line?: Partial<Omit<LineSeries, "type" | "encode">>;
  area?: Partial<Omit<AreaSeries, "type" | "encode">>;
  scatter?: Partial<Omit<ScatterSeries, "type" | "encode">>;
  bubble?: Partial<Omit<BubbleSeries, "type" | "encode">>;
  candlestick?: Partial<Omit<CandlestickSeries, "type" | "encode">>;
  radar?: Partial<Omit<RadarSeries, "type" | "encode">>;
}
```

> Provides common default values for all series of that type, avoiding repetition across multiple series. For the merge algorithm and the range of usable types, see [§3.4](#3-chart-styles).

#### SpokeAxisConfig

Used only by [radar](#radar) series.

```ts
interface SpokeAxisConfig {
  show?: boolean;                      // default: true
  min?: number;                        // default: 0; minimum of the value axis shared by all dimensions
  max?: number;                        // default: auto-adapt to data; maximum of the value axis shared by all dimensions
  label?: boolean | (TextStyle & {     // default: true; tick labels
    numberFormat?: string;             // default: no formatting
  });
  axisLine?: boolean | LineStyleConfig;     // default: true; spoke lines from the center to the outer ring
  gridLine?: boolean | LineStyleConfig;     // default: true; spider grid lines (concentric polygons connecting the spoke endpoints)
}
```

#### LinearSeriesBase

Curve-class common fields shared by [line](#line) / [area](#area) / [radar](#radar).

```ts
interface LinearSeriesBase {
  smooth?: boolean;                                   // default: false
  lineStyle?: "solid" | "dash" | "dot";               // default: "solid"
  width?: number;                                     // default: 2
  marker?: false | MarkerConfig;                      // default: not applied
  nullHandling?: "zero" | "gap" | "connect";          // default: "gap" for line/area, "connect" for radar
  lineColor?: Color | GradientFill;                   // default: follows the theme color cycle; line color of line / polygon stroke color of area+radar
}
```

> If multiple line/area/radar series within the same chart set different `nullHandling` values, only the **first non-empty value** takes effect and the other series follow; multiple null-handling methods are not supported.

---

#### bar

> **series constraint**: may be freely mixed with `line / area / scatter / bubble`; may also mix with `candlestick`; no limit on the number of bar series in the same chart.

```ts
interface BarSeries {
  type: "bar";
  encode: { x: string; y: string };    // required
  name?: string;                       // default: the encode.y column name; for legend display only
  xAxisIndex?: number;                 // default: 0; meaningful only when chart.xAxis is an array
  yAxisIndex?: number;                 // default: 0; meaningful only when chart.yAxis is an array
  stack?: "value" | "percent";         // default: no stacking; "value" sums directly, "percent" normalizes to 100%
  symbol?: ShapeDef;                   // default: normal rectangular bar; pictographic bar shape definition (see [ShapeDef](image.md#image-image))
  fill?: Color | GradientFill;         // default: follows the theme color cycle
  border?: Border;                     // default: not applied
  dataLabels?: DataLabelConfig;        // default: not shown; content only takes "value"
}
```

#### line

> **series constraint**: may be freely mixed with `bar / area / scatter / bubble`; may also mix with `candlestick`.

```ts
interface LineSeries extends LinearSeriesBase {
  type: "line";
  encode: { x: string; y: string };    // required
  name?: string;                       // default: the encode.y column name
  xAxisIndex?: number;                 // default: 0
  yAxisIndex?: number;                 // default: 0
  dataLabels?: DataLabelConfig;        // default: not shown; content only takes "value"
}
```

> line has no area, so `fill` is not provided; for the other curve-class fields, see [LinearSeriesBase](#linearseriesbase).

#### area

> **series constraint**: may be freely mixed with `bar / line / scatter / bubble`; may also mix with `candlestick`.

```ts
interface AreaSeries extends LinearSeriesBase {
  type: "area";
  encode: { x: string; y: string };    // required
  name?: string;                       // default: the encode.y column name
  xAxisIndex?: number;                 // default: 0
  yAxisIndex?: number;                 // default: 0
  stack?: "value" | "percent" | "stream";  // default: no stacking; "stream" = streamgraph (area only)
  areaColor?: Color | GradientFill;    // default: derived from lineColor as semi-transparent
  dataLabels?: DataLabelConfig;        // default: not shown
}
```

> **Stacking group rules**: within the same chart, **all series of the same type that set `stack` are automatically grouped into one stack**, with no explicit group identifier needed. At most one stack group of the same type is supported within the same chart — all series that set `stack` must use the same value (all `"value"` / all `"percent"` / all `"stream"`); mixing raises `StackModeMismatchError`; series without `stack` display independently. If multiple independent stack groups are needed, split them into multiple chart elements.
>
> **`stream` applies only to area**: `value` normalization + central baseline offset; the stacked region is symmetric above and below y=0, taking a "streamgraph" shape.

#### scatter

> **series constraint**: may be freely mixed with `bar / line / area / bubble`.

```ts
interface ScatterSeries {
  type: "scatter";
  encode: { x: string; y: string };    // required; each series references its own x/y column pair
  name?: string;                       // default: the encode.y column name
  yAxisIndex?: number;                 // default: 0
  dataFilter?: { col: string; value: string | number };  // default: no filtering; optional: group with a long table
  marker?: MarkerConfig;               // default: {shape: "circle"}; constraint: cannot be false
  fill?: Color | GradientFill;         // default: follows the theme color cycle; serves as the marker's default fill color (marker.fill takes precedence)
  border?: Border;                     // default: not applied; serves as the marker's default border (marker.border takes precedence)
  dataLabels?: DataLabelConfig;        // default: not shown; content only takes "value"
}
```

#### bubble

> **series constraint**: may be freely mixed with `bar / line / area / scatter`.

```ts
interface BubbleSeries {
  type: "bubble";
  encode: { x: string; y: string; size: string };  // required
  name?: string;                       // default: the encode.y column name
  yAxisIndex?: number;                 // default: 0
  dataFilter?: { col: string; value: string | number };  // default: no filtering; rows where the col column equals value are used as this series' data
  sizeScale?: "linear" | "sqrt" | "log";  // default: "sqrt"
  sizeRange?: [number, number];        // default: auto-adapts to chart size; bubble radius range in px
  fill?: Color | GradientFill;         // default: follows the theme color cycle; bubble fill color
  border?: Border;                     // default: not applied
  dataLabels?: DataLabelConfig;        // default: not shown; content only takes "value"
}
```

> **sizeScale**: `sqrt` (default) makes the area proportional to size; `linear` makes the radius proportional to size; `log` suits scenarios with order-of-magnitude differences. Negative size is treated as 0. For multiple groups, use a wide table + null padding, with each series referencing its own `x/y/size` column triple.

#### candlestick

> **series constraint**: may only mix with `bar / line / area` (common usage: candlestick body + a line overlaying the MA moving average).

```ts
interface CandlestickSeries {
  type: "candlestick";
  /**
   * encode.open is optional → determines the rendering mode
   *   open provided → OHLC candlestick (rendered with 4 series; a solid body expresses the open-close direction)
   *   open omitted → HLC high-low-close (rendered with 3 series; a vertical line + dot marker at close, no body)
   */
  encode: { x: string; high: string; low: string; close: string; open?: string };
  xAxisIndex?: number;                 // default: 0
  yAxisIndex?: number;                 // default: 0
  upBars?:   { fill?: Color; border?: Border };   // rising bar (close > open) style; only effective in OHLC mode (HLC has no body)
  downBars?: { fill?: Color; border?: Border };   // falling bar (close ≤ open) style; only effective in OHLC mode
  wickStyle?: Border;                  // wick (high-low vertical line) style; common to HLC / OHLC
}
```
>
> **Date column handling**: a date column (e.g. `"2024-01-01"`) is treated as string categories, laid out at equal intervals on the x-axis in the order they appear in `rows`, naturally skipping non-trading days. If precise layout by real date intervals is needed, manually padding empty trading days with null rows is recommended.

#### pie

> **series constraint**: the `series` array may only have 1 element, and may not coexist with other types.

```ts
interface PieSeries {
  type: "pie";
  encode: { category: string; value: string };  // required
  innerRadius?: number;                // default: 0; constraint: [0, 1]; > 0 = donut
  startAngle?: number;                 // default: 0 (12 o'clock direction)
  fill?: Color | GradientFill | (Color | GradientFill)[];   // default: follows the theme color cycle; an array cycles by slice
  border?: Border;                     // default: not applied
  dataLabels?: DataLabelConfig;        // default: not shown; content takes "value" | "percentage" | "category", default "value"
}
```

> **Angle direction**: fixed **clockwise** as positive; 0° = 12 o'clock position, 90° = 3 o'clock, 180° = 6 o'clock, 270° = 9 o'clock.

#### radar

> **series constraint**: multiple radar series are allowed in the same chart (sharing one set of spokes), but the type of all series must be `radar`; it may not coexist with other types.

```ts
interface RadarSeries extends LinearSeriesBase {
  type: "radar";
  encode: { category: string; y: string };    // required; the category column holds the spoke labels
  name?: string;                       // default: the encode.y column name
  areaColor?: Color | GradientFill;    // default: derived from lineColor as semi-transparent; polygon fill color
  dataLabels?: DataLabelConfig;        // default: not shown; content only takes "value"
}
```

> The radar chart's spoke axis lines, spider grid, and value range (min/max) are uniformly configured via the chart top-level [spokeAxis](#spokeaxisconfig), shared by multiple series.
>
> **Dimension-column sharing constraint**: all radar series within the same chart must reference the same `category` column (i.e., all polygons share the same set of spoke labels). To display radar charts with different spoke labels, use multiple chart elements. Checker validation: the `encode.category` of all radar series must be identical.

#### waterfall

> **series constraint**: the `series` array may only have 1 element, and may not coexist with other types.

```ts
interface WaterfallSeries {
  type: "waterfall";
  encode: {
    x: string;                         // category column
    y: string;                         // value column (floating bars hold the increase/decrease amounts; total columns hold the absolute value of the cumulative total)
    isTotal?: string;                  // default: omitted = all floating bars; after specifying a bool column, true = total column (opening/subtotal/closing), false/null = floating bar
  };
  totalBars?:    { fill?: Color; border?: Border };   // total column (opening/subtotal/closing, isTotal=true) style
  increaseBars?: { fill?: Color; border?: Border };   // floating increase bar (y > 0) style
  decreaseBars?: { fill?: Color; border?: Border };   // floating decrease bar (y < 0) style
  dataLabels?: DataLabelConfig;        // default: not shown; content takes "value" | "category", default "value"
}
```

> **Colors**: waterfall does not use `fill`; colors are mapped through the three categories `totalBars` / `increaseBars` / `decreaseBars` by isTotal and the sign of y; all total columns (opening/subtotal/closing) share `totalBars`.
>
> **isTotal semantics**: it may appear at any position (first row / middle subtotal / last row are all legal); every `isTotal=true` is an independent total column whose y value should equal "previous total column's y + the sum of all intermediate floating bars' y" — on mismatch, the checker outputs `WaterfallTotalMismatchWarning` (the first-row total column's y is defined directly). The `isTotal` column only accepts bool or null; the string `"true"` or the number `1` both raise `InvalidValueError`.

#### heatmap

> **series constraint**: the `series` array may only have 1 element, and may not coexist with other types.

```ts
interface HeatmapSeries {
  type: "heatmap";
  encode: { x: string; y: string; value: string };  // required; the x and y columns must be categories (string), value is numeric
  colorScheme?: Color[];               // default: falls back to the theme; gradient color-scale endpoints
  colorScale?: {
    type?: "linear" | "diverging";     // default: "linear"
    domain?: [number, number];         // default: data range; for type=diverging, default [-max(|v|), +max(|v|)], 0 centered
  };
  colorbar?: boolean | LegendConfig;   // default: true; color-scale bar legend; position default "right"
  dataLabels?: DataLabelConfig;        // default: not shown; content only takes "value"
}
```

> **Colors**: `colorScheme` serves as gradient endpoints, interpolated per `colorScale.type`:
> - `linear`: `colorScheme` length ≥ 2, interpolated between the endpoints;
> - `diverging`: `colorScheme` length = 3 (low / mid / high); the midpoint is determined by the middle of `domain`, often used in "negative-neutral-positive" scenarios.
>
> **Data layout**: the x / y columns are fixed as categories (string); category order on the axes follows first-appearance order in `rows`; (x, y) combinations that do not appear in `rows`, or whose value is `null`, are missing cells and remain transparent. Zero is a real value, not a missing cell. Each (x, y) pair must occur at most once. For a complete matrix, explicitly listing all (x, y) combinations and using null for missing values is recommended.
>
> heatmap does not use `chart.legend`; it is replaced by `colorbar`; `colorbar: false` turns off the color-scale bar.

#### treemap

> **series constraint**: the `series` array may only have 1 element, and may not coexist with other types.

```ts
interface TreemapSeries {
  type: "treemap";
  encode: {
    category: string;                  // node-name column
    value: string;                     // value column
    parent?: string;                   // parent-node column; null/missing/empty = root node (multiple roots allowed)
  };
  levels?: number;                     // default: show all levels
  fill?: Color | GradientFill
       | (Color | GradientFill)[]
       | (Color | GradientFill)[][];   // default: follows the theme color cycle; see "color derivation rules" below
  border?: Border;                     // default: not applied
  dataLabels?: DataLabelConfig;        // default: not shown; content takes "value" | "category", default "category"
}
```

> **Color derivation rules**:
> - `fill: Color | GradientFill` (single value): all root nodes share this color; child nodes are derived by decreasing lightness by 10% per level (along the HSL.L dimension).
> - `fill: (Color | GradientFill)[]` (1-D array): cycles in the order the root nodes appear; each root node's child nodes are derived by decreasing lightness by 10% per level.
> - `fill: (Color | GradientFill)[][]` (2-D array): the outer dimension cycles by root node, the inner dimension specifies levels directly (bypassing automatic derivation); if an inner array is not long enough to cover all levels, the remaining levels are still derived by decreasing lightness by 10%.

> **Local hierarchy export (treemap and sunburst):** node names must be unique, values must be non-negative or `null`, and parent links must be acyclic. A parent referenced without its own row becomes a grouping node. A `null` grouping-node value is derived from its children; an explicit zero remains zero. When `border` is omitted, nodes are separated by a 1px white line so same-colored siblings stay distinguishable. Totals include all descendants before `levels` limits the visible depth, so hiding deeper levels does not discard their values.

#### sunburst

> **series constraint**: the `series` array may only have 1 element, and may not coexist with other types.

```ts
interface SunburstSeries {
  type: "sunburst";
  encode: { category: string; value: string; parent?: string };  // required
  levels?: number;                     // default: show all levels
  fill?: Color | GradientFill | (Color | GradientFill)[];   // default: follows the theme color cycle; an array cycles by top-level node
  border?: Border;                     // default: not applied
  dataLabels?: DataLabelConfig;        // default: not shown; content takes "value" | "category", default "category"
}
```

#### sankey

> **series constraint**: the `series` array may only have 1 element, and may not coexist with other types.

```ts
interface SankeySeries {
  type: "sankey";
  encode: {
    source: string;                    // source-node column
    target: string;                    // target-node column
    flow: string;                      // flow column
  };
  nodeAlign?: "left" | "right" | "justify";  // default: "justify"
  fill?: Color | GradientFill                     // default: follows the theme color cycle (colors picked in node topological order)
       | (Color | GradientFill)[]                // an array cycles by node
       | Record<string, Color | GradientFill>;   // mapped by node name; unspecified nodes fall back to the theme color cycle
  border?: Border;                     // default: not applied
  dataLabels?: DataLabelConfig;        // default: not shown; content takes "value" | "category", default "value"
}
```

> **Graph constraint**: sankey is restricted to a **directed acyclic graph (DAG)**. Local export rejects cycles and negative or non-numeric flows with the page and chart ID. Zero and `null` flows have no visible ribbon.
>
> **Node order**: the `source` and `target` columns are deduplicated and arranged in topological order. When `fill` is an array, it cycles in this order; when the array length < node count, it wraps around and reuses; when > node count, it truncates. The object form matches by node name exactly.

---

#### Field Quick Reference

##### 5.1 Data encode Channels

| type | encode channels |
|---|---|
| bar / line / area | `x` + `y` |
| scatter | `x` + `y` (multi-series use a wide table + null padding) |
| bubble | `x` + `y` + `size` (multi-series use a wide table + null padding) |
| candlestick | Candlestick: `x` + `open` + `close` + `low` + `high`; overlay: `x` + `y` |
| pie | `category` + `value` |
| radar | `category` + `y` |
| waterfall | `x` + `y` + optional `isTotal` (bool column) |
| heatmap | `x` + `y` + `value` |
| treemap / sunburst | `category` + `value` + optional `parent` |
| sankey | `source` + `target` + `flow` |

> **Naming convention**: Cartesian coordinate systems (bar/line/area/scatter/bubble/candlestick/waterfall/heatmap) use `x` / `y` for the horizontal/vertical axes; non-Cartesian category fields are uniformly `category` (pie/radar/treemap/sunburst); sankey graph edge endpoints use `source` / `target`.

##### 5.2 Color Mechanism

| type | Color fields | Description |
|---|---|---|
| bar | `series[].fill` | Bar body fill color |
| line | `series[].lineColor` | Line color (no area) |
| area | `series[].lineColor` + `series[].areaColor` | Stroke color + area color (when the area color is omitted, it is derived from lineColor as semi-transparent) |
| radar | `series[].lineColor` + `series[].areaColor` | Polygon stroke + fill (same as area) |
| scatter | `series[].fill` / `marker.fill` | Series level is the marker default color; `marker.fill` takes precedence |
| bubble | `series[].fill` | Bubble fill color |
| candlestick | `upBars` / `downBars` (body fill+border) + each overlay series' own `lineColor`/`fill` | The candlestick body maps by up/down; overlay line/bar use their own colors |
| pie / sunburst / sankey | The single series' `fill` array, cycled by data point/node | Array length cycles and reuses |
| treemap | The single series' `fill` (single value / 1-D array / 2-D array) | Same as pie etc.; child nodes decrease from the parent along the HSL.L dimension (`L_new = max(0, L_old - 10)`) |
| heatmap | `series[].colorScheme` + `series[].colorScale` | The gradient color scale maps by value; `linear` interpolates between the endpoints, `diverging` aligns three colors at the midpoint |
| waterfall | `series[].totalBars` / `increaseBars` / `decreaseBars` | Mapped into three classes — total (total columns) / increase / decrease; does not participate in the theme color cycle |

##### 5.3 Applicability of Chart Top-Level Fields

| Top-level field | Applicable series types |
|---|---|
| `xAxis` | bar / line / area / scatter / bubble / candlestick / waterfall / heatmap |
| `yAxis` | bar / line / area / scatter / bubble / candlestick / waterfall / heatmap |
| `barWidth` / `barGap` | bar / waterfall (bar layout parameters) |
| `categoryGap` | bar / candlestick / waterfall (category spacing parameter) |
| `spokeAxis` | radar (includes spoke axis lines + spider grid + min/max) |
| `legend` | bar / line / area / scatter / bubble / candlestick / pie / radar / waterfall |
| `title` | All |
| `dataLabels` | All (candlestick: only effective for overlay series; the candlestick body itself expresses the up/down roles via upBars/downBars) |
| `fontFamily` | All |

> **Axis single-value vs array rules**: a secondary axis is always placed on the **side where the value axis is** — vertical charts use a `yAxis` array + `yAxisIndex`, horizontal charts use an `xAxis` array + `xAxisIndex`. When any series uses `xAxisIndex > 0` / `yAxisIndex > 0`, the corresponding `xAxis` / `yAxis` must be an array (length ≥ max(index) + 1).

##### 5.4 Type-Mixing Compatibility Quick Reference

```
bar / line / area / scatter / bubble may coexist with each other freely; candlestick may only coexist with bar / line / area
```

> The other 7 types each exclusively own the series array; see the first line of the corresponding section for detailed constraints.

##### 5.5 dataLabels.content Value Quick Reference

| type | Allowed values | Default |
|---|---|---|
| bar / line / area / scatter / bubble / radar / heatmap | `value` | `value` |
| candlestick (overlay series only) | `value` | `value` |
| pie | `value` / `percentage` / `category` | `value` |
| waterfall | `value` / `category` | `value` |
| treemap / sunburst | `value` / `category` | `category` |
| sankey | `value` / `category` | `value` |

> Writing a value outside this table → the checker raises `InvalidValueError`. The candlestick body itself does not support dataLabels.

---

#### Examples

**Bar chart (stacked)**

```yaml
- elementId: c1
  elementType: chart
  bounds: [50, 100, 600, 400]
  data:
    cols: [quarter, revenue, cost]
    rows:
      - [Q1, 120, 220]
      - [Q2, 132, 182]
      - [Q3, 101, 191]
      - [Q4, 134, 234]
  seriesDefaults:
    bar: {stack: value}
  series:
    - type: bar
      encode: {x: quarter, y: revenue}
      name: Revenue
      fill: "$primary"
    - type: bar
      encode: {x: quarter, y: cost}
      name: Expenses
      fill: "$accent"
```

**Line chart (multi-series differentiation)**

```yaml
- elementId: c2
  elementType: chart
  bounds: [50, 100, 600, 400]
  data:
    cols: [month, actual, target, baseline]
    rows:
      - [Jan, 72, 65, 50]
      - [Feb, 85, 70, 50]
      - [Mar, null, 78, 50]
      - [Apr, 90, 82, 50]
  yAxis: {min: 0, max: 100, gridLine: {color: "#f0f0f0"}}
  series:
    - type: line
      encode: {x: month, y: actual}
      name: Actual
      lineColor: "#5470c6"
      lineStyle: solid
      width: 3
      smooth: true
    - type: line
      encode: {x: month, y: target}
      name: Target
      lineColor: "#ee6666"
      lineStyle: dash
      smooth: true
    - type: line
      encode: {x: month, y: baseline}
      name: Baseline
      lineColor: "#999999"
      lineStyle: dot
      width: 1
      marker: false
```

**Area chart (stream stacking)**

```yaml
- elementId: c3
  elementType: chart
  bounds: [50, 80, 700, 400]
  title: Traffic Evolution by Channel
  data:
    cols: [week, web, app, partner]
    rows:
      - [W1, 200, 120, 80]
      - [W2, 240, 160, 90]
      - [W3, 260, 200, 110]
      - [W4, 280, 240, 130]
  seriesDefaults:
    area: {stack: stream}
  series:
    - type: area
      encode: {x: week, y: web}
      name: Web
      areaColor: "#5470c6"
    - type: area
      encode: {x: week, y: app}
      name: App
      areaColor: "#91cc75"
    - type: area
      encode: {x: week, y: partner}
      name: Partner
      areaColor: "#fac858"
```

**Bubble chart (multi-series grouping)**

```yaml
- elementId: c5
  elementType: chart
  bounds: [50, 80, 700, 420]
  title: User Distribution
  xAxis: {title: Age}
  yAxis: {title: "Annual income (10K)"}
  data:
    cols: [age_s, inc_s, pop_s, age_w, inc_w, pop_w, age_m, inc_m, pop_m]
    rows:
      - [22, 5, 120, 28, 12, 380, 45, 40, 180]
      - [null, null, null, 35, 25, 260, 52, 60, 90]
  seriesDefaults:
    bubble:
      sizeScale: sqrt
      sizeRange: [8, 48]
  series:
    - type: bubble
      encode: {x: age_s, y: inc_s, size: pop_s}
      name: Students
      fill: "#5470c6"
    - type: bubble
      encode: {x: age_w, y: inc_w, size: pop_w}
      name: White-collar
      fill: "#91cc75"
    - type: bubble
      encode: {x: age_m, y: inc_m, size: pop_m}
      name: Management
      fill: "#ee6666"
```

**Candlestick chart (with MA5 overlay line)**

```yaml
- elementId: c6
  elementType: chart
  bounds: [50, 80, 700, 420]
  title: Stock Price Trend
  data:
    cols: [date, open, high, low, close, ma5]
    rows:
      - ["2024-01-01", 100, 110, 95, 108, null]
      - ["2024-01-02", 108, 115, 105, 112, null]
      - ["2024-01-03", 112, 118, 109, 116, null]
      - ["2024-01-04", 116, 120, 110, 113, null]
      - ["2024-01-05", 113, 117, 108, 115, 112.8]
  yAxis: {title: Price}
  series:
    - type: candlestick
      encode: {x: date, open: open, close: close, low: low, high: high}
      upBars: {fill: "#ee6666"}
      downBars: {fill: "#5470c6"}
    - type: line
      encode: {x: date, y: ma5}
      name: MA5
      smooth: true
      width: 2
      lineColor: "#fac858"
```

**Waterfall chart**

```yaml
- elementId: c9
  elementType: chart
  bounds: [50, 80, 700, 380]
  title: Cash Flow Waterfall
  data:
    cols: [phase, amount, total]
    rows:
      - [Opening balance, 500, true]
      - [Sales revenue, 300, null]
      - [Operating expenses, -180, null]
      - [Taxes, -60, null]
      - [Closing balance, 560, true]
  series:
    - type: waterfall
      encode: {x: phase, y: amount, isTotal: total}
      totalBars: {fill: "#5470c6"}
      increaseBars: {fill: "#91cc75"}
      decreaseBars: {fill: "#ee6666"}
      dataLabels: {show: true}
```

**Heatmap**

```yaml
- elementId: c10
  elementType: chart
  bounds: [50, 80, 700, 420]
  title: User Activity Heatmap
  data:
    cols: [hour, day, count]
    rows:
      - ["00:00", Mon, 5]
      - ["00:00", Tue, 8]
      - ["06:00", Mon, 22]
      - ["12:00", Mon, 45]
  series:
    - type: heatmap
      encode: {x: hour, y: day, value: count}
      colorScheme: ["#ffffff", "#5470c6"]
      colorScale: {domain: [0, 50]}
```

**Treemap (with hierarchy)**

```yaml
- elementId: c11
  elementType: chart
  bounds: [50, 80, 700, 420]
  title: Budget Allocation
  data:
    cols: [dept, parentDept, budget]
    rows:
      - [Engineering, null, 1000]
      - [Frontend, Engineering, 400]
      - [Backend, Engineering, 600]
      - [Sales, null, 800]
  series:
    - type: treemap
      encode: {category: dept, value: budget, parent: parentDept}
      fill: ["#5470c6", "#91cc75"]
```

**Sankey diagram**

```yaml
- elementId: c13
  elementType: chart
  bounds: [50, 80, 800, 420]
  title: User Conversion Funnel
  data:
    cols: [from, to, users]
    rows:
      - [Ad campaign, Landing page, 10000]
      - [Ad campaign, Direct search, 4000]
      - [Landing page, Sign-up, 3000]
      - [Landing page, Drop-off, 7000]
      - [Sign-up, First order, 1200]
      - [Direct search, First order, 2000]
  series:
    - type: sankey
      encode: {source: from, target: to, flow: users}
      nodeAlign: justify
      fill: ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de"]
```

**seriesDefaults + mixing: bar default width + line default smoothing**

```yaml
- elementId: c15
  elementType: chart
  bounds: [50, 80, 700, 420]
  data:
    cols: [month, sales, growth]
    rows:
      - [Jan, 120, 0.10]
      - [Feb, 150, 0.25]
      - [Mar, 180, 0.20]
  yAxis:
    - {title: Sales}
    - {title: Growth rate, label: {numberFormat: "0%"}}
  seriesDefaults:
    bar:
      fill: "#5470c6"
    line:
      smooth: true
      width: 2
      lineColor: "#ee6666"
  barWidth: 0.6
  series:
    - type: bar
      encode: {x: month, y: sales}
      name: Sales
    - type: line
      encode: {x: month, y: growth}
      name: Growth rate
      yAxisIndex: 1
```

**Horizontal bar chart (category axis on the y side)**

```yaml
- elementId: c16
  elementType: chart
  bounds: [50, 80, 600, 360]
  title: Headcount by Department
  data:
    cols: [dept, headcount]
    rows:
      - [Engineering, 120]
      - [Product, 45]
      - [Design, 30]
      - [Operations, 60]
  xAxis: {label: {numberFormat: "#,##0"}}
  yAxis: {label: {fontSize: 12}}
  series:
    - type: bar
      encode: {x: headcount, y: dept}
      fill: "$primary"
      dataLabels: {show: true}
```

---
