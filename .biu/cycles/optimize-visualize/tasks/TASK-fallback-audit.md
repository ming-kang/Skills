---
id: TASK-fallback-audit
title: Audit svgkit bypass triggers, close top gaps, doc consistency sweep
status: ready
owner:
depends_on: [TASK-svgkit-guards]
created: 2026-07-03
updated: 2026-07-03
---

# TASK-fallback-audit: Audit svgkit bypass triggers, close top gaps, doc consistency sweep

When executing this task, first check `owner`: if it names someone else, the task is already claimed — pick another. To claim it, set `owner` to your developer name (`git config user.name`), set `status` to `in_progress`, and update `updated` to today. When done, set `status` to `completed` and refresh `updated`.

**Reflection checks.** Pause and surface to the user — do not silently continue — when you catch yourself: appending to an already-long file, adding a 4th parameter to a function, copy-pasting a code block, or writing an `if (special case)` patch branch.

Then: a small fix the user approves goes into this task and its `## Implementation Decisions`; anything beyond this task's boundary goes into `## Notes` as a follow-up — do not expand scope.

## Objective

Find out when and why generating agents bypass svgkit (hand-written fallback or `raw()`), rank the triggers, close the top 1–2 gaps, tighten SKILL.md so svgkit is the default wherever `python3` exists, and finish with a documentation consistency sweep over everything this cycle added. This is Track 2 of the SPEC; runs last so the sweep covers T1–T3's new behavior.

## Context

The cycle's diagnosis (SPEC `## Background & Facts`): svgkit's math is sound — occlusion and text-overflow defects only arise on the bypass paths, where no geometry protection exists. Every bypass the audit eliminates converts an unprotected generation into a protected one.

Design decisions already made (from SPEC `## Design`, `## Non-Goals` and user alignment):

- **Audit surface**: (a) SKILL.md — where its wording legitimizes hand-writing (the "Fallback — Python list method" section, the step-4 "Otherwise assemble…by hand" branch); (b) `svg-cookbook.md` — hand-written snippets an agent would copy instead of calling a helper; (c) `references/layout-patterns.md` — `raw()` usages that signal vocabulary gaps; (d) `assets/gallery/*.svg` — reverse-check: which visual elements in the ground-truth diagrams exceed the current svgkit vocabulary (those are the things agents must hand-write today).
- **Output**: a ranked trigger list recorded in this task's `## Notes` (frequency × defect risk). This list is the primary deliverable even where nothing gets fixed — it seeds the next cycle.
- **Gap closure**: top 1–2 triggers only. A new helper is justified only if small and deterministic (<~50 lines, pure geometry, no aesthetics heuristics); otherwise close the gap with explicit cookbook guidance ("to draw X, use Y + raw(layer=...)"). Declarative auto-layout is a Non-Goal — do not drift there.
- **SKILL.md tightening**: the hand-written fallback remains documented only for the no-`python3` environment; every `python3`-present path should read as "svgkit, full stop". Keep the file's structure and length discipline — sharpen wording, don't add sections.
- **Consistency sweep (AC8)**: every new parameter/behavior from T1–T3 (`route=`, auto-height, size lock, `align=`, label warning, required `raw()` layer) appears in both SKILL.md (where workflow-relevant) and cookbook §0. Fix any drift found.

### Critical Files

- `visualize/SKILL.md` — fallback wording, workflow steps 2/4/6 touchpoints.
- `visualize/references/svg-cookbook.md` — §0 API completeness; hand-written snippet audit.
- `visualize/references/layout-patterns.md` — `raw()` usage audit.
- `visualize/scripts/svgkit.py` — only if a top gap earns a small helper.
- `visualize/assets/gallery/` — reverse-audit source + static regression baseline.

## Steps

- [ ] Sweep the four audit surfaces; record the ranked bypass-trigger list in `## Notes`.
- [ ] Close the top 1–2 gaps (small helper or explicit cookbook recipe); leave the rest ranked in `## Notes` for the next cycle.
- [ ] Tighten SKILL.md fallback wording (hand-writing = no-`python3` only).
- [ ] Consistency sweep: T1–T3 behaviors present in SKILL.md + cookbook §0; fix drift.
- [ ] Run the verification below.

## Verify

If a subagent is available, spawn one to verify this task independently — it must not modify any project files. Approach: grep-based doc assertions plus running any new helper through the validator.

**The goal is to break it, not confirm it works.** Do not read code and narrate — run it. Do not stop when the happy path works; test edge cases and error states.

Recognize and reject common rationalizations:
- "The code looks correct based on my reading" — reading is not verification.
- "Tests already pass" — verify independently; don't trust the implementer's own tests as the only signal.
- "This is probably fine" — probably is not verified.

- [ ] Baseline: `python3 visualize/scripts/check_gallery.py` passes (17/17) — final gate for the whole cycle's code changes.
- [ ] The ranked trigger list exists in `## Notes` with at least the four audit surfaces covered.
- [ ] Each closed gap has a before/after demonstration: a snippet that previously required hand-written SVG now expressed via svgkit (run it, validate the output).
- [ ] If a helper was added: it is <~50 lines, deterministic, documented in cookbook §0, and its output passes the validator.
- [ ] Doc-consistency greps: `route=`, the size-lock parameter name, `align=`, and the `raw()` layer requirement each appear in `svg-cookbook.md`; SKILL.md mentions auto-height in step 2 and contains no unconditional hand-writing recommendation when `python3` exists.
- [ ] SKILL.md still reads coherently end-to-end (no orphaned references to removed wording).

## Covers

- AC7
- AC8
- AC5

## Implementation Decisions

## Notes
