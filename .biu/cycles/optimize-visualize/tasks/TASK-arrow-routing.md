---
id: TASK-arrow-routing
title: Obstacle registry + auto-routing arrows in svgkit
status: ready
owner:
depends_on: []
created: 2026-07-03
updated: 2026-07-03
---

# TASK-arrow-routing: Obstacle registry + auto-routing arrows in svgkit

When executing this task, first check `owner`: if it names someone else, the task is already claimed — pick another. To claim it, set `owner` to your developer name (`git config user.name`), set `status` to `in_progress`, and update `updated` to today. When done, set `status` to `completed` and refresh `updated`.

**Reflection checks.** Pause and surface to the user — do not silently continue — when you catch yourself: appending to an already-long file, adding a 4th parameter to a function, copy-pasting a code block, or writing an `if (special case)` patch branch.

Then: a small fix the user approves goes into this task and its `## Implementation Decisions`; anything beyond this task's boundary goes into `## Notes` as a follow-up — do not expand scope.

## Objective

Give `Diagram` an obstacle registry + content-extent tracker (shared infrastructure — TASK-render-autofit reuses the extent), then make `arrow()` avoid obstacles by default: on a collision, route an orthogonal L-bend; when no clear route exists, keep the straight line and print a warning. `route="straight"` restores old behavior. Stops at `arrow()` — `lpath()`/`curve()` keep user-given geometry untouched.

## Context

This is the first consumer of the registry, which is why infrastructure and routing live in one task. svgkit currently throws away placement knowledge: `node()` returns a `Box` but `Diagram.__init__` (svgkit.py:187-193) keeps no record, so `arrow()` (svgkit.py:706) emits a straight line blind. Meanwhile the validator reconstructs obstacles from raw XML with heuristics (`is_non_obstacle`, validate_svg.py:384 — size thresholds, guesses). Generation-side avoidance is strictly stronger: svgkit knows exactly which rects are content boxes. Do not import validate_svg (the two scripts are deliberately decoupled — each has its own `text_width` copy); adapt its geometry ideas instead.

Design decisions already made (from SPEC `## Design` and user alignment):

- **Registry**: every method that returns a `Box` (`node`, `state`, `diamond`, `usecase`, `actor`, `cylinder`, `entity`, `class_box`, `step`, `panel`, `bar`) appends its bounds to `self._obstacles`. `container`/`scope`/`zone` are pass-through (arrows may cross them) — do not register. `raw()` is not registered.
- **Extent**: every emit (boxes, arrows, labels, legend) updates `self._extent` (min/max x/y). Build the mechanism here; TASK-render-autofit consumes it. Track label extents approximately via `text_width`.
- **Intersection test**: full segment-vs-rect (parametric clipping, ~20 lines, handles diagonal segments — deliberately stronger than the validator's orthogonal-only `segment_hits_bounds`, validate_svg.py:424). Exclude any obstacle that contains endpoint `a` or `b` (arrows depart from box edges; see the validator's `point_near_edge` tolerance idea, validate_svg.py:689).
- **Routing**: `route="auto"` (default) — on hit, try the two single-bend L candidates (horizontal-first, vertical-first) and pick the collision-free one; if both hit, keep the straight line and print a one-line stdout warning naming the segment and the box hit, suggesting a re-layout. Prefer the minimal detour; no multi-bend search this cycle (SPEC risk mitigation: minimal single-bend, warn-and-degrade).
- **Escape hatch**: `route="straight"` emits the old straight line unconditionally.
- Auto-routed L-bends reuse the existing `lpath` emission logic (svgkit.py:721-740) including longest-segment label placement.

### Critical Files

- `visualize/scripts/svgkit.py` — the whole change: `Diagram.__init__` (registry + extent), box methods (register), `arrow()` (routing), reuse `lpath` emission.
- `visualize/scripts/validate_svg.py` — read-only reference: `segment_hits_bounds` edge-tolerance handling and `check_arrow_collisions` (what the output must satisfy).
- `visualize/references/svg-cookbook.md` — §0 documents the svgkit API: add `route=` and the auto-avoidance behavior.
- `visualize/assets/gallery/` — static regression baseline (never regenerate these files in this task).

## Steps

- [ ] Add `_obstacles` + `_extent` tracking to `Diagram`; register all Box-returning methods; leave `container`/`scope`/`zone`/`raw` out.
- [ ] Implement segment-vs-rect intersection (orthogonal + diagonal) with endpoint-owner exclusion.
- [ ] Rewire `arrow()`: default auto-route with two single-bend candidates, warn-and-degrade fallback, `route="straight"` hatch; auto L-bends go through the `lpath` emission path.
- [ ] Document the new behavior and hatch in `svg-cookbook.md` §0.
- [ ] Build the verification layouts below and run the full check suite.

## Verify

If a subagent is available, spawn one to verify this task independently — it must not modify any project files. Approach: run inline `python3` scripts that build small diagrams via svgkit and pipe the output through `validate_svg.py`.

**The goal is to break it, not confirm it works.** Do not read code and narrate — run it. Do not stop when the happy path works; test edge cases and error states.

Recognize and reject common rationalizations:
- "The code looks correct based on my reading" — reading is not verification.
- "Tests already pass" — verify independently; don't trust the implementer's own tests as the only signal.
- "This is probably fine" — probably is not verified.

- [ ] Baseline: `python3 visualize/scripts/check_gallery.py` passes (17/17 — this task must not touch gallery files or validator behavior).
- [ ] Collision layout: three boxes A, B, C in a row; `arrow(A.right, C.left)` must cross B when straight. Default output passes `check_arrow_collisions`; `route="straight"` reproduces the old crossing line.
- [ ] Diagonal layout: an arrow whose straight path crosses a box diagonally gets L-bent (the validator can't see diagonals — assert via the emitted path coordinates instead).
- [ ] Adjacent-neighbor layout: `arrow(A.right, B.left)` between touching neighbors stays straight (endpoint-owner exclusion works; no spurious detours).
- [ ] Dense no-route layout: both L candidates blocked → output keeps the straight line and stdout carries exactly one warning naming segment and obstacle.
- [ ] `d.save()` output still ends with `</svg>` and passes the full validator suite for every layout above.

## Covers

- AC1
- AC5

## Implementation Decisions

## Notes
