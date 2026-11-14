# PPTD shared types

Read only the types used by your elements. The common project contract is [pptd.md](pptd.md).

## 2. Shared Types
The following types are reused in multiple places and are defined together up front. Element sections reference them by type name without repeating the expansion

### Color
```ts
type Color = string;
```
> Supports opaque **HEX6** (`#RRGGBB`), alpha **HEX8** (`#RRGGBBAA`), and [Theme.colors](pptd.md#theme) theme color references (e.g. `$primary`)

### FontFamily
```ts
type FontFamily = string | { latin: string; ea: string };
```
| Form | Example | Description |
|------|------|------|
| String | `"MiSans"` | Chinese and English use the same font uniformly |
| Object | `{latin: "Arial", ea: "MiSans"}` | Explicitly specify Latin (latin) and East Asian (ea) fonts separately |

See [fonts.md](fonts.md) for the list of available fonts

### Alignment
```ts
type HorizontalAlign = "left" | "center" | "right" | "justify" | "distributed";
type VerticalAlign   = "top"  | "middle" | "bottom";
type Alignment       = [HorizontalAlign, VerticalAlign];
```
| Value | Description |
|----|------|
| `left` / `center` / `right` | Horizontal left / center / right alignment |
| `justify` | Justified (last line not stretched) |
| `distributed` | Distributed (last line stretched) |
| `top` / `middle` / `bottom` | Vertical top / middle / bottom alignment |

### LineStyle
```ts
type LineStyle = "solid" | "dash" | "dot";
```

### Border
```ts
interface Border {
  style?: LineStyle;  // default: "solid"
  width?: number;     // default: 1
  color?: Color;      // default: "#000000"
}
```

#### BorderSpec
[Cell](elements/table.md#cell) and [CellStyle](elements/table.md#cellstyle) support an array form of `Border` to set the four side borders separately

```ts
type BorderSpec = null
                | Border
                | [Border | null, Border | null]
                | [Border | null, Border | null, Border | null, Border | null];
```

| Form | Meaning |
|------|------|
| `null` | Explicit clear: no border on any of the four sides (used to override a border set higher up the inheritance chain)|
| `Border` | Same on all four sides |
| Two-element array `[Border\|null, Border\|null]` | `[top-bottom, left-right]` |
| Four-element array `[Border\|null, Border\|null, Border\|null, Border\|null]` | `[top, right, bottom, left]` (clockwise) |

> A `null` inside the array means no border at the corresponding position; a top-level `null` clears everything.

### Shadow

```ts
interface Shadow {
  blur: number;                // blur radius
  color: Color;
  offset?: [number, number];   // default: [0, 0]; [x, y] offset
}
```

### ColorStop

```ts
interface ColorStop {
  position: number;  // constraint: [0, 1]
  color: Color;
}
```

### ImageFit / ImageCrop

```ts
interface ImageFit {
  mode: "fill" | "contain" | "cover";
}

interface ImageCrop {
  left?: number;
  top?: number;
  right?: number;
  bottom?: number;
}
```

> **Constraint:** the four fields of `ImageCrop` are analogous, default 0. A positive value crops inward from the corresponding edge proportionally (inset); a negative value expands outward toward the corresponding edge proportionally and pads with transparent pixels (outset). Must ensure `left + right < 1` and `top + bottom < 1`, otherwise the source rectangle degenerates.

| ImageFit.mode | Description |
|---|---|
| `cover` | Fills the container, keeps aspect ratio, may crop |
| `contain` | Shows the image completely, keeps aspect ratio, may leave blank space |
| `fill` | Stretches to fill, may distort |

### Fill

```ts
type Fill = SolidFill | GradientFill | ImageFill;

interface SolidFill {
  type: "solid";
  color: Color;
}

interface GradientFill {
  type: "gradient";
  gradientType: "linear" | "radial";
  stops: ColorStop[];                // constraint: at least 2
  angle?: number;                    // default: 0; only effective for linear
}

interface ImageFill {
  type: "image";
  src: string;                       // URL or relative path
  fit?: ImageFit;                    // default: {mode: "cover"}
  crop?: ImageCrop;                  // always applied; see the rendering order with fit below
  opacity?: number;                  // default: 1; constraint: [0, 1]
}
```

> `GradientFill.angle` takes values in `[0, 360)`; `0` means left to right, increasing clockwise. Examples: `90` = top→bottom, `180` = right→left.

> **ImageFill rendering order:** `crop` (adjust the source rectangle proportionally: positive values crop inward, negative values expand outward and pad with transparent pixels) → `fit` (adapt to the fill container per mode). The specific semantics of each `fit.mode` value are consistent with the "rendering logic" discussion in the [Image](elements/image.md#image-image) section.

**Examples:**

```yaml
# Solid
fill:
  type: solid
  color: "$primary"

# Gradient
fill:
  type: gradient
  gradientType: linear
  angle: 90
  stops:
    - {position: 0, color: "$primary"}
    - {position: 1, color: "$accent"}

# Image
fill:
  type: image
  src: "media/bg.jpg"
  fit: {mode: cover}
  opacity: 0.9
```

---
