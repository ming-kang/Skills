# Supplied SVG reference study

Studied all 13 files supplied in `~/Desktop/references`: parsed their text, geometry, and presentation attributes, then inspected each Chromium rendering at its viewBox dimensions. Source snapshots, PNGs, and the browser report are local review artifacts under `.artifacts/visualize-reference-study/source/`.

The distributed skill contains the extracted guidance and newly drawn reusable examples. The supplied source files and their repeated export styles remain review inputs outside the skill.

| Source | Visual method learned | Application |
|---|---|---|
| `01.svg` — training lifecycle | Equal-width vertical stages, grouped phase colors, feedback outside the spine | `feedback-pipeline.svg`; layout §6 |
| `02.svg` — training-scale chart | Quiet guides, a local point callout, line-style legend | `annotated-chart.svg`; layout §14, with explicit illustrative values and a consistent scale |
| `03.svg` — data funnel | Centered narrowing bands and aligned removal notes | `annotated-funnel.svg`; layout §11, with proportional widths and reconciling counts |
| `04.svg` — compute choices | One central constraint, balanced choices, secondary consequence notes | Radial-map guidance in layout §15; side-note guidance in §7 |
| `05.svg` — post-training stages | Equal stage cards, short explanatory detail, a return below the main row | Numbered steps and feedback recipes, §2 and §6 |
| `06.svg` — outcome/process rewards | Matched panels, miniature state diagrams, a shared comparison table | `mechanism-comparison.svg`; layout §12 |
| `07.svg` — evaluation cycle | One emphasized stage and a nearby detail panel | `feedback-pipeline.svg`; focus and side-note guidance |
| `08.svg` — paired training phases | Shared reference above two consistently aligned lanes | `parallel-pipelines.svg`; §13 explicitly preserves any real phase dependency |
| `09.svg` — compute map | Two named axes, soft region fills, fixed label positions | `quadrant-map.svg`; layout §15, with qualitative categories labeled as such |
| `10.svg` — reasoning/agent comparison | The same panel width and comparable rows beneath process diagrams | `mechanism-comparison.svg`; evidence-based comparison guidance |
| `11.svg` — harness loop | Meaningful container boundaries, a clear outer loop, and named payloads | Grouping and feedback guidance; explicit query input in the memory example |
| `12.svg` — parallel agents | A broad shared source, repeated branches, a shared result area, and side notes | `parallel-pipelines.svg`; shared-trunk and output-merge guidance |
| `13.svg` — attention mechanisms | Chinese typography, equal repeated tokens, miniature shapes that reveal retained state | Chinese `mechanism-comparison.svg`; repeated-mark guidance in §9 |

The portable rules live in `visualize/references/layout-patterns.md`, supported by the style, notation, and shape guides. New assets are under `visualize/assets/gallery/patterns/`; their editable sources stay in `tools/visualize/gallery/patterns.py`.

Visual adaptation keeps the house palette, 14/12 typography, and open-chevron flow arrows. Explanations use lighter unheaded leaders. Numeric examples identify illustrative data; domain claims in the supplied references are not treated as general facts or templates for an unrelated system.

The repository renderer now derives dimensions for percentage-sized SVG roots from the viewBox, so the source files can be reviewed without the browser's default 1280×720 viewport changing their proportions.
