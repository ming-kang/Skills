# Clean Style (the only style)

This skill ships **one** style: warm, flat, restrained, and built for technical clarity. There is no style flag and no second theme — keep output predictable.

The look in one sentence: **warm paper canvas, cream/tinted rounded boxes, thin open-chevron arrows that recolor themselves, and absolutely flat** (no shadows, no gradients, no filters). Meaning is carried by a small set of **color families** used as box *fills*, not by icons or borders.

> The skill's own reference diagrams live in `assets/gallery/<type>.svg` — one per common diagram type, all in this style and all generated with `svgkit`. Read the one matching your task before drawing; they are the ground truth for the look. Index: `references/diagram-gallery.md`.

---

## Color families

Each conceptual category gets exactly one family. A family is a 5-tuple: **FILL** (tinted pastel box fill) · **STROKE** (box border) · **TITLE** (primary text) · **SUB** (secondary text) · **LINE** (solid accent for arrows / swatches).

| Family | Meaning | FILL | STROKE | TITLE | SUB | LINE / accent |
|---|---|---|---|---|---|---|
| **Neutral** | default boxes, plumbing | `#F5F4ED` | `rgba(31,30,29,0.3)` | `#141413` | `#3D3D3A` | `#73726C` |
| **Green** | primary / happy path, success, retrieval | `#E1F5EE` | `#0F6E56` | `#085041` | `#0F6E56` | `#1D9E75` |
| **Purple** | alternate / parallel branch, secondary | `#EEEDFE` | `#534AB7` | `#3C3489` | `#534AB7` | `#7F77DD` |
| **Terracotta** | warning, limitation, failure, "the problem" | `#FAECE7` | `#993C1D` | `#712B13` | `#993C1D` | `#C75B38` |
| **Amber** | highlight, special module, callout | `#FAEEDA` | `#854F0B` | `#633806` | `#854F0B` | `#EF9F27` |

- Canvas background: `#FFFFFF` (full-canvas rect). The cream boxes read as intentional on it. Transparent is allowed only if the user asks.
- Alt neutral fill `#F1EFE8` is fine for a second tier of muted boxes.
- **Colors ARE box fills.** (Old rule "accents on arrows only" is retired.)
- Box `stroke-width` is a hairline: **0.5** (0.75 acceptable in print). Lines are 1.5.

### Restraint (default to less)

The five families are a *vocabulary*, not a quota — using all of them in one diagram is usually a mistake. Two rules, learned from studying editorial research diagrams (editorial workflow figures):

- **Default to fewer families.** One accent family + Neutral cream is almost always stronger than two or three. Reach for a second family only when there is a *meaning* contrast to mark (primary vs. alternate path, success vs. failure), never just to color-code unrelated boxes. A diagram that reads "one system" beats one that reads "five sticky notes".
- **Tint-within-family for siblings.** When items are peers (pipeline stages, lane rows, a series of steps), distinguish them by varying the family FILL **opacity** (0.9 → 0.55 → 0.4) rather than switching families. Opacity is applied as a `opacity="…"` attribute on the `<rect>`; combine with the family STROKE so edges stay crisp. This is a common editorial-workflow trick — one periwinkle family in three tints carries a whole multi-stage flow.

```xml
<!-- three sibling stages, one green family, opacity does the differentiation -->
<rect x="40"  y="40" width="160" height="56" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5" opacity="0.9"/>
<rect x="240" y="40" width="160" height="56" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5" opacity="0.55"/>
<rect x="440" y="40" width="160" height="56" rx="8" fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5" opacity="0.4"/>
```

### Decorative pastel tints

For grids, patch-maps, and categorical cells — *fill only*, with a `rgba(31,30,29,0.3)` 0.5 stroke:

```
amber #FAC775   peach #F5C4B3   mint #9FE1CB   lavender #CECBF6
pink  #F4C0D1   lime  #C0DD97   sky  #B5D4F4
```

---

## Typography

```css
text { font-family: 'Anthropic Sans', -apple-system, BlinkMacSystemFont,
       'Segoe UI', 'PingFang SC', 'Microsoft YaHei', 'Hiragino Sans GB',
       'Noto Sans CJK SC', sans-serif; }
```

Put this once in a `<style>` block. `'Anthropic Sans'` first is harmless — it falls back cleanly when absent.

| Role | size | weight | fill |
|---|---|---|---|
| Node title | 14 | 500 | family TITLE |
| Node sub-label | 12 | 400 | family SUB |
| Caption / footnote / axis | 12 | 400 | `#3D3D3A` |
| Container label (title / sub) | 14 / 12 | 500 / 400 | `#141413` / `#3D3D3A` |

Centered text in a box: `text-anchor="middle" dominant-baseline="central"`.

**Locked scale — don't improvise.** Use **exactly two sizes** everywhere: `14` (titles, weight 500) and `12` (everything else, weight 400). One optional diagram heading at `15–16`/600, used at most once, top-left. More than two sizes or three weights makes a diagram look like a ransom note. Write labels in **sentence case** (or natural Chinese) — never Title Case Every Word.

---

## Box geometry & text placement

### Size every box from its text — compute it, don't guess

Text overflowing its box is the #1 failure in quick SVG diagrams. Never pick a round number; compute the width:

1. Estimate each line's pixel width by character class (at the 14px title size):
   - Latin letter / digit / space / punctuation ≈ **8px**
   - CJK character (汉字、全角标点) ≈ **15px** (nearly a full em — almost 2× Latin)
   - the 12px sub-line is ~85% of those (Latin ≈ 7px, CJK ≈ 13px)
2. `lineWidth = latinCount×8 + cjkCount×15` (use the 12px factors for the sub-line).
3. `boxWidth = max(titleWidth, subWidth) + 32` (16px padding per side), rounded up to a multiple of 4, **minimum 120**.

> Example: title `受上下文窗口限制` = 8 CJK → 8×15 = 120; +32 = **152** (not 150).

The estimate deliberately errs wide, so text never clips. For long labels prefer a wider box or a shorter wording over shrinking the font (the scale is locked).

### Placement

- Height `56` (two-line) or `40` (one-line); `rx="8"` (`rx="10"` for larger cards).
- `cx = x + w/2`. Two-line text inside a box at `(x, y, w, h=56)`:

```xml
<rect x="X" y="Y" width="W" height="56" rx="8"
      fill="#F5F4ED" stroke="rgba(31,30,29,0.3)" stroke-width="0.5"/>
<text x="CX" y="Y+22" text-anchor="middle" dominant-baseline="central"
      font-size="14" font-weight="500" fill="#141413">Title</text>
<text x="CX" y="Y+39" text-anchor="middle" dominant-baseline="central"
      font-size="12" fill="#3D3D3A">sub-label</text>
```

- One-line: a single `<text>` at `y = Y + h/2`, 14/500.
- Vertical gap between stacked boxes: `≥ 56–60px` (the connector lives in the gap).
- Horizontal gap between boxes: `≥ 40–75px`. Outer margin: `40px`.

---

## Containers (grouping)

```xml
<!-- Dashed group (NOT counted as a collision obstacle) -->
<rect x="X" y="Y" width="W" height="H" rx="14"
      fill="none" stroke="rgba(31,30,29,0.3)" stroke-width="0.5" stroke-dasharray="4 3"/>
<text x="X+20" y="Y+26" font-size="14" font-weight="500" fill="#141413">Group label</text>

<!-- Solid section -->
<rect x="X" y="Y" width="W" height="H" rx="20"
      fill="#F5F4ED" stroke="rgba(31,30,29,0.3)" stroke-width="0.5"/>
```

**Dash patterns.** Plain grouping containers use `stroke-dasharray="4 3"`. **Scope/loop frames** (`.scope`, labelled `EACH TURN`-style badges) and **zone dividers** (`.zone`, the trust-boundary split) use the longer `6 4` so they read as region boundaries rather than ordinary groups. Both stay at `stroke-width="0.5"`.

---

## Arrows — the signature element

Define **one** marker. The open chevron recolors itself to match each line via `context-stroke`, so a single marker serves every color:

```xml
<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5"
          markerWidth="6" markerHeight="6" orient="auto-start-reverse">
    <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke"
          stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
  </marker>
</defs>

<!-- straight connector (neutral) -->
<line x1="" y1="" x2="" y2="" stroke="#73726C" stroke-width="1.5"
      stroke-linecap="round" marker-end="url(#arrow)"/>

<!-- colored connector — chevron inherits the stroke -->
<line x1="" y1="" x2="" y2="" stroke="#1D9E75" stroke-width="1.5"
      stroke-linecap="round" marker-end="url(#arrow)"/>

<!-- orthogonal branch: only the arriving segment carries the marker -->
<path d="M ax ay L bx by L cx cy" fill="none" stroke="#7F77DD"
      stroke-width="1.5" stroke-linecap="round" marker-end="url(#arrow)"/>
```

- Connect to box **edges**, never centers; never route a straight arrow through another box (use an L-shaped `path`).
- Arrow labels: `≤3 words`, 12–14px, at the segment midpoint offset 6–15px. Add a tiny `#FFFFFF` background rect only if the label would overlap a line or box.

---

## Legend

Include one whenever 2+ families or 2+ arrow meanings appear. A horizontal row near the bottom; each item = swatch + label:

```xml
<rect x="X" y="Y" width="12" height="12" rx="3"
      fill="#E1F5EE" stroke="#0F6E56" stroke-width="0.5"/>
<text x="X+18" y="Y+6" dominant-baseline="central" font-size="12"
      fill="#3D3D3A">Retrieval path</text>
```

(Use a solid `LINE`-color square for pure category dots.)

---

## Accessibility

Make `<title>` and `<desc>` the first children of `<svg>` (the examples do this).

---

## Hard rules

- Self-contained: no `@import`, no remote `url()/href/src`, fonts inline. End with `</svg>`.
- Flat: **no** drop shadows, gradients, filters, or blur.
- Clean presentation attributes (`fill="…"`), not the verbose duplicated `style="…"` that the exported examples contain.
- Snap coordinates to integers. One `<marker id="arrow">` in `<defs>`.
