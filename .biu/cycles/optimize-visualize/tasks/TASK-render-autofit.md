---
id: TASK-render-autofit
title: Canvas height auto-fit + deferred legend rendering
status: ready
owner:
depends_on: [TASK-arrow-routing]
created: 2026-07-03
updated: 2026-07-03
---

# TASK-render-autofit: Canvas height auto-fit + deferred legend rendering

When executing this task, first check `owner`: if it names someone else, the task is already claimed — pick another. To claim it, set `owner` to your developer name (`git config user.name`), set `status` to `in_progress`, and update `updated` to today. When done, set `status` to `completed` and refresh `updated`.

**Reflection checks.** Pause and surface to the user — do not silently continue — when you catch yourself: appending to an already-long file, adding a 4th parameter to a function, copy-pasting a code block, or writing an `if (special case)` patch branch.

Then: a small fix the user approves goes into this task and its `## Implementation Decisions`; anything beyond this task's boundary goes into `## Notes` as a follow-up — do not expand scope.

## Objective

Make `render()` grow the canvas height automatically so content and legend never clip, and make the legend position itself after the final height is known. Width is never auto-changed — horizontal overflow only warns. Stops at height/legend; no content re-layout of any kind.

## Context

Two coupled problems. (1) `Diagram(760, 240)` fixes the viewBox up front, but the agent only discovers the content didn't fit after validation fails (`check_box_viewbox_overflow`, `check_legend_overlap` — both exist because this is a real failure class). (2) `legend()` bakes `y = self.height - 20` into strings at call time (svgkit.py:874-875), so growing the height at render time would strand an already-placed legend. Deferral is therefore a prerequisite, not an option.

Design decisions already made (from SPEC `## Design` and user alignment):

- **Deferred legend**: `legend()` stores items (and any explicit `x`/`y`) instead of emitting; `render()` lays it out last. An explicit user-given `y` is respected verbatim (user took control); the wrap-to-new-line logic (svgkit.py:879-893) is preserved, just executed later.
- **Height**: grows, never shrinks — `Diagram(w, h)` means "at least h". Final height = max(declared, content extent bottom + legend block + bottom margin ~20). Uses `self._extent` built by TASK-arrow-routing.
- **Width**: a style convention (~680–760, SKILL.md step 2). Never auto-widen; if extent exceeds `width - 40` margin, print a warning naming the overflowing region so the agent re-lays-out.
- **Escape hatch**: a size-lock parameter (e.g. `Diagram(..., fixed_size=True)` or equivalent) restores fully manual behavior; pick the least-surprising spelling and document it.
- The legend's own footprint must feed back into the final height (legend rows can wrap — compute rows first, then height, then place).

### Critical Files

- `visualize/scripts/svgkit.py` — `legend()` (866-893) deferral, `render()` (927-940) fit logic, `Diagram.__init__` for the lock parameter; consumes `_extent` from TASK-arrow-routing.
- `visualize/references/svg-cookbook.md` — §0: document auto-height, the width warning, and the lock.
- `visualize/SKILL.md` — step 2's "Pick a viewBox" wording: height is now a floor, not a ceiling (small touch, keep step structure intact).
- `visualize/assets/gallery/` — static regression baseline.

## Steps

- [ ] Convert `legend()` to record-then-render; keep wrap behavior and explicit-position override.
- [ ] Implement height fit in `render()`: extent + legend block + margin, never below declared height; place legend beneath content.
- [ ] Add the horizontal-overflow warning (no auto-widen) and the size-lock escape hatch.
- [ ] Update `svg-cookbook.md` §0 and the SKILL.md step-2 wording.
- [ ] Build the verification layouts below and run the full check suite.

## Verify

If a subagent is available, spawn one to verify this task independently — it must not modify any project files. Approach: inline `python3` scripts building over/under-sized diagrams, piped through `validate_svg.py`.

**The goal is to break it, not confirm it works.** Do not read code and narrate — run it. Do not stop when the happy path works; test edge cases and error states.

Recognize and reject common rationalizations:
- "The code looks correct based on my reading" — reading is not verification.
- "Tests already pass" — verify independently; don't trust the implementer's own tests as the only signal.
- "This is probably fine" — probably is not verified.

- [ ] Baseline: `python3 visualize/scripts/check_gallery.py` passes (17/17).
- [ ] Overflow layout: declare `Diagram(760, 200)`, place a column + legend that needs ~400px. Output passes `check_box_viewbox_overflow` and `check_legend_overlap` with no manual resizing; legend sits below the lowest content with visible margin.
- [ ] Fit layout: content that already fits — declared height unchanged, legend at its classic position (no gratuitous growth).
- [ ] Lock: same overflow layout with the lock parameter → old clipping behavior returns (and the validator fails it, proving the hatch is honest).
- [ ] Width overflow: a row wider than the canvas → exactly one stdout warning, width unchanged in the output SVG.
- [ ] Explicit `legend(y=...)` is honored verbatim even when auto-fit grows the canvas.

## Covers

- AC2
- AC5

## Implementation Decisions

## Notes
