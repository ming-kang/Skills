# Deep Blue Atlas · academic STYLE DESIGN SYSTEM

Category baseline: [baselines/academic.md](baselines/academic.md) — read alongside this file; the signature system below overrides baseline visual defaults on conflict, never evidence boundaries.

## Signature system

One-line style signature: a deep-blue linear-reasoning system on white — oversized conclusory titles deliver the judgment first, orthogonal segments and nodes organize the evidence, cyan singles out the one key piece of evidence, and trace orange-red handles thresholds and exceptions.

【Color Palette】
All hex values below are approximations pixel-sampled from the reference images (marked "approx."):
- Page background #FFFFFF (approx.): a uniform pure-white canvas across the deck, white covering over 90% of the area, no dark pages.
- Primary structural deep blue #203D74 (approx.): page titles, body emphasis, table headers, key figures, chart main lines, nodes, arrows, and decision-tree edges — the system's first visual anchor.
- Secondary deep blue #2C477A (approx.): section subheads and secondary structural lines, carrying the deep blue's anti-aliased tiers.
- Primary accent cyan #49B7D0 (approx.): subtitles, two-digit numerals, selected/active states, point estimates, event nodes, current step; never used as large-area fill, and it doubles as the entire "positive/valid" semantics (this style uses no green).
- Neutral gray #7F899E (approx.): explanatory text, axis labels, auxiliary notes, and legend-style annotations.
- Light blue-gray #B5C0D0 (approx.): page numbers, secondary notes, de-emphasized information, and fine reference lines.
- Divider gray #D9DEE7 (approx.): table hairlines, row separators, inter-column boundaries.
- Grid gray #E7ECF1 (approx.): horizontal chart gridlines, faintest structural lines.
- Negative red #E94B3B (approx.): inapplicable/excluded states, ex-ante threshold lines, risk reference lines — trace amounts only.
- Reminder orange #FD9F66 (approx.): exceptions and flagged figures needing attention without a negative verdict — even more trace than red.
Color discipline: no multi-series rainbow palette; within a page, no more than the three hue families deep blue / cyan / gray; every colored element must be able to explain its information role.

【Layout Skeleton】
Source facts: 16:9 canvas (sample images ~1467×825 px). Outer margins ~5–7% left/right, 6–8% top; page titles left-aligned, occupying roughly the top quarter; body content begins at ~28–32% of page height. The reading path is a Z: title → main figure/table → sidebar explanation → bottom conclusion line. Columns are always asymmetric — ratios such as ~58:42, 37:63, 31:38:31, 72:28 chosen per page type — with zones separated only by whitespace and fine gray rules, never panels. A light-gray "current page / total pages" number is fixed at lower right, omitted on the cover; no header navigation bar, no fixed sidebar, no logo corner mark. The bands between title zone and main figure, the inter-column transitions, and the page edges are fixed whitespace.

【Typography】
Source facts: a modern sans-serif character throughout — even stroke widths, flat terminals, open letterforms, close to a modern gothic/humanist sans (render with {latin: QuattrocentoSans, ea: MiSans}); Latin and numerals equally clean sans (the JPGs cannot confirm exact family names). Taking body text as 1x: small notes/page numbers 0.65–0.8x; section subheads 1.25–1.5x, semi-bold; page titles 2.1–2.5x, regular-to-medium weight, authority built through size rather than extreme boldness; cover main title 3–3.5x, distinctly bold; result big numbers 2–2.8x, semi-bold to bold. Weight hierarchy: page titles regular/medium, section heads semi-bold, key conclusions and figures bold, explanatory text regular, auxiliary information demoted to gray. No serif, script, italic, or monospace code faces anywhere in the set.

【Chart Language】
Only types that actually appear in the samples:
- ⭐ Single-series line chart: light-gray horizontal grid, no legend, node values labeled directly, one in-chart sentence of annotation.
- ⭐ Three-line academic wide table: only two deep-blue rules, below the header and at the foot — no vertical lines, no outer frame, no zebra striping; key-difference cells switch to cyan, variable differences legible without a legend.
- ⭐ Orthogonal decision tree: diamond decision nodes + right-angle polylines + small terminal arrows, branch labels placed along the lines; leaf nodes = deep-blue bold name + status word (red = inapplicable, cyan = applicable) + gray explanation.
- ⭐ Segmented timeline: thick deep-blue main axis + short ticks; excluded phases switch to gray dashed lines with axis-break jogs; cyan dots mark key instants, vertical leader lines connect annotations.
- ⭐ Confidence-interval plot (simplified forest plot): deep-blue interval lines + end caps + cyan point estimates + gray reference dashes + a red ex-ante threshold line.
- Mini interval scale: fine line with ticks at both ends, baseline value in gray at left, criterion value in deep-blue bold at right, flanking metric rows and logic rows.
- Horizontal process chain: cyan-numbered steps joined by thin arrows, with one looping bracket line allowed to express retrospective iteration.
Shared discipline: labels placed directly, no legend dependence; one main figure per page — never pile up multiple independent charts.

【Signature Components】
- Conclusory display title: one complete long-form assertion per body page, left-aligned, occupying the top quarter; on the cover, a main title plus core proposition performs the same function.
- Two-digit cyan numerals: 01/02-style navigation numbers, small but conspicuous, used for list items and process steps — the deck's wayfinding.
- Cyan evidence points: one to three cyan focuses per page (point estimate, key node, selected path, current step) — the reader's sole landing spot, never a fill.
- Lines as grammar: dividers, axes, leader lines, and table rules carry all structural expression — the style's most stable visual fingerprint.
- Panel-free zones: multi-column areas are zoned by whitespace and fine gray rules alone — no rounded cards, no shadows, no fill blocks.
- Short-tick anchor lists: resolution/threshold lists use short cyan vertical ticks as per-item anchors instead of bullets.
- Bottom conclusion line: one full-width deep-blue bold line at the foot of body pages, sealing the page's argument.
- Light lower-right page number: light gray "current page / total pages", omitted on the cover.
- Restrained geometric nodes: diamond = decision, dot = status/estimate, short tick = list anchor, arrow = direction; no general-purpose icon library.

【Prohibited】
- No dark full-bleed backgrounds; deep blue is for text and lines, never page fills.
- No photos, people images, product shots, screenshots, illustrations, or large image backgrounds.
- No gradients, glows, shadows, glassmorphism, transparency layering, or 3D effects.
- No rounded cards, card walls, colored panels, or heavy information boxes.
- No colored icons, emoji, stickers, badge-style labels, or decorative graphic assets; no logos, brand corner marks, permanent sidebars, or header navigation bars.
- No vertical table lines, heavy outer frames, or zebra row fills; tables use horizontal rules only.
- No pies, donuts, default office-suite legends, or multi-color categorical charts.
- No green for positive states; positive/valid semantics are carried entirely by cyan.
- No free-curve connectors, radial mind maps, or dense network node graphs — the "atlas feel" comes from orthogonal-line relationship expression, not webs.
- No long centered copy, slogan-style one-liner pages, or decorative giant background numerals; no serif, script, italic, or display faces.

【Slide Types and Layouts】
Cover | module opening | left ~2/3 information zone + right 1/3 whitespace | eyebrow + oversized main title + cyan subtitle + one line of meta info + fine divider + bolded core proposition + supplementary note | ~7 text blocks, no charts, no page number.
Problem evidence page | phenomenon data + misreading teardown | ~58:42 two columns | 1 main figure + 3 numbered items + bottom conclusion band | direct-labeled line chart, cyan numerals | not suited to parallel multi-topic content.
Logic hypothesis page | falsifiable hypothesis statements | narrow left column with large relational words + wide middle column of explanation + mini interval plot at right | 3 logic rows + 2 dividers | not suited to long formula derivations.
Comparison table page | groups/approaches compared side by side | full-width three-line table (~88% of page width) + basis note below + key-points passage + conclusion line | high density relieved by generous row height.
Decision-tree page | option selection converging | ~37:63, conclusion first in the left column + orthogonal decision tree at right | 2–3 decision nodes + 4 leaf nodes | wide gaps between branches to avoid line crossings.
Timeline page | measurement windows / phase schedule | full-width single axis (~86% of page width) + annotations above and below the axis + 2-line bottom note | medium-low density, breathing room around the axis.
Results decision page | metric comparison + point estimates + action branches | ~31:38:31 three columns + bottom three-column action zone | the deck's density ceiling, order maintained by three-column alignment.
Convergence page | scaling resolutions | ~72:28 main zone + right resolution rail | process chain + loop line + threshold checklist + limitations note | does not end on a thank-you page.

【Density Baseline】
One core visual object per page: 1 main figure/table/framework — never pile up multiple independent charts. Body pages carry ~7–15 text and graphic blocks; line charts directly label 3–5 nodes; comparison tables 2–4 data rows × 4–6 columns with generous row height; decision trees 2–3 decision nodes and at most 4 leaves; timelines carry at most 8 time-point labels; results pages allow 2 sets of mini metrics + 1 interval plot + 3 columns of action branches. Numbered lists run 3–5 items per page, each a one-line bolded claim + one gray explanatory sentence. Whitespace concentrates between title and main figure, in asymmetric-column transitions, and at the page edges; the body area holds no large empty block, nor may anything be stuffed in to fill. At most 3 cyan focuses per page; red and orange combined remain trace.
