# Code Quality Review

An extremely strict maintainability review skill focused on implementation quality, structural simplification, abstraction cleanliness, file size discipline, and spaghetti-condition prevention.

## Philosophy: The "Code Judo" Move

Above all, this skill pushes the reviewer to be **ambitious** about code structure rather than stopping at cosmetic cleanups.

It actively searches for **"code judo" moves**: structural refactorings that preserve existing behavior while making the implementation dramatically simpler, smaller, more direct, and more elegant. If there is a path to delete whole categories of complexity rather than merely rearrange them, the review pushes hard for that path.

## Non-Negotiable Review Standards

Every review enforces eight explicit quality standards:

| # | Standard | Core Expectation |
|---|---|---|
| **0** | **Structural Simplification** | Seek "code judo" reframings so whole branches, helpers, or layers disappear. Prefer solutions that feel inevitable in hindsight. |
| **1** | **1k-Line File Limit** | Treat files crossing or exceeding 1,000 lines as a strong smell. Require decomposition into helpers, subcomponents, or modules. |
| **2** | **No Spaghetti Growth** | Reject ad-hoc conditionals or special cases scattered across unrelated flows. Push logic into dedicated abstractions or state machines. |
| **3** | **Design Cleanliness** | Do not rubber-stamp "it works" code that leaves the codebase messier. Bias toward removing moving pieces altogether. |
| **4** | **Boring & Direct Code** | Avoid magic handling, pass-through helpers, or thin wrappers that add indirection without buying clarity. |
| **5** | **Type & Boundary Cleanliness** | Question unnecessary optionality, casts, `unknown`, or `any`. Prefer explicit typed models and shared contracts. |
| **6** | **Canonical Layering & Reuse** | Prevent feature logic from leaking into shared paths. Reuse canonical codebase utilities instead of introducing bespoke one-offs. |
| **7** | **Orchestration & Atomicity** | Parallelize independent async work when obvious. Ensure related updates flow atomically rather than leaving partial state. |

## Primary Review Checklist

For every meaningful change or audited module, the reviewer probes:

- **Simplification**: Is there a code-judo move that makes this dramatically simpler? Can concepts, branches, or helper layers be eliminated?
- **Architecture**: Does this improve or degrade local architecture? Does logic live in the canonical file and layer?
- **Branching**: Are ad-hoc conditionals or flags being bolted onto unrelated paths?
- **Scale & Cohesion**: Did a cohesive module become more coupled or stateful? Does a file exceed healthy size boundaries?
- **Abstractions**: Is every abstraction earning its keep, or is it a superfluous wrapper?
- **Contracts**: Are casts, `any`, or loose object shapes obscuring invariants?
- **Concurrency & State**: Is orchestration unnecessarily sequential or non-atomic?

## What Gets Flagged Aggressively

Findings are escalated when code exhibits any of the following critical smells:

- **Incidental Complexity**: Complicated implementations where a cleaner reframing would delete moving parts.
- **Complexity Shuffling**: Refactors that move code around without reducing cognitive load for the reader.
- **Bloated Files**: Files exceeding 1,000 lines without decomposition.
- **Scattered Conditionals**: Ad-hoc special-case checks, one-off flags, or feature logic leaking into shared modules.
- **Magic & Thin Wrappers**: Identity abstractions, pass-through helpers, or magic behavior obscuring simple data flow.
- **Type Dilution**: Unnecessary casts, `any`, `unknown`, or silent fallbacks papering over unclear invariants.
- **Helper Duplication**: Bespoke one-off utilities duplicating existing canonical helpers.
- **Suboptimal Orchestration**: Serialized independent async operations or non-atomic state mutations.

## Preferred Remedies

When structural issues are identified, the review favors high-leverage solutions:

- **Delete indirection** layers rather than polishing them.
- **Reframe state models** so conditionals disappear naturally rather than requiring centralized handling.
- **Shift ownership boundaries** so features become natural extensions of existing abstractions.
- **Turn special-case branches** into simpler default flows with fewer exceptions.
- **Extract helpers or pure functions** and split large files along natural cohesion seams.
- **Replace condition chains** with typed models or explicit dispatchers.
- **Parallelize independent operations** and enforce atomic state updates.

## Output Expectations & Prioritization

Reviews prioritize high-conviction structural feedback over superficial nits:

1. Structural code-quality regressions
2. Missed opportunities for dramatic simplification / code-judo restructuring
3. Spaghetti / branching complexity increases
4. Boundary, abstraction, and type-contract problems
5. File-size and decomposition concerns
6. Modularity and abstraction issues
7. Legibility and maintainability concerns

Low-value cosmetic comments are suppressed when larger structural issues are present.

## Approval Bar & Presumptive Blockers

Working code is **not** sufficient for approval. The review blocks on:

- Preserving incidental complexity when an obvious simplification path is visible.
- Pushing a file past 1,000 lines (or touching an oversized file without decomposing it).
- Introducing ad-hoc branching that tangles control flow.
- Scattering feature checks across shared code paths.
- Introducing unnecessary wrappers, magic, or cast-heavy contracts.
- Duplicating canonical helpers or putting logic in the wrong architectural layer.

## License

MIT
