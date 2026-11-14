# Academic Category Baseline

Category baseline for academic presets. The preset's signature system always overrides visual defaults below (background, palette, typography, layout/density) on conflict, never evidence boundaries. Each preset's `Density Baseline` sets per-slide minimums; impose no uniform module, data, or image quotas.

## Argument Spine & Scholarly Discipline
- **Fixed spine**: `Research Question → Gap in Related Work → Data & Methods → Main Results → Ablation/Analysis → Limitations → Future Work`. Short decks may compress, never reorder. Open with problem statement and one-sentence contribution; close with numbered conclusion claims (not summaries) and open questions.
- **Claim titles & evidence**: Content titles state a finding/claim backed on-slide by one primary evidence unit (figure, table, or equation)—no orphan numbers. Pass the title read-through test.
- **Discipline emphasis**: Theory centers equations/proofs; CS/engineering centers diagrams, code, traces, and curves; experimental work clusters equations, charts, and images around one claim; humanities/social sciences layer archival records, maps, and manuscripts rigorously.

## Reproducibility, Math, Charts, Ethics & Citations
- **Tables & reproducibility**: Main results tables include baseline columns, mark best values, and report relative gains beside absolute values. Method slides state dataset size, annotation protocol, inter-annotator agreement, and hyperparameters.
- **Math**: Typeset equations formally (KaTeX quality) with numbering and italic variables; keep only the core equation in main slides (derivations to appendix).
- **Self-contained, honest charts**: Include axis labels with units, sample definitions, and captions giving sample size and measurable uncertainty (mean ± variance or confidence intervals, never vague wording). Never truncate the y-axis to exaggerate differences; explicitly distinguish correlation from causation; never rely on legends alone.
- **Ablations, limitations & ethics**: Ablations (isolating component contributions) and limitations (scope, failure modes, ethics/de-identification status) are mandatory slides. Citations sit in compact bottom footnotes where used—no full-slide bibliography wall unless required.

## Visual Defaults & Minimum Sizes (Overridable)
- Scholarly style: no marketing copy, decorative photos, clip art, 3D, shadows, decorative gradients, watermarks, or confidentiality stamps.
- Projection readability on `960×540` canvas: body text `≥14 pt` equivalent, chart labels `≥10 pt` equivalent.
- Clear sans serif (`Liter`/`MiSans`) for body/labels (titles may use serif if signature specifies); white/near-white ground, two-color system (structural + accent), gray hierarchy, one warning color for negative/ablation signals, thin vector lines, minimal horizontal table rules.
- Inherit [slides_categories.md](../../slides_categories.md): no default cards (functional boxes exempt), no unjustified equal splits, no empty planned regions (whitespace allowed between argument stages).
