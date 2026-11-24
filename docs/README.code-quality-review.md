# Code Quality Review

An extremely strict structural review skill for PRs, commits, branches, files, directories, modules, or entire repositories — focused on structure and maintainability, not correctness: abstraction quality, structural simplification, file size discipline, and spaghetti-condition prevention.

## Philosophy: The "Code Judo" Move

Above all, this skill pushes the reviewer to be **ambitious** about code structure rather than stopping at cosmetic cleanups.

It actively searches for **"code judo" moves**: structural refactorings that preserve existing behavior while making the implementation dramatically simpler, smaller, more direct, and more elegant. If there is a path to delete whole categories of complexity rather than merely rearrange them, the review pushes hard for that path.

## Scope & Inputs

The review target can be a PR, commit, branch, file, directory, module, or repository. When no target is named, the skill reviews the current uncommitted diff if one is present, otherwise it asks once what to review. If the target is genuinely ambiguous, it asks once and then proceeds with the most likely reading.

## How a Review Runs

1. **Resolve scope and inventory** — gather the code in scope excluding generated, vendored, and build files, and measure source file sizes. When the scope is too large to read in full, triage to structural hotspots and disclose what was sampled.
2. **Read for intent and context** — read whatever explains why the code exists alongside surrounding callers, canonical helpers, layer boundaries, and repo conventions. Structure is judged against what the code is *for*, not isolated lines alone.
3. **Apply the standards** — review the code in scope and its surrounding boundaries against the eight standards below.
4. **Deliver the review** — findings in the output format below. On a PR, post inline comments on the offending lines plus one summary review; otherwise report in chat.

## Non-Negotiable Review Standards

Every review enforces eight explicit quality standards:

| # | Standard | Core Expectation |
|---|---|---|
| **0** | **Structural Simplification** | Seek "code judo" reframings so whole branches, helpers, modes, or layers disappear. Prefer solutions that feel inevitable in hindsight. |
| **1** | **1k-Line File Limit** | Treat production source files crossing or exceeding 1,000 lines (`wc -l`) without decomposition as a presumptive blocker; waive only for generated code, data tables, fixtures, or compelling structural reasons. |
| **2** | **No Spaghetti Growth** | Reject ad-hoc conditionals, scattered special cases, or one-off flags bolted onto unrelated flows. Push logic into a dedicated abstraction, state machine, or module. |
| **3** | **Design Cleanliness** | Do not rubber-stamp messy code or excuse tangled structure just because it works. Bias toward removing moving pieces altogether. |
| **4** | **Boring & Direct Code** | Flag generic mechanisms that hide simple data-shape assumptions, and thin wrappers or pass-through helpers that add indirection without buying clarity. |
| **5** | **Type & Boundary Cleanliness** | Question unnecessary optionality, casts, `any`/`unknown`, or silent fallbacks papering over unclear invariants. Prefer explicit typed models and shared contracts. |
| **6** | **Canonical Layering & Reuse** | Flag feature logic leaking into shared paths, implementation details escaping APIs, duplicated helpers or parallel implementations across modules, and logic living in the wrong layer. |
| **7** | **Orchestration & Atomicity** | Parallelize independent work when it is serialized for no reason. Ensure related updates cannot leave state half-applied. Do not over-index on micro-optimizations. |

## What Gets Flagged Aggressively

Findings are escalated when code exhibits any of the following critical smells:

- **Incidental Complexity**: Complicated implementations where a cleaner reframing would delete whole categories of complexity.
- **Complexity Shuffling**: Refactors that move complexity around without deleting any.
- **Flag Sprawl**: One-off booleans, nullable modes, or flags complicating existing control flow.
- **Buried Edge Cases**: Edge-case handling buried in the middle of an already busy function.
- **Copy-Pasted Logic**: Duplicated code where an extracted helper exists or should exist.
- **Missing Models**: Repeated conditionals signaling a missing model or missing helper.
- **"Temporary" Branching**: Provisional branches that will become permanent debt.
- **Tangled Modules**: God modules, circular dependencies, or parallel implementations across modules.

## Preferred Remedies

When structural issues are identified, the review favors high-leverage solutions:

- **Delete indirection** layers rather than polishing them.
- **Reframe state models** so conditionals disappear naturally rather than requiring centralized handling.
- **Shift ownership boundaries** so features become natural extensions of existing abstractions.
- **Turn special-case logic** into a simpler default flow with fewer exceptions; collapse duplicate branches into one clearer flow.
- **Extract helpers or pure functions** and split large files along natural cohesion seams.
- **Replace condition chains** with typed models or explicit dispatchers; make type boundaries explicit so control flow simplifies.
- **Separate orchestration from business logic**; parallelize independent work; restructure related updates into an atomic flow.
- **Move logic to the layer that already owns the concept**; reuse the canonical helper instead of a near-duplicate; delete wrappers that do not clarify the API.

## Output Format & Prioritization

Each review delivers a summary — scope, overall verdict or remediation priority, finding counts by severity, and one paragraph on the biggest structural call — followed by findings ordered by structural leverage:

1. Structural regressions and code-judo moves that delete whole categories of complexity
2. Spaghetti / branching complexity
3. Boundary, abstraction, and type-contract problems
4. File-size and decomposition concerns
5. Modularity and abstraction issues
6. Legibility and maintainability concerns

Every finding carries:

- **Severity**: Blocker (a presumptive blocker under the quality bar) / Major (a real maintainability problem) / Minor (worth fixing when convenient) / Nit (optional).
- **Location**: `file:line` or affected files with line anchors.
- **Issue**: the structural problem.
- **Remedy**: the concrete restructuring, in the spirit of the preferred remedies.

On a PR the review posts inline comments on the offending lines plus one summary review; otherwise it reports in chat. Low-value nits are suppressed when larger structural issues are present, broad reviews stay focused on the highest-conviction findings rather than an exhaustive dump, and one or two things done well are named — a review that only complains is less credible.

## Quality Bar & Presumptive Blockers

Behavioral correctness is never enough. The review flags as a blocker:

- Preserving incidental complexity when a plausible code-judo move would delete it.
- A production source file crossing or sitting past 1,000 lines without decomposition.
- Ad-hoc branching that tangles control flow or feature checks scattered across shared paths.
- Unnecessary wrappers, magical mechanisms, or cast-heavy contracts that obscure the real design.
- Duplicating canonical helpers or putting logic in the wrong architectural layer when a clear home exists.

## Self-Check Before Delivering

Before delivering, the review verifies:

- Every finding has a concrete location (`file:line` or anchored files), severity, and concrete remedy — no "maybe consider".
- The 1k-line check was measured with `wc -l`, not eyeballed, and any sampling is disclosed.
- Each blocker names the restructuring that would remove it, and cross-file claims were verified in code (or phrased as questions).
- The list is short and high-conviction; nits are suppressed when blockers exist.

## License

MIT
