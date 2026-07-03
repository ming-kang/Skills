---
id: TASK-svgkit-guards
title: Centering for row/col, arrow-label length guard, explicit raw() layer
status: ready
owner:
depends_on: [TASK-render-autofit]
created: 2026-07-03
updated: 2026-07-03
---

# TASK-svgkit-guards: Centering for row/col, arrow-label length guard, explicit raw() layer

When executing this task, first check `owner`: if it names someone else, the task is already claimed — pick another. To claim it, set `owner` to your developer name (`git config user.name`), set `status` to `in_progress`, and update `updated` to today. When done, set `status` to `completed` and refresh `updated`.

**Reflection checks.** Pause and surface to the user — do not silently continue — when you catch yourself: appending to an already-long file, adding a 4th parameter to a function, copy-pasting a code block, or writing an `if (special case)` patch branch.

Then: a small fix the user approves goes into this task and its `## Implementation Decisions`; anything beyond this task's boundary goes into `## Notes` as a follow-up — do not expand scope.

## Objective

Three small generation-time guards, one theme (defects the user reported that are cheap to prevent by construction): center-alignment for `col()`/`row()`, a warning when an arrow label outgrows its segment, and an explicit layer choice for `raw()` so text can no longer be silently buried under boxes.

## Context

All three are localized surgeries on `svgkit.py`; they are bundled because splitting them into three handoffs costs more than the changes themselves.

Design decisions already made (from SPEC `## Design` and user alignment):

- **`col()` centering**: default flips to centered — the user's reported pain is exactly "rows of boxes not centered / asymmetric", and svgkit has no persistent callers to break (SPEC decision: automations on by default). `align="left"` keeps the old left-edge behavior and stays available for list-style columns. Implementation: widths are computable before placement (`box_width` is a pure function, svgkit.py:108) — pre-compute per-spec widths, then place each box at `x + (max_w - w) / 2`. Update the docstring that currently promises left-alignment (svgkit.py:227-229).
- **`row()` alignment**: mixed-height rows (40px single-line next to 56px two-line boxes) get a vertical-midline option; same pre-compute approach with heights. Default: centered midlines, `align="top"` for the old top-edge baseline.
- **Arrow-label guard**: in `_place_label` (svgkit.py:766), compare `text_width(label, 12)` against the carrying segment's length; if the label is longer (allow a small tolerance), print a one-line warning naming the label and suggesting a shorter text or a `plate`d offset. Warn only — never mutate or truncate the label (residual of the `d25cf57` label fix; user says mismatches still recur).
- **`raw()` layer**: drop the silent `layer="boxes"` default — make `layer` required. The error message must list the layers with a one-line hint each (text → `"labels"`, backdrop art → `"containers"`, shape art → `"boxes"`). This kills the reported "external text hidden under later color blocks" mode at its root. Update every `raw()` example in the cookbook accordingly.

### Critical Files

- `visualize/scripts/svgkit.py` — `row()`/`col()` (207-237), `_place_label()` (766-783), `raw()` (915-923).
- `visualize/references/svg-cookbook.md` — §0 API docs: `align=` options, label-length warning, required `raw()` layer with layer-choice table.
- `visualize/assets/gallery/` — static regression baseline.

## Steps

- [ ] `col()`: pre-compute widths, centered default, `align="left"` fallback; fix the docstring; mirror for `row()` vertical midlines.
- [ ] `_place_label()`: segment-length vs label-width warning (warn-only).
- [ ] `raw()`: required `layer` with guiding error message.
- [ ] Update cookbook §0 for all three; sweep cookbook `raw()` examples to pass an explicit layer.
- [ ] Build the verification layouts below and run the full check suite.

## Verify

If a subagent is available, spawn one to verify this task independently — it must not modify any project files. Approach: inline `python3` scripts asserting emitted coordinates and stdout/stderr, plus the validator suite.

**The goal is to break it, not confirm it works.** Do not read code and narrate — run it. Do not stop when the happy path works; test edge cases and error states.

Recognize and reject common rationalizations:
- "The code looks correct based on my reading" — reading is not verification.
- "Tests already pass" — verify independently; don't trust the implementer's own tests as the only signal.
- "This is probably fine" — probably is not verified.

- [ ] Baseline: `python3 visualize/scripts/check_gallery.py` passes (17/17).
- [ ] Centering: a `col()` of three boxes with very different title lengths — assert numerically that all three `cx` values are equal; with `align="left"` all `x` values are equal (old behavior).
- [ ] Mixed-height `row()`: a 40px box next to a 56px box — midlines equal by default; `align="top"` restores equal `y`.
- [ ] Label guard: an `arrow()` with a label wider than its short segment → exactly one warning; a comfortably fitting label → silent. The SVG itself is unchanged by the warning path.
- [ ] `raw()` without `layer` raises with the guiding message; `raw('<text ...>', layer="labels")` followed by a later `node()` overlapping it renders the text above the box (inspect emitted layer order).
- [ ] Interplay: a centered `col()` inside an auto-fit canvas (TASK-render-autofit) still passes the full validator suite — the two features compose.

## Covers

- AC3
- AC4
- AC6
- AC5

## Implementation Decisions

## Notes
