# PPTD vector icons

Shared types are in [../types.md](../types.md).

### Icon (icon)

```ts
interface Icon extends ElementBase {
  elementType: "icon";
  rotation?: number;                 // default: 0; degrees, clockwise rotation
  opacity?: number;                  // default: 1; constraint: [0, 1]
  flip?: [boolean, boolean];         // default: [false, false]; [horizontal flip, vertical flip]
  iconName: string;                  // format "style:name"
  fill?: Fill;                       // default: black solid fill
  border?: Border;                   // default: not applied
  shadow?: Shadow;                   // default: not applied
}
```

**iconName format:** `style:name`, using the Font Awesome 7.x free icon library.

| Prefix | Style | Example |
|------|------|------|
| `fas` | Solid (most common) | `fas:house` |
| `far` | Regular | `far:heart` |
| `fab` | Brands | `fab:github` |

Icon search: https://fontawesome.com/search?ic=free-collection

**Example:**

```yaml
- elementId: icon-1
  elementType: icon
  bounds: [100, 100, 48, 48]
  iconName: "fas:lightbulb"
  fill: {type: solid, color: "$primary"}
```

---
