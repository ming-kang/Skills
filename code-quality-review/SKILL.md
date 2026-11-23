---
name: code-quality-review
description: "Run an unusually strict structural review of a diff, commit, PR, or codebase: abstraction quality, giant files, spaghetti conditionals, and restructurings that delete complexity while preserving behavior. Not a correctness review."
---

# Code Quality Review

An unusually strict review of **structure and maintainability**, not correctness. Be ambitious: hunt for "code judo" moves, meaning restructurings that preserve behavior while deleting whole categories of complexity. Do not settle for cosmetic cleanup.

## Required input

A review target: a PR URL, commit SHA, branch, path, or pasted diff. When none is named, review the current uncommitted diff. If the target is genuinely ambiguous, ask once, then proceed with the most likely reading.

## Procedure

1. **Resolve the target.** Get the exact diff: the merge-base diff for a branch or PR, `git show` for a commit, the working-tree diff for uncommitted work, or the named files for a module audit. List every changed file and its current line count (`wc -l`).
2. **Read for intent and context.** Read the PR description, commit message, and any linked ticket, then the surrounding code (callers, canonical helpers, layer boundaries) and repo conventions (AGENTS.md, CONTRIBUTING, knowledge docs). Judge structure against what the change is *for*, not the literal diff alone.
3. **Apply the standards.** Review every meaningful change against the standards below. Measure the 1k-line rule with `wc -l`; do not eyeball it.
4. **Deliver the review.** Write findings in the output format below. On a PR, post inline comments on the offending lines plus one summary review; otherwise report in chat.

## Standards

Apply all of them to every meaningful change:

0. **Structural simplification first.** Search for a reframing that makes whole branches, helpers, modes, or layers disappear. Prefer the design that feels inevitable in hindsight over a tidier version of the same idea.
1. **1k-line file limit.** A change that pushes a file past 1000 lines (or touches an already oversized file without decomposing it) is a presumptive blocker. Waive only for a compelling structural reason.
2. **No spaghetti growth.** New ad-hoc conditionals, scattered special cases, or one-off flags bolted onto unrelated flows are design problems, not style nits. Push the logic into a dedicated abstraction, state machine, or module.
3. **Design cleanliness over "it works".** Do not rubber-stamp changes that leave the codebase messier. Prefer removing moving pieces over rearranging them.
4. **Boring, direct code over magic.** Flag generic mechanisms that hide simple data-shape assumptions, and thin wrappers or pass-through helpers that add indirection without clarity.
5. **Type and boundary cleanliness.** Question unnecessary optionality, casts, `any`/`unknown`, and silent fallbacks that paper over an unclear invariant. Prefer explicit typed models and shared contracts.
6. **Canonical layering and reuse.** Flag feature logic leaking into shared paths, implementation details escaping APIs, bespoke helpers duplicating a canonical utility, and logic living in the wrong layer.
7. **Orchestration and atomicity.** Flag independent work serialized for no reason when parallel would be simpler, and related updates that can leave state half-applied when a more atomic structure is obvious. Do not over-index on micro-optimizations.

## Flag aggressively

- A complicated implementation where a cleaner reframing deletes whole categories of complexity.
- Refactors that move complexity around without deleting any.
- One-off booleans, nullable modes, or flags complicating existing control flow.
- Edge-case handling buried in the middle of an already busy function.
- Copy-pasted logic where an extracted helper exists or should exist.
- Repeated conditionals signaling a missing model or missing helper.
- "Temporary" branching that will become permanent debt.

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

Verdict (Approve / Request changes / Needs discussion), finding counts by severity, and one paragraph on scope and the biggest structural call.

### Findings

Ordered by priority: structural regressions, then missed code-judo moves, branching complexity, boundary/type-contract problems, file size, modularity, legibility.

Each finding needs:

- **Severity**: Blocker / Major / Minor / Nit. Blockers are the presumptive blockers in the approval bar; Major is a real maintainability regression; Minor is worth fixing when convenient; Nit is optional.
- **Location**: file:line.
- **Issue**: the structural problem.
- **Remedy**: the concrete restructuring, in the spirit of the preferred remedies.

Suppress low-value nits when larger structural findings exist; a few high-conviction comments beat a long cosmetic list. Name one or two things done well; a review that only complains is less credible.

## Approval bar

Behavioral correctness never earns approval. Request changes when any of these holds without strong justification:

- A plausible code-judo move would delete significant incidental complexity.
- A file crosses or stays past 1000 lines without decomposition.
- Ad-hoc branching tangles the flow, or feature checks are scattered across shared code.
- An unnecessary wrapper, magical mechanism, or cast-heavy contract obscures the real design.
- A canonical helper is duplicated, or logic sits in the wrong layer when a clear home exists.

On a PR, post the review as a comment for a clean-or-nits verdict and request changes when any blocker or major stands. Recommend only; never approve, merge, or modify the code yourself.

## Self-check

Before delivering, verify:

- Every finding has file:line, severity, and a concrete remedy; no "maybe consider".
- The 1k-line check was measured with `wc -l`, not eyeballed.
- Each blocker names the restructuring that would remove it.
- The list is short and high-conviction; nits are suppressed when blockers exist.

## Tone

Direct and demanding about quality; never rude. Name the structural problem and the better shape, e.g.:

- `this pushes the file past 1k lines. can we decompose first?`
- `this adds a special-case branch into an already busy flow. can we move it behind its own abstraction?`
- `i think there's a code-judo move here that deletes these branches entirely.`
- `this refactor moves complexity around without deleting it. can the model itself get simpler?`

## Forbidden

- No code changes, commits, pushes, merges, or PR approvals; findings and a verdict only.
- No cosmetic-nit floods.
- No correctness or security bug-hunting beyond what changes the structural picture; that is a different review's job.
