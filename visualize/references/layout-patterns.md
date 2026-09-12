# Layout patterns

Choose a composition that exposes the relationship the reader needs to understand. Exact tokens live in [style.md](style.md), primitives in [svg-cookbook.md](svg-cookbook.md), and notation in [diagram-types.md](diagram-types.md). The snippets below assume an existing `Diagram`.

## Choose the reading order first

| What the reader needs to see | Composition | Example |
|---|---|---|
| A sequence with revision | One main spine, feedback in an outside gutter | [Feedback pipeline](../assets/gallery/patterns/feedback-pipeline.svg) |
| What survives successive checks | Aligned narrowing bands and a column of removal notes | [Annotated funnel](../assets/gallery/patterns/annotated-funnel.svg) |
| Two implementations of the same task | Matched panels, the same input, and aligned comparison rows | [Mechanism comparison](../assets/gallery/patterns/mechanism-comparison.svg) |
| Shared input and independent work | Common source above parallel lanes, explicit merge below | [Parallel pipelines](../assets/gallery/patterns/parallel-pipelines.svg) |
| How a numeric value changes | Scaled axes, data marks, and a local callout | [Annotated chart](../assets/gallery/patterns/annotated-chart.svg) |
| Two qualitative dimensions | Labeled regions on two axes | [Quadrant map](../assets/gallery/patterns/quadrant-map.svg) |
| Choices around one constraint | A central hub with short, balanced branches | [Mind map](../assets/gallery/mind-map.svg) |

Keep the main explanation readable without its side notes. Put detail next to the stage it explains, and use at most one short takeaway below the body when it adds information. Equal peers share dimensions, typography, and row baselines. Color related stages as a group; use an accent for a meaningful difference or focal point.

## §1. Zone split — `.zone()`

Use a boundary when location, ownership, or trust changes the meaning of a connection. Name both regions and label the crossing payload or protocol.

```python
d.zone(380, 70, 420, "Client", "Server", 210, 560)
client = d.node(60, 120, "Browser")
server = d.node(420, 120, "API", family="green")
d.arrow(client.right, server.left, label="HTTPS")
```

`both=True` means traffic travels both ways. Use two labeled edges when request and response carry different information.

## §2. Numbered steps — `.step()`

Number steps when their order matters. Keep the number small and the title dominant; the number is an ordering cue, not a completion status.

```python
first = d.step(40, 80, 1, "Receive", "input file")
second = d.step(d.right_of(first, 64), 80, 2, "Parse", "read records")
d.arrow(first.right, second.left)
```

## §3. Verdict rails

Use [decision-ladder.svg](../assets/gallery/decision-ladder.svg) for **ordered policy groups** that return allow, deny, or no match. A final verdict exits to its labeled rail; no match continues to the next group. Show the default after the last group. A successful check that merely continues is different from a final allow verdict.

```python
allow = d.node(40, 40, "Allow", family="green", w=680, h=32)
deny = d.node(40, 320, "Deny", family="terracotta", w=680, h=32)
group = d.step(64, 168, 1, "Group A", "first check")
d.arrow(group.top, (group.cx, allow.y + allow.h), color="green", label="allow")
d.arrow(group.bottom, (group.cx, deny.y), color="terracotta", label="deny")
```

Give each group its own vertical ports. Adapt the actual policy ordering; the example is not a product's authorization algorithm.

## §4. Titled panel — `.panel()`

A panel groups related components or explanatory rows. Its 26px header band needs clear space beneath it; put child nodes about 52px below the panel top.

```python
panel = d.panel(40, 160, 520, 152, "Result", family="green")
source = d.node(64, panel.y + 52, "Input", "parsed values", w=160)
total = d.node(376, panel.y + 52, "Total", "sum of values", family="green", w=160)
d.arrow(source.right, total.left, color="green", label="sum", label_offset=12)
```

Paint the panel background before its connectors and child nodes. In manual SVG, mark the body `data-role="panel"` and its heading `container-label`. For a qualitative region, a full tinted background can be clearer than a header band; see the quadrant example.

## §5. Scope / loop frame — `.scope()`

Name the condition or repetition that applies to the enclosed work: `each turn`, `retry`, `alt`, or `opt`. Put a guard in the subtitle when relevant. Nested frames indicate nested scope, not execution order by themselves.

```python
d.scope(40, 100, 680, 240, "opt", "token valid + permitted")
```

The [sequence frames](../assets/gallery/sequence-frames.svg) example leaves separate space for the frame heading, guards, and real messages.

## §6. Feedback gutter

Keep the main flow on one axis; reserve a separate left or right gutter for the return. Route to the earlier node's edge and label what the return carries or why it happens. Give multiple unrelated returns separate gutters.

```python
gutter_x = max(first.x + first.w, last.x + last.w) + 64
d.lpath([last.right, (gutter_x, last.cy), (gutter_x, first.cy), first.right],
        color="terracotta", dashed=True, label="revise", label_offset=-12)
```

Choose the label side with available room; a left gutter often needs a positive offset and a right gutter a negative one. Extend the canvas beyond the gutter and its text. See [feedback-pipeline.svg](../assets/gallery/patterns/feedback-pipeline.svg).

## §7. Side notes and side events

A note explains a component; an event transfers information. Draw notes with a light **0.5–0.75px leader without an arrowhead**. Use a 1.5px arrow for an actual notification, query, or update. Reserve a side column so the extra text does not interrupt the main spine.

Use a short title and one or two explanatory lines. Put longer lists in a `.panel()`. The [feedback pipeline](../assets/gallery/patterns/feedback-pipeline.svg) uses a criteria panel; the [funnel](../assets/gallery/patterns/annotated-funnel.svg) aligns a note with each filtering stage. In both, the leader means “explains this,” not another processing step.

## §8. Message and payload labels

When both a message name and literal payload matter, put 12px text on opposite sides of the line with about 14px baseline clearance. A monospace payload may distinguish literal data. Move long payloads into a nearby note instead of shrinking the font or covering the connector.

## §9. Repeated cells and miniature mechanisms

Small circles, cells, and bars can explain records, tokens, caches, and repeated state. Use the same spacing and shape for equivalent items. Mark chart cells `data-role="data-mark"`; their width or count may encode data, so it must not change merely to fit a label.

Show a concrete, internally consistent example. In [mechanism-comparison.svg](../assets/gallery/patterns/mechanism-comparison.svg), the same inputs `2, 4, 3` produce `9`; intermediate running totals are `2, 6, 9`. The shapes explain what each method retains. Counts and highlighted progress cells must agree with their captions.

## §10. Narrow re-layout

For a phone or a narrow document column, make a separate `<name>_mobile.svg`. Keep the font scale and graph; recompute the positions and edge anchors.

- A 360px canvas with 40px margins leaves 280px for content.
- Turn a horizontal pipeline into a vertical spine. Give peers a common computed width and center them; `col()` alone aligns left edges.
- Stack parallel panels when needed, preserving their shared input and merge. Their placement must not introduce a serial dependency.
- Put notes below their relevant stage and reserve every wrapped legend row.

The [desktop](../assets/gallery/data-flow.svg) and [narrow](../assets/gallery/data-flow_mobile.svg) examples carry the same stream, batch, and file payloads in the same direction.

## §11. Funnel with aligned explanations

Use a funnel for successive retention or filtering. Keep stage labels on one centerline and align the explanations in a separate column. The remaining count belongs inside each band; removals explain the difference from the prior band.

For numeric counts, use one width scale: `band_width = max_width * retained / initial`. Keep heights equal. In the [example](../assets/gallery/patterns/annotated-funnel.svg), `1000 → 800 → 600 → 480` has removals `200, 200, 120`. If the input has no quantities, label the funnel schematic rather than inventing a measured taper.

## §12. Matched mechanism comparison

Give each method the same input, panel width, type scale, and output baseline. Show the distinctive operation inside the panel, using miniature shapes when they explain more than another labeled box. Put a compact comparison table below, with its value columns aligned to the panels.

Color identifies the two methods; it need not imply that one is better. Compare the same dimension in each row and support any performance claim with data. [Example](../assets/gallery/patterns/mechanism-comparison.svg).

## §13. Shared source and parallel lanes

Place a common input above the lanes and draw its trunk once. Split at a clear junction, then color each branch consistently. Align equivalent stages. Merge only when the outputs really join; independent results can remain separate.

If one phase consumes another's output, draw that dependency even when the phases sit side by side. A repeated caption is not a substitute for a missing edge. [Example](../assets/gallery/patterns/parallel-pipelines.svg).

## §14. Annotated data chart

Keep axes and guides quieter than the data. Derive ticks and marks from the same scale, state units, and label logarithmic axes if used. Put a callout near a meaningful point, using an unheaded leader; keep it clear of the plotted series.

Use the series' actual line/point symbol in the legend. Mark illustrative values explicitly. [Example](../assets/gallery/patterns/annotated-chart.svg): attempts `1–5` and delays `1, 2, 4, 8, 8` seconds on linear axes. For measured or publication-ready charts, use the supplied data and a plotting tool, then apply the relevant visual principles.

## §15. Two-axis concept map

Name both dimensions and their directions. Use equal regions for qualitative categories; region size must not suggest an unsupported numeric difference. Keep labels in consistent positions and leave any trend arrow a clear corridor. [Example](../assets/gallery/patterns/quadrant-map.svg).

For several choices around a single constraint, use a radial hub instead: pair each choice with a short consequence note. Equal branches communicate alternatives; use arrows only when their direction has a defined meaning.

## Keep the composition proportional to the task

A simple chain can remain a simple chain. Add a frame for a real boundary, a sidebar for useful explanation, or a chart for actual quantities. Validate the SVG and inspect the rendered reading order; neither a tidy grid nor a clean validator report establishes semantic correctness.
