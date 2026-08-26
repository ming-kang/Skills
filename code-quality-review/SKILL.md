---
name: code-quality-review
description: Run an extremely strict maintainability review for abstraction quality, giant files, and spaghetti-condition growth. Use for a code quality review, deep code quality audit, or especially harsh maintainability review.
disable-model-invocation: true
---

# Code Quality Review

A strict, structural code-quality review skill. The goal is not to verify correctness — it is to push for the simplest, most maintainable implementation that preserves behavior.

The guiding instinct: there is almost always a "code judo" move — a restructuring that uses the existing architecture more effectively and makes a change dramatically simpler, smaller, and more elegant. Do not stop at "this could be a bit cleaner." Actively search for the move that deletes whole categories of complexity.

## Workflow

1. **Identify scope.** Determine the diff to review (current branch vs main, or user-specified files/PRs).
2. **Read changed files in full.** Note pre-change line counts, module boundaries, and existing abstractions.
3. **Apply review dimensions** (below) to each meaningful change unit.
4. **Produce structured findings** grouped by severity — structural regressions first, cosmetic nits last.
5. **State approval or blocking feedback** against the approval bar.

## Review Dimensions

Each dimension lists its rule, the signals that indicate a violation, and preferred remedies.

---

### 1. Structural Simplification

**Rule:** Prefer the solution that makes the code feel inevitable in hindsight. If a reframing can delete whole branches, helpers, modes, or layers while preserving behavior, push hard for that path.

**Signals:**
- A complicated implementation where a cleaner reframing could delete whole categories of complexity.
- Refactors that move code around but fail to reduce concepts a reader must hold in their head.
- Refactors that technically pass tests but make the code less modular or less readable.

**Remedies:**
- Reframe the state model so conditionals disappear instead of getting centralized.
- Change the ownership boundary so the feature becomes a natural extension of an existing abstraction.
- Delete a whole layer of indirection rather than polishing it.
- Collapse duplicate branches into a single clearer flow.

---

### 2. File Size & Decomposition

**Rule:** Do not let a PR push a file past 1000 lines, or meaningfully grow an already-large file, without a very strong reason. Treat this as a presumptive blocker.

**Signals:**
- A file crossing 1000 lines due to the PR.
- A file already above 1000 lines receiving significant additions.
- New code that could clearly live in its own focused module.

**Remedies:**
- Extract helpers, subcomponents, or focused modules.
- Split along natural seams (data vs orchestration, feature-specific vs shared).

---

### 3. Branching & Spaghetti Growth

**Rule:** Be highly suspicious of new ad-hoc conditionals, scattered special cases, or one-off branches inserted into unrelated flows. If a change adds "weird if statements in random places," treat that as a design problem.

**Signals:**
- New conditionals bolted onto unrelated code paths.
- One-off booleans, nullable modes, or flags that complicate existing control flow.
- Narrow edge-case handling in the middle of an already busy function.
- "Temporary" branching that is likely to become permanent debt.

**Remedies:**
- Push the logic into a dedicated abstraction, helper, state machine, or policy object.
- Turn special-case logic into a simpler default flow with fewer exceptions.
- Replace condition chains with a typed model or explicit dispatcher.

---

### 4. Abstraction Quality

**Rule:** Every abstraction must earn its keep. Prefer direct, boring, maintainable code over hacky or magical code. Thin wrappers and identity abstractions that add indirection without buying clarity are code-quality problems.

**Signals:**
- Generic "magic" handling that hides simple structure.
- Thin wrappers or identity abstractions that add indirection without simplifying anything.
- Pass-through helpers that could be inlined with no loss of clarity.

**Remedies:**
- Delete wrappers that do not meaningfully clarify the API.
- Extract a helper or pure function only when it genuinely reduces local complexity.
- Inline indirection that exists for no clear reason.

---

### 5. Type & Boundary Cleanliness

**Rule:** Question unnecessary optionality, `unknown`, `any`, or cast-heavy code when a clearer type boundary could exist. Prefer explicit typed models over loosely-shaped ad-hoc objects.

**Signals:**
- Unnecessary casts, `any`, `unknown`, or optional params that muddy the real contract.
- Branches that rely on silent fallback to paper over an unclear invariant.
- Ad-hoc object shapes where a shared contract would be clearer.

**Remedies:**
- Make type boundaries more explicit so control flow gets simpler.
- Replace optional params with separate call sites or explicit variants.
- Prefer shared typed contracts over loosely-shaped objects.

---

### 6. Layer & Canonical Placement

**Rule:** Keep logic in the canonical layer. Do not let feature logic leak into shared paths, and do not duplicate an existing helper when a canonical one exists.

**Signals:**
- Feature-specific logic leaking into general-purpose modules.
- Bespoke helpers where the codebase already has a canonical utility for the job.
- Implementation details leaking through APIs.
- Logic added in the wrong layer/package when it should live somewhere more central.

**Remedies:**
- Move logic to the package/module/layer that already owns the concept.
- Reuse the existing canonical helper instead of introducing a near-duplicate.
- Move feature-specific logic behind a dedicated abstraction.

---

### 7. Orchestration & Atomicity

**Rule:** Treat unnecessary sequential orchestration and non-atomic updates as design smells when the cleaner structure is obvious.

**Signals:**
- Independent work serialized for no good reason.
- Related updates that can leave state half-applied.
- Orchestration complexity that makes the implementation more brittle.

**Remedies:**
- Parallelize independent work when that also simplifies orchestration.
- Restructure related updates into a more atomic flow.
- Separate orchestration from business logic.

---

## Review Tone

Be direct, serious, and demanding about quality. Do not be rude, but do not soften major maintainability issues into mild suggestions.

Example phrasings:

- `this pushes the file past 1k lines. can we decompose first?`
- `this adds another special-case branch into an already busy flow. can we move this behind its own abstraction?`
- `this works, but it makes the surrounding code more tangled. let's keep the behavior and restructure.`
- `i think there's a code-judo move here — can we reframe this so these branches disappear?`

## Approval Bar

Do not approve merely because behavior seems correct. The bar is:

- No clear structural regression.
- No obvious missed code-judo simplification when such a path is visible.
- No unjustified file-size explosion past 1000 lines.
- No spaghetti growth from ad-hoc branching in unrelated flows.
- No unnecessary wrappers, casts, or optionality obscuring the real design.
- No architecture-boundary leaks or canonical-helper duplication.

If any of these are present, leave explicit, actionable blocking feedback and push for a cleaner decomposition.
