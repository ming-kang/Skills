# PPTD element animations

The common element/ID contract is in [pptd.md](pptd.md). Slide-level fade is an export option, not an element animation.

## 6. Animations

The optional `animations` array can be used to orchestrate animations for elements on the current page. `animations` is a page-level field and references elements in the page's `elements` array through `elementId`. Array order determines the sequence relationships among animations, while `trigger` determines when each animation starts.

```ts
type AnimationEffect =
  | "appear" | "fade-in" | "fly-in" | "zoom-in" | "wipe-in" | "float-in" | "peek-in" | "rise-in"
  | "pulse" | "grow-shrink" | "spin" | "teeter" | "fill-color" | "transparency" | "color-pulse"
  | "disappear" | "fade-out" | "fly-out" | "zoom-out" | "wipe-out" | "float-out"
  | "motion-path";

type AnimationTrigger = "onClick" | "withPrevious" | "afterPrevious";
type AnimationDirection = "up" | "down" | "left" | "right";
type AnimationEasing = "linear" | "ease-in" | "ease-out" | "ease-in-out";

interface Animation {
  elementId: string;                 // required; must reference an existing element on this page
  effect: AnimationEffect;           // required; animation effect
  trigger?: AnimationTrigger;        // default: "onClick"
  direction?: AnimationDirection;    // default: "up"; only used by fly/wipe/peek/float effects
  durationMs?: number;               // default: the default duration of the corresponding effect; constraint: > 0
  delayMs?: number;                  // default: 0; constraint: >= 0
  easing?: AnimationEasing;          // default: "linear"
  repeat?: number;                   // default: 1; constraint: positive integer
  path?: string;                     // required when using motion-path
  color?: string;                    // required for fill-color / color-pulse; 6-digit HEX, with optional #
  amount?: number;                   // required for transparency; target opacity; constraint: [0, 1]
}
```

**Example:**

```yaml
elements:
  - elementId: title
    elementType: text
    bounds: [60, 40, 600, 60]
    content: {fontSize: 40, text: Title}
  - elementId: photo
    elementType: image
    bounds: [60, 140, 400, 300]
    src: media/pic.png
animations:
  - elementId: title
    effect: fade-in
    trigger: onClick
  - elementId: photo
    effect: fly-in
    direction: up
    trigger: withPrevious
  - elementId: photo
    effect: pulse
    trigger: afterPrevious
```

### Effects

- Entrance: `appear` appears immediately, `fade-in` fades in, `fly-in` flies in, `zoom-in` zooms in, `wipe-in` wipes in, `float-in` fades in with a short drift (about 10% of the page height and gentler than `fly-in`), `peek-in` slides out from behind the element's own edge mask without fading in, and `rise-in` rises linearly from below the page without fading in
- Emphasis: `pulse` pulses (scales to 110% and rebounds), `grow-shrink` scales to 150%, `spin` rotates 360°, `teeter` rocks from side to side, `fill-color` changes the fill color and preserves the result, `transparency` changes the opacity and preserves the result, and `color-pulse` changes the fill color and then restores the original color
- Exit: `disappear` disappears immediately, `fade-out` fades out, `fly-out` flies out, `zoom-out` zooms out, `wipe-out` wipes out, and `float-out` fades out with a short drift
- Path: `motion-path` moves along a path

| Effect | Default duration |
|---|---|
| `fade-in`, `fade-out`, `fly-in`, `fly-out`, `zoom-in`, `zoom-out`, `wipe-in`, `wipe-out`, `float-in`, `float-out`, `peek-in` | 500ms |
| `pulse` | 600ms |
| `grow-shrink`, `spin`, `fill-color`, `transparency`, `color-pulse` | 2000ms |
| `teeter`, `rise-in` | 1000ms |
| `motion-path` | 2000ms |
| `appear`, `disappear` | Instantaneous; ignores `durationMs` |

### Parameterized Emphasis Effects

| Effect | Parameter | Visual behavior |
|---|---|---|
| `fill-color` | `color`, required | Transitions the fill from its current color to `color` and preserves the target color after the animation ends |
| `transparency` | `amount`, required | Transitions opacity from its current value to `amount` and preserves the target opacity after the animation ends; `0` is fully transparent and `1` is fully opaque |
| `color-pulse` | `color`, required | Transitions the fill color to `color`, then restores the original color without preserving the intermediate state |

```yaml
animations:
  # Highlight a process step: change the fill to amber and preserve it
  - elementId: step-2
    effect: fill-color
    color: "#F59E0B"
    trigger: onClick

  # Dim a secondary element: reduce its opacity to 30%
  - elementId: bg-decoration
    effect: transparency
    amount: 0.3
    trigger: withPrevious

  # Emphasize the current card: pulse red once, then restore the original color
  - elementId: card-current
    effect: color-pulse
    color: "#EF4444"
    trigger: afterPrevious

  # Bring body text in gently
  - elementId: body-text
    effect: float-in
    direction: up
    easing: ease-out
```

### Triggers and Groups

- `onClick` starts a new click group and plays on click
- `withPrevious` starts at the same time as the preceding animation
- `afterPrevious` starts automatically after the preceding animation ends
- If the first animation on a page uses `withPrevious` or `afterPrevious`, the group beginning with it plays automatically when the page is entered
- To make multiple elements enter together after a click, set the first animation to `onClick` and the rest to `withPrevious`
- Use `afterPrevious` for animations that should play sequentially

### direction

`direction` indicates the travel direction or wipe progression direction. For entrance effects, `up` means entering upward from below the page; for exit effects, `up` means leaving the page upward. This field only affects fly/wipe/peek/float effects and is ignored by other effects. Float effects support only `up` and `down`; `rise-in` does not use this field and always rises from below the page.

### motion-path

`path` is an SVG path string. Path coordinates are offsets relative to the element's current position, measured in page px. The path must start with `M 0 0`, contain only one subpath, and may use `L` (line), `Q` / `C` (curves), and `Z` (close). For example, `M 0 0 L 200 -100` moves the element 200px to the right and 100px upward.

The same element may define multiple animations in array order. Keep each page to 1–3 animation groups when possible, prefer simple effects such as fade, fly, and zoom, and avoid applying multiple emphasis effects to the same element in succession.
