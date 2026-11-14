# PPTD lines

Shared types are in [../types.md](../types.md).

### Line (line)

```ts
type ArrowType = "arrow" | "stealth" | "diamond" | "oval";

interface Line extends ElementBase {
  elementType: "line";
  rotation?: number;                             // default: 0; degrees, clockwise rotation
  opacity?: number;                              // default: 1; constraint: [0, 1]
  flip?: [boolean, boolean];                     // default: [false, false]; [horizontal flip, vertical flip]
  viewBox: [number, number];                     // path coordinate system [w, h]; points live in this coordinate system, so changing bounds does not require changing points
  points: string;                                // bezier path points "x1,y1 x2,y2 ..."; the first/last points are the start/end the curve passes through, the middle points are control points
  curve?: "sharp" | "round" | "smooth";          // default: "round"; sharp joins / rounded joins / bezier smooth curve
  arrow?: [ArrowType | null, ArrowType | null];  // start arrow, end arrow; default: [null, null] (no arrows at either end)
  border?: Border;                               // default: not applied
  shadow?: Shadow;                               // default: not applied
}
```

> **Constraint:** `points` needs at least 2 points; the first point and the last point are points the curve passes through, the rest are bezier control points; all coordinates must be within `viewBox`.
> **viewBox vs bounds:** at render time, the viewBox is stretched independently to the bounds size; to keep the line from being stretched out of shape, require `viewBoxW : viewBoxH = bounds.w : bounds.h`.

**Examples:**

```yaml
# Normalized coordinates: from top-left to bottom-right, the two middle points are control points
- elementId: l4
  elementType: line
  bounds: [100, 100, 500, 300]
  viewBox: [1, 1]
  points: "0,0 0.2,0 0.8,1 1,1"
  curve: smooth
  border: {style: solid, width: 2, color: "$primary"}

# Bezier arc: passes through the start and end points; the two middle points control the bend direction
- elementId: bezier-arc
  elementType: line
  bounds: [50, 200, 860, 100]
  viewBox: [360, 100]
  points: "0,80 120,0 240,100 360,20"
  curve: smooth
  border: {style: solid, width: 2, color: "$primary"}
```

---
