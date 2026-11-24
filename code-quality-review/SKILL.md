---
name: code-quality-review
description: "Run a strict structural review: abstraction quality, giant files, spaghetti conditionals, and restructurings that delete complexity while preserving behavior."
---

# Code Quality Review

A strict review of **structure and maintainability**, not correctness. Be ambitious: hunt for "code judo" moves, meaning restructurings that preserve behavior while deleting whole categories of complexity. Do not settle for cosmetic cleanup.

## Required input

A review target: a PR, commit, branch, file, directory, module, or repository. When none is named, review the current uncommitted diff if present, otherwise ask once what to review. If the target is genuinely ambiguous, ask once, then proceed with the most likely reading.

## Procedure

1. **Resolve scope and inventory.** Gather the code in scope excluding generated, vendored, and build files, and measure source file sizes. When the scope is too large to read in full, triage to structural hotspots and note what was sampled.
2. **Read for intent and context.** Read whatever explains why the code exists alongside surrounding callers, canonical helpers, layer boundaries, and repo conventions. Judge structure against what the code is *for*, not isolated lines alone.
3. **Apply the standards.** Review the code in scope and its surrounding boundaries against the standards below.
4. **Deliver the review.** Write findings in the output format below. On a PR, post inline comments on the offending lines plus one summary review; otherwise report in chat.

## Standards

Apply all of them to everything meaningful in scope:

0. **Structural simplification first.** Search for a reframing that makes whole branches, helpers, modes, or layers disappear. Prefer the design that feels inevitable in hindsight over a tidier version of the same idea.
1. **1k-line file limit.** A production source file crossing or exceeding 1000 lines without decomposition is a presumptive blocker. Waive only for a compelling structural reason such as generated code, data tables, or fixtures.
2. **No spaghetti growth.** Ad-hoc conditionals, scattered special cases, or one-off flags bolted onto unrelated flows are design problems, not style nits. Push the logic into a dedicated abstraction, state machine, or module.
3. **Design cleanliness over "it works".** Do not rubber-stamp messy code or excuse tangled structure just because it works. Prefer removing moving pieces over rearranging them.
4. **Boring, direct code over magic.** Flag generic mechanisms that hide simple data-shape assumptions, and thin wrappers or pass-through helpers that add indirection without clarity.
5. **Type and boundary cleanliness.** Question unnecessary optionality, casts, `any`/`unknown`, and silent fallbacks that paper over an unclear invariant. Prefer explicit typed models and shared contracts.
6. **Canonical layering and reuse.** Flag feature logic leaking into shared paths, implementation details escaping APIs, duplicated helpers or parallel implementations across modules, and logic living in the wrong layer.
7. **Orchestration and atomicity.** Flag independent work serialized for no reason when parallel would be simpler, and related updates that can leave state half-applied when a more atomic structure is obvious. Do not over-index on micro-optimizations.

## Flag aggressively

- A complicated implementation where a cleaner reframing deletes whole categories of complexity.
- Refactors that move complexity around without deleting any.
- One-off booleans, nullable modes, or flags complicating existing control flow.
- Edge-case handling buried in the middle of an already busy function.
- Copy-pasted logic where an extracted helper exists or should exist.
- Repeated conditionals signaling a missing model or missing helper.
- "Temporary" branching that will become permanent debt.
- God modules, circular dependencies, or parallel implementations across modules.

## Preferred remedies

Prefer suggestions in this spirit:

- Delete a layer of indirection rather than polish it.
- Reframe the state model so conditionals disappear instead of being centralized.
- Shift an ownership boundary so the feature becomes a natural extension of an existing abstraction.
- Turn special-case logic into a simpler default flow with fewer exceptions; collapse duplicate branches into one clearer flow.
- Extract a helper or pure function; split a large file along natural cohesion seams.
- Replace condition chains with a typed model or explicit dispatcher; make type boundaries explicit so control flow simplifies.
- Separate orchestration from business logic; parallelize independent work; restructure related updates into an atomic flow.
- Move logic to the layer that already owns the concept; reuse the canonical helper instead of a near-duplicate; delete wrappers that don't clarify the API.

## Output format

### Summary

Scope, overall verdict or remediation priority, finding counts by severity, and one paragraph on the biggest structural call.

### Findings

Ordered by structural leverage: regressions and code-judo moves that delete whole categories of complexity first, then branching complexity, boundary/type-contract problems, file size, modularity, legibility. Keep broad reviews focused on the highest-conviction findings instead of an exhaustive dump.

Each finding needs:

- **Severity**: Blocker / Major / Minor / Nit. Blockers are the presumptive blockers in the quality bar; Major is a real maintainability problem; Minor is worth fixing when convenient; Nit is optional.
- **Location**: `file:line` (or affected files with line anchors).
- **Issue**: the structural problem.
- **Remedy**: the concrete restructuring, in the spirit of the preferred remedies.

Suppress low-value nits when larger structural findings exist; a few high-conviction comments beat a long cosmetic list. Name one or two things done well; a review that only complains is less credible.

## Quality bar

Behavioral correctness is never enough. Flag as a blocker when any of these holds without strong justification:

- A plausible code-judo move would delete significant incidental complexity.
- A production source file crosses or sits past 1000 lines without decomposition.
- Ad-hoc branching tangles the flow, or feature checks are scattered across shared code.
- An unnecessary wrapper, magical mechanism, or cast-heavy contract obscures the real design.
- A canonical helper is duplicated, or logic sits in the wrong layer when a clear home exists.

## Self-check

Before delivering, verify:

- Every finding has a concrete location (`file:line` or anchored files), severity, and concrete remedy; no "maybe consider".
- The 1k-line check was measured with `wc -l`, not eyeballed, and any sampling is disclosed.
- Each blocker names the restructuring that would remove it, and cross-file claims were verified in code (or phrased as questions).
- The list is short and high-conviction; nits are suppressed when blockers exist.
