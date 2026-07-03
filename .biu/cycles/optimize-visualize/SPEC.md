---
title: Optimize visualize
status: ready
created: 2026-07-03
updated: 2026-07-03
owner: ming-kang
baseline_commit: 7f08e8705cbd5d3f9feab214e838375d0474b79b
---

# SPEC: Optimize visualize

## Goal

Raise visualize's first-pass success rate — fewer generated diagrams needing rework for arrow collisions, text overflow, or layout defects.

## Background & Facts

- visualize generates self-contained SVG diagrams in a fixed house style (warm, flat, five color families) via `scripts/svgkit.py` + `scripts/validate_svg.py`, with 14 diagram types and a per-type ground-truth gallery (`assets/gallery/`, 17 SVGs).
- 8 reference docs under `references/`; SKILL.md orchestrates a 6-step workflow with a 3-strike validation retry strategy.
- History: `04b1b8a` promoted the self-check into a formal DRC pass (+388 lines in `validate_svg.py`), reverted three days later by `2dc99e1` (−413 lines); `d25cf57` then continued with lighter "validator enhancements". Quality assurance is an active concern, but the DRC form was rejected.
- Defect classes reported by the user (2026-07-03, all four options selected): arrow-through-box, canvas overflow / legend squeeze, global alignment & symmetry, text overflow still frequent. Plus three concrete modes: (1) external text hidden under later-drawn color blocks, (2) arrow-label length mismatch (fixed once in `d25cf57`, reduced but recurring), (3) rows of boxes not centered / asymmetric.
- Diagnosis from code: svgkit's z-order is correct (`_LAYERS` puts `labels` after `boxes`, svgkit.py:82), and `node()` computes box widths — so occlusion and text overflow can only occur **outside** svgkit: hand-written fallback SVG, or `raw()` which defaults to the `boxes` layer (svgkit.py:915). The dominant failure surface is agents falling back to hand-writing, not svgkit doing wrong math.
- svgkit automates local math (text width, box sizing, edge anchors, z-order) but not global geometry: no arrow obstacle-avoidance (`arrow()` draws straight lines), no canvas auto-fit, no auto legend placement, no row/column centering — exactly the gaps `validate_svg.py` checks for after the fact (`check_arrow_collisions`, `check_box_viewbox_overflow`, `check_legend_overlap`).

## Scope

**Track 1 — generation-time automation in svgkit** (use the global geometry svgkit already holds):
- Obstacle-avoiding arrows: `arrow()` detects straight-line hits against placed boxes and routes an L-bend automatically.
- Canvas auto-fit: at render time, compute the content bounding box; grow the viewBox (and reposition the legend) so nothing clips.
- Alignment helpers: centering options for `row()` / `col()` so multi-row layouts come out symmetric.
- Arrow-label geometry: label width checked against segment length (residual of the `d25cf57` fix).

**Track 2 — close the fallback gap** (defects only occur when agents bypass svgkit):
- Audit when/why agents fall back to hand-written SVG or `raw()` (vocabulary gaps? doc guidance?).
- Fix the `raw()` default-layer trap (`layer="boxes"` buries text under later boxes).
- Plug the highest-frequency vocabulary gaps found by the audit; strengthen SKILL.md guidance toward svgkit.

## Non-Goals

- Context efficiency, coverage expansion, and workflow changes — considered and deferred this cycle (2026-07-03 interview).
- Declarative auto-layout (agent declares nodes/edges, svgkit computes all coordinates) — a paradigm change, too heavy for this cycle; revisit later.
- Strengthening `validate_svg.py` rules — the reverted DRC path; validator stays light.

## Constraints

- Zero third-party dependencies (`svgkit` is python3 stdlib only) — existing hard rule.
- Single style, no themes / variants — existing hard rule.

## Design

**Track 1 mechanics:**
- `arrow()` obstacle avoidance: before emitting a straight segment, test it against placed obstacle bounds (boxes/nodes; containers and zones are pass-through). On a hit, route an orthogonal L-bend through the clear gap; if no clear route exists (dense layout), keep the straight line and print a warning to stdout so the generating agent sees it and can re-layout.
- Canvas auto-fit: at `render()`, compute the content bounding box. **Height** grows automatically to fit content + legend (content-driven). **Width** is a style convention (~680–760): never auto-widen; print a warning instead so the agent re-lays-out.
- Alignment: `row()` / `col()` gain a centering option — box groups on each row share a common horizontal midline; assertable geometry, no aesthetic heuristics.
- Arrow labels: at emit time, compare label width (`text_width`) against segment length; on mismatch, warn with the suggested fix (shorter label or midpoint offset).
- Every automation ships an escape hatch (e.g. `route="straight"`, explicit size lock) and is **on by default**.

**Track 2 mechanics:**
- Audit: sweep SKILL.md, the cookbook, and gallery usage for the situations that push agents to hand-written SVG or `raw()`; rank by frequency.
- `raw()` layer semantics: make the layer an explicit, conscious choice (no silent `boxes` default burying text); update cookbook examples accordingly.
- Close the top vocabulary gaps found (new helpers only if small and deterministic); tighten SKILL.md wording that steers toward svgkit wherever python3 exists.

## Decisions

- **Decision**: This cycle targets first-pass success rate, not context efficiency / coverage / workflow.
  - Reasoning: recent commit history (gallery regression check → DRC pass → revert → validator enhancements) shows generation quality is the active battleground; user confirmed.
  - Alternatives considered: context efficiency (deferred — no acute pain reported), coverage expansion (conflicts with doc size), workflow polish (mature enough).

- **Decision**: Invest in generation-time prevention (svgkit automation); keep validation light.
  - Reasoning: the DRC revert (`2dc99e1`) taught three lessons, all user-confirmed — too many false positives (fixing "problems" cost more than drawing), the 3-strike retry × strict DRC made every generation a marathon, and the form itself was wrong: effort belongs before the error exists, not in post-hoc checking.
  - Alternatives considered: strengthening `validate_svg.py`'s rule set — rejected; that is the reverted DRC path.

- **Decision**: Both tracks this cycle — svgkit automation and closing the fallback gap.
  - Reasoning: complementary failure surfaces; fixing only one leaves the other dragging first-pass rate. Both are small, deterministic, generation-time changes consistent with the DRC lesson.
  - Alternatives considered: track 1 only (fallback symptoms persist), track 2 only (defers high-certainty routing wins).

- **Decision**: New automations are on by default, each with an escape hatch — not opt-in.
  - Reasoning: svgkit has no persistent downstream callers to break — every diagram is a freshly written script, and gallery assets are static files unaffected by API behavior. Opt-in would hand "remembering to do it right" back to the agent, defeating the cycle's purpose.
  - Alternatives considered: opt-in parameters — rejected (agents won't reliably opt in); silent hard-failure on unroutable arrows — rejected in favor of warn-and-degrade.

## Risks

- **Risk**: New helpers or checks recreate the DRC failure mode (false positives, heavier loop).
  - Impact: gets reverted like `04b1b8a`; the cycle is wasted.
  - Mitigation: any new validation rule must be zero-false-positive against the existing gallery (17 ground-truth SVGs); prefer svgkit doing the right thing by construction over checking after the fact.

- **Risk**: Auto-routed L-bends occasionally look worse than the straight line they replace (detours, visual noise in dense layouts).
  - Impact: aesthetic regressions the user has to hand-fix — the very rework this cycle fights.
  - Mitigation: route only on an actual collision; prefer the minimal single-bend detour; `route="straight"` escape hatch; warn-and-degrade when no clear route exists.

## Open Questions

(none — all resolved 2026-07-03)

## Acceptance Criteria

- [ ] AC1: A layout where the straight path must cross a box: default `arrow()` emits a route that passes `check_arrow_collisions`; `route="straight"` restores the old behavior.
- [ ] AC2: A layout whose content exceeds the declared height: after `render()`, output passes `check_box_viewbox_overflow` and `check_legend_overlap` without manual resizing; horizontal overflow produces a warning, never auto-widening.
- [ ] AC3: `row()`/`col()` centering option produces rows whose box groups share a common horizontal midline (asserted numerically on a test layout).
- [ ] AC4: An over-long arrow label triggers a warning naming the segment and suggested fix.
- [ ] AC5: `python3 scripts/check_gallery.py` still passes for all 17 gallery SVGs (no regression from validator or doc changes).
- [ ] AC6: `raw()` no longer silently buries text: layer is an explicit choice, cookbook examples updated, and a `raw()`-with-text usage renders text above boxes.
- [ ] AC7: Fallback audit findings recorded (list of bypass triggers, ranked); the top gaps addressed with a helper or explicit doc guidance, each demonstrated by a snippet that previously required hand-written SVG.
- [ ] AC8: SKILL.md and `svg-cookbook.md` document every new behavior and escape hatch.
