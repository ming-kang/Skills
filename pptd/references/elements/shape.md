# PPTD shapes

Shared types are in [../types.md](../types.md); the 177 names and adjustments are in [../shapes.md](../shapes.md).

### Shape (shape)

```ts
interface Shape extends ElementBase {
  elementType: "shape";
  rotation?: number;                  // default: 0; degrees, clockwise rotation
  opacity?: number;                   // default: 1; constraint: [0, 1]
  flip?: [boolean, boolean];          // default: [false, false]; [horizontal flip, vertical flip]
  shapeName: string;                  // see ../shapes.md
  adjustments?: number[];             // see ../shapes.md; geometry parameters; default: the default parameter values
  viewBox?: [number, number];         // view box; used only when shapeName="custom", required in that case
  path?: string;                      // SVG shape path; used only when shapeName="custom", required in that case
  fill?: Fill;                        // default: not applied
  border?: Border;                    // default: not applied
  shadow?: Shadow;                    // default: not applied
}
```

> Custom shapes: you may specify `shapeName: "custom"` and use `viewBox` and `path` to define a custom shape; these two parameters have no effect when `shapeName` is not `custom`

> The `adjustments` parameters: reuse the parameter order and quantity defined by OOXML; see ../shapes.md for value constraints.

> **Note**: `shape` does not support embedded text! Add an extra text box to achieve that.

**custom path conventions:**
- `viewBox`: view box, the path coordinate system `[w, h]`
- `path`: SVG path string, supporting the `M / L / H / V / C / S / Q / A / Z` commands.
- Multi-segment paths are supported for shapes such as hollow-outs: make the outer contour **clockwise** (`sweep=1`) and the inner contour **counterclockwise** (`sweep=0`) to achieve a hollow cutout
- **Scaling and aspect ratio**: changing `bounds` resizes the shape (the path needs no rewriting); but the viewBox is stretched independently to bounds — when the ratios differ, the shape distorts. To keep the ratio, require `viewBoxW : viewBoxH = bounds.w : bounds.h`.

**Common shapes**

> See [shapes.md](../shapes.md) for the full 177 shapes.

| shapeName | Description | adjustments default values |
|-----------|------|-------------------|
| `rect` | Rectangle | — |
| `roundRect` | Rounded rectangle | `[16667]` (corner radius) |
| `ellipse` | Ellipse | — |
| `triangle` | Triangle | `[50000]` (horizontal position of apex) |
| `diamond` | Diamond | — |
| `homePlate` | Five-sided arrow | `[50000]` |
| `chevron` | V-shaped arrow | `[50000]` |
| `donut` | Ring | `[25000]` (ring width ratio) |
| `star5` | 5-point star | `[19098, 105146, 110557]` |
| `rightArrow` | Right arrow | `[50000, 50000]` (shaft width, arrowhead length) |
| `wedgeRectCallout` | Rectangle callout | `[-20833, 62500]` |
| `bracePair` | Brace pair | `[8333]` |

**Examples:**

```yaml
# Built-in shape
- elementId: shape-1
  elementType: shape
  bounds: [200, 200, 300, 150]
  shapeName: roundRect
  adjustments: [20000]
  fill: {type: solid, color: "$primary"}
  border: {style: solid, width: 2, color: "$accent"}

# Custom hollow ring (outer contour clockwise + inner contour counterclockwise)
- elementId: shape-2
  elementType: shape
  bounds: [400, 200, 150, 150]
  shapeName: custom
  viewBox: [1000, 1000]
  path: "M500,0 A500,500 0 1 1 499,0 Z M500,200 A300,300 0 1 0 499,200 Z"
  fill: {type: solid, color: "$accent"}
```

---
