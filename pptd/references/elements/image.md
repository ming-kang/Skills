# PPTD images

Shared fill, crop and fit types are in [../types.md](../types.md).

### Image (image)

```ts
interface Image extends ElementBase {
  elementType: "image";
  rotation?: number;                 // default: 0; degrees, clockwise rotation
  opacity?: number;                  // default: 1; constraint: [0, 1]
  flip?: [boolean, boolean];         // default: [false, false]; [horizontal flip, vertical flip]
  src: string;                       // URL or local relative path
  cropShape?: ShapeDef;              // default: rectangle (i.e., no shape cropping)
  fit?: ImageFit;                    // default: {mode: "cover"}
  crop?: ImageCrop;                  // always applied; see the rendering order with fit/cropShape below
  border?: Border;                   // default: not applied
  shadow?: Shadow;                   // default: not applied
}

interface ShapeDef {
  shapeName: string;                 // see ../shapes.md; use "custom" for a custom path
  adjustments?: number[];            // default: use the shape's built-in defaults (see ../shapes.md)
  viewBox?: [number, number];        // used only when shapeName="custom", required in that case
  path?: string;                     // used only when shapeName="custom", required in that case
}
```

> `ShapeDef` fields correspond one-to-one with the shape fields of the [Shape](shape.md#shape-shape) element; for detailed conventions (adjustments values and angle conversion, custom path rules, hollow rules, common shape table), see the [Shape](shape.md#shape-shape) section.

**Rendering logic:** `crop` (proportionally adjust the source rectangle to get a sub-image: positive values crop inward, negative values expand outward and pad with transparent pixels) → `fit` (adapt the sub-image to the bounds container per mode) → `cropShape` (clip the final display area to the shape outline). All three can be set independently and are applied in the fixed order above.

- `fit.mode="cover"`: scale the sub-image proportionally to fill bounds; the overflow is cropped.
- `fit.mode="contain"`: scale the sub-image proportionally to display it completely; the shortfall is left blank.
- `fit.mode="fill"`: **the sub-image is stretched directly to fill bounds** — although no cropped blank edges are visible in this case, the picture content is still only the sub-region after crop, not the full original image.

**Examples:**

```yaml
- elementId: img-1
  elementType: image
  bounds: [50, 50, 400, 300]
  src: "media/cover.jpg"
  cropShape: {shapeName: roundRect, adjustments: [15000]}
  fit: {mode: cover}
  crop: {top: 0.1, bottom: 0.1, left: 0.05, right: 0.05}   # crop the surrounding proportions first, then apply cover fitting
  shadow:
    blur: 10
    color: "#00000033"
    offset: [0, 4]

# Custom clip outline
- elementId: img-2
  elementType: image
  bounds: [200, 200, 200, 200]
  src: "media/avatar.jpg"
  cropShape:
    shapeName: custom
    viewBox: [1000, 1000]
    path: "M500,0 A500,500 0 1 1 499,0 Z"
  fit: {mode: cover}
```

---
