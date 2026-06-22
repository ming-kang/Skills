# Optional Shape Snippets

Renderer rules and **optional** literal shapes when a pictorial read helps. For everyday diagrams use `svgkit` helpers (`node`, `diamond`, `cylinder`, `lifeline`, `entity`) and the flat vocabulary in `references/shape-vocabulary.md`.

**Brand / product colors:** `references/product-colors.md` (use only when the user names a specific product).

## Rules for Self-Contained SVG

**Never use** `@import url()` for icon fonts — SVG renderers and viewers do not fetch external resources. **Always use** inline SVG `<path>`, `<circle>`, `<rect>`, `<text>` combinations. **Font fallback**: embed font-family in `<style>` using system fonts only.

---

## Prefer svgkit helpers over raw XML

| Need | Use |
|---|---|
| Rounded process / service box | `d.node(...)` |
| Flowchart decision | `d.diamond(...)` |
| Datastore cylinder | `d.cylinder(...)` |
| Sequence lifeline | `d.lifeline(...)` |
| ER entity | `d.entity(...)` |
| State pseudo-states | `d.state_dot(..., kind="initial" / "final")` |

Raw snippets below are fallbacks when not using `svgkit`.

---

## Optional literal shapes

> Meaning is normally carried by **color family** on flat rounded rects, not ornaments. Use these only when the shape itself aids reading (cylinder = storage, diamond = decision). Hairline `0.5` strokes, family colors, no gradients.

### Database / Vector Store (cylinder)

Prefer `d.cylinder(x, y, title, sub, family)`. Raw fallback:

```xml
<ellipse cx="cx" cy="top" rx="w/2" ry="w/6" fill="fill" stroke="stroke" stroke-width="0.5"/>
<rect x="cx-w/2" y="top" width="w" height="h" fill="fill" stroke="none"/>
<line x1="cx-w/2" y1="top" x2="cx-w/2" y2="top+h" stroke="stroke" stroke-width="0.5"/>
<line x1="cx+w/2" y1="top" x2="cx+w/2" y2="top+h" stroke="stroke" stroke-width="0.5"/>
<ellipse cx="cx" cy="top+h" rx="w/2" ry="w/6" fill="fill" stroke="stroke" stroke-width="0.5"/>
```

### LLM / Agent / Tool — flat rounded rect only

No special shape. See `references/svg-cookbook.md` and `references/shape-vocabulary.md`.

### Decision diamond (flowcharts)

Prefer `d.diamond(x, y, title, family)`. Raw fallback:

```xml
<polygon points="cx,cy-hh  cx+hw,cy  cx,cy+hh  cx-hw,cy"
         fill="fill" stroke="stroke" stroke-width="0.5"/>
<text x="cx" y="cy" text-anchor="middle" dominant-baseline="central"
      fill="text" font-size="14" font-weight="500">Condition?</text>
```

### User / human actor (sequence + use-case diagrams)

Prefer `d.actor(cx, y, label, family)` (use-case diagrams). Raw fallback:

```xml
<circle cx="cx" cy="cy-18" r="10" fill="fill" stroke="stroke" stroke-width="0.5"/>
<path d="M cx-14,cy+16 Q cx-14,cy-4 cx,cy-4 Q cx+14,cy-4 cx+14,cy+16"
      fill="fill" stroke="stroke" stroke-width="0.5"/>
<text x="cx" y="cy+30" text-anchor="middle" fill="text" font-size="14">User</text>
```

Arrow markers: see `references/style.md` (single open-chevron via `context-stroke`).
