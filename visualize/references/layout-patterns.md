# Layout Patterns — compositing recipes

Single-element primitives (boxes, arrows, containers) live in `svg-cookbook.md`; per-type layout rules in `diagram-types.md`; routing in `svg-layout-best-practices.md`. **This file is the catalogue of multi-element *compositing patterns*** — the recurring ways those primitives are combined to express something a bare box/arrow can't. Each is shown in the house warm tokens.

Reach for these when the request is one of: a trust-boundary split, a numbered recipe / pipeline, an allow-vs-deny decision, a titled result panel, a repeating scope, a long feedback return, out-of-band side events, a two-line payload label, or a stateful cell strip. If `python3` is available, the `svgkit` helper implements the bolded ones as one-liners (`.step`, `.panel`, `.scope`, `.zone`).

> Style tokens, the marker, the type scale, and the flat rule all still apply — a pattern never justifies a new color, a filled triangle, or a shadow.

---

## §1. Zone split (trust boundary) — `svgkit: .zone()`

Two regions separated by a dashed vertical divider, each with its own column header. For "Client | Server", "Local | External", "On-prem | Cloud". The interesting edges are the ones that **cross** the divider.

```python
d.zone(divider_x=380, y_top=70, y_bottom=420,
       left_label="Client", right_label="Server",
       left_cx=210, right_cx=560)
# then place nodes in each half; cross-zone arrows are the story
cli = d.node(60, 120, "Browser", family="neutral")
srv = d.node(420, 120, "API", family="green")
d.arrow(cli.right, srv.left, label="HTTPS")
```

Hand-written form:

```xml
<line x1="380" y1="70" x2="380" y2="420" stroke="rgba(31,30,29,0.3)"
      stroke-width="0.5" stroke-dasharray="6 4"/>
<text x="210" y="70" text-anchor="middle" dominant-baseline="central"
      font-size="14" font-weight="500" fill="#141413">Client</text>
<text x="560" y="70" text-anchor="middle" dominant-baseline="central"
      font-size="14" font-weight="500" fill="#141413">Server</text>
```

A **double-headed** connector (e.g. a bind mount) is the same divider with a line that carries both `marker-start` and `marker-end` — used sparingly, only for genuinely bidirectional flows.

## §2. Numbered step ladder — `svgkit: .step()`

A row (or column) of cards, each with a circled step number + title + optional sub. For recipes, pipelines, and any "do this, then this, then this". The circled number makes order unmistakable without arrowheads on every link.

```python
s1 = d.step(40, 80, 1, "Receive", "tool request")
s2 = d.step(d.right_of(s1, 40), 80, 2, "Check rules", "allow / deny", family="green")
s3 = d.step(d.right_of(s2, 40), 80, 3, "Execute", family="green")
d.arrow(s1.right, s2.left); d.arrow(s2.right, s3.left, color="green")
```

## §3. Verdict rails (allow ↑ / deny ↓)

A specialised flowchart for a chain of checks where each step either **passes (continues right / up)** or **fails (drops down)**. Bracket the ladder between two terminal bars: a green "Execute" bar on top (or at the right end) and a terracotta "Blocked" bar on the bottom. Each step's verdict is the arrow color + direction — green up = allow, terracotta down = deny.

```python
# top rail = allow target, bottom rail = deny target
d.raw('<rect x="40" y="20" width="680" height="28" rx="6" fill="#E1F5EE" '
      'stroke="#0F6E56" stroke-width="0.5"/>', layer="boxes")
d.raw('<rect x="40" y="280" width="680" height="28" rx="6" fill="#FAECE7" '
      'stroke="#993C1D" stroke-width="0.5"/>', layer="boxes")
s = d.step(60, 140, 1, "Hook", "PreToolUse")
d.arrow(s.top, (s.cx, 48), color="green", label="allow")     # up to Execute
d.arrow(s.bottom, (s.cx, 280), color="terracotta", label="deny")  # down to Blocked
```

Stagger multiple steps' allow/deny arrows by ±20px so heads don't pile up on the same rail point. (See `assets/gallery/decision-ladder.svg` for the full pattern.)

## §4. Titled panel with header band — `svgkit: .panel()`

A white card with a colored title strip across the top — the "Step 1" / "Result" window treatment. Use when a group of rows needs both a visible container *and* an obvious name, and a dashed container isn't strong enough. The body is white so you can drop nodes, mono rows, or `.raw()` art onto it.

```python
pnl = d.panel(40, 160, 360, 140, "Result", "cumulative", family="green")
# place content inside; anchor off pnl.x / pnl.y + the 26px band
d.node(60, pnl.y + 46, "total", "0.0034 USD", family="green")
```

Hand-written: body rect (white, family stroke) + a 26px header band in the family fill (drawn as a rounded rect + a thin square rect to flatten its bottom) + the title in the band. Band height stays under 30 so the validator still treats the whole panel as a single collision box.

## §5. Scope / loop frame — `svgkit: .scope()`

A dashed region whose label says what the region *does*, not just what's in it: `EACH TURN`, `AGENTIC LOOP`, `RETRY ×3`. Visually a `container()` variant, but the label is **uppercased and tracked out** (letter-spacing 2, on the 14/500 container-label weight) so it reads as a scope badge. The uppercase + tracking carries the emphasis without leaving the locked type scale. Nest scopes to show "this group repeats inside that group".

```python
d.scope(28, 60, 700, 240, "each turn", sub="repeats per request")
d.scope(60, 110, 640, 170, "agentic loop")
```

## §6. Right-gutter loop-back

When a feedback edge has to return from a late node to an early one, route it up the **right margin** rather than across the diagram. The long vertical leg lives in empty space the boxes already leave as padding, so it never collides.

```python
# from the bottom-right step's right edge, up the gutter, back into step 1
d.lpath([(last.right[0], last.cy), (W - 24, last.cy),
         (W - 24, first.cy), (first.right[0] + 10, first.cy)],
        color="purple", label="repeat")
```

Reserve ~24px of right margin (so `W - 24` is clear) and keep the canvas 40px wider than the content when you plan to use it. Only the arriving segment carries the marker.

## §7. Side-rail of out-of-band events

A vertical column of **dashed** boxes beside the main spine, joined to it by short **dashed** arrows. For things that happen alongside the main flow without blocking it: async notifications, config changes, observers, telemetry. The dashing is the signal that they're not on the critical path.

```python
for i, (lbl, y) in enumerate([("Notification", 200), ("ConfigChange", 260)]):
    d.raw(f'<rect x="20" y="{y}" width="120" height="42" rx="8" fill="#F5F4ED" '
          f'stroke="rgba(31,30,29,0.3)" stroke-width="0.5" stroke-dasharray="4 3"/>',
          layer="boxes")
    # dashed connector into the main spine
    d.lpath([(140, y + 21), (200, y + 21)], color="neutral")  # use stroke-dasharray via raw if needed
```

(For a fully dashed connector, emit the `<line>` via `.raw()` with `stroke-dasharray="4 3"` — `svgkit.arrow` is solid by design.)

## §8. Two-line arrow label (label + payload)

Sequence and request/response diagrams often need both a human label *and* the actual payload on one arrow. Stack them: the label at 12/CAPTION above the line, a monospace payload at 12/SUB below. Monospace is the only place a non-system font appears — it signals "this is literal data".

```xml
<text x="300" y="94" text-anchor="middle" dominant-baseline="central"
      font-size="12" fill="#141413">permission_request</text>
<text x="300" y="110" text-anchor="middle" dominant-baseline="central"
      font-size="12" font-family="ui-monospace, 'SF Mono', Menlo, monospace"
      fill="#3D3D3A">{tool_name: "Bash", ...}</text>
```

Keep payloads short — if they wrap, the arrow isn't the right place; move the detail into a side note or a `.panel()`.

## §9. Stateful cell strip (time-stack)

Rows of small cells where **fill encodes state**, with a one-line caption under each row. For caches, token budgets, pipelines that grow turn-by-turn, queues. Reuse §5 of `svg-cookbook.md` (striped strip) and §6 (vector bars) vocabulary — the new part is the *legend of states* and the per-row caption.

```python
# one row per timestep; cached vs new vs changed encoded by fill
for row, turn in enumerate(turns):
    y = 80 + row * 76
    for col, cell in enumerate(turn.cells):
        fill = {"cached": "#F1EFE8", "new": "#FAEEDA", "changed": "#FAECE7"}[cell.state]
        d.raw(f'<rect x="{44 + col * 46}" y="{y}" width="40" height="26" '
              f'rx="3" fill="{fill}" stroke="rgba(31,30,29,0.3)" stroke-width="0.5"/>',
              layer="boxes")
    d.raw(f'<text x="44" y="{y + 42}" dominant-baseline="central" '
          f'font-size="12" fill="#3D3D3A">{turn.caption}</text>',
          layer="labels")
```

Cells under 70×30 are ignored by the collision checker, so arrows can run between rows freely. A 1px hairline rule above the legend separates it from the data.

---

## §10. Responsive re-layout (desktop → mobile)

When a diagram is wide it doesn't survive a phone screen by scaling — the text becomes illegible and the horizontal flow collapses. The fix is to **re-lay-out**, not rescale: produce a separate `_mobile.svg` with a tall-narrow viewBox and the same content re-flowed vertically. (Figure sets that ship `desktop` + `mobile` variants do this — e.g. a `596×407` desktop chart becomes a `327×467` mobile one, re-composed not cropped.)

**When:** the user asks for a "mobile / phone / narrow" version, or the source diagram is wider than ~760 and will be embedded in a column.

**Rules — only the geometry changes; tokens, marker, type scale, palette stay.**

- Target a tall-narrow viewBox: width ~360, height grows to fit.
- Re-flow a horizontal pipeline as a vertical column — `.col([...], x=80, gap=60)` instead of `.row([...], gap=56)`; re-anchor every arrow on `.top`/`.bottom`.
- Stack parallel lanes (e.g. a 3-service fan-out) **serially** down the column rather than side-by-side; a fan-in/merge becomes a single vertical chain.
- Widen one box before shrinking the font (the type scale is locked). At width 360 with 40px margins, a single column of ~200–260-wide boxes reads cleanest.
- The legend wraps on its own (svgkit's `legend()` wraps at the right margin); give the canvas ~40px extra height so the wrapped second row isn't clipped.
- Name it `<name>_mobile.svg` next to its desktop sibling.

```python
# desktop:  Kafka → Spark → S3 → Athena   (.row, 880×230)
# mobile:   same four nodes, top-to-bottom (.col, 360×N)
d = Diagram(360, 560, title="Streaming data pipeline", desc="…")
k  = d.node(80, 40,  "Kafka",  "event stream")
sp = d.node(80, 156, "Spark",  "transform", family="green")
s3 = d.cylinder(80, 272, "S3", "parquet", family="green", w=200, h=54)
at = d.node(80, 404, "Athena", "SQL query", family="purple")
d.arrow(k.bottom,  sp.top, label="stream")
d.arrow(sp.bottom, s3.top,  color="green",  label="batch")
d.arrow(s3.bottom, at.top,  color="purple", label="query")
d.legend([("green", "write path"), ("purple", "read path"), ("neutral", "ingest")], y=520)
```

See `assets/gallery/data-flow_mobile.svg` for the worked example.

---

## When NOT to reach for these

- A plain `node`/`arrow` chain already says it → don't wrap it in a scope or panel.
- Two boxes on each side of a boundary, but there's no meaningful "crossing" → a zone split is decorative; just label the boxes.
- A decision has one outcome → it's not a ladder; use a single diamond.

The patterns exist to **clarify structure that a flat graph hides**. If the structure is already obvious, the pattern is noise.
