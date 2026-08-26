# Code Quality Review

An extremely strict maintainability review skill focused on structural simplification, abstraction quality, file size discipline, and spaghetti-condition prevention.

## When to Use

- Before merging a PR that touches core modules.
- When you want a harsh, structural audit — not just a correctness check.
- When a codebase area feels like it's accumulating incidental complexity.

## What It Does

The skill runs a structured review workflow:

1. Identifies the diff scope.
2. Reads changed files in full, noting line counts and module boundaries.
3. Applies seven review dimensions to each meaningful change.
4. Produces findings grouped by severity.
5. States approval or blocking feedback.

## Review Dimensions

| # | Dimension | Core Question |
|---|-----------|---------------|
| 1 | Structural Simplification | Is there a "code judo" move that deletes whole categories of complexity? |
| 2 | File Size & Decomposition | Does the PR push a file past 1000 lines without strong justification? |
| 3 | Branching & Spaghetti Growth | Are new conditionals bolted onto unrelated flows? |
| 4 | Abstraction Quality | Is every abstraction earning its keep, or just adding indirection? |
| 5 | Type & Boundary Cleanliness | Are casts, optionality, or ad-hoc shapes obscuring real invariants? |
| 6 | Layer & Canonical Placement | Is logic in the right layer, reusing existing helpers? |
| 7 | Orchestration & Atomicity | Is independent work needlessly serialized, or state left half-applied? |

## Approval Bar

The skill does not approve merely because behavior is correct. It blocks on:

- Structural regressions or missed simplification opportunities.
- Unjustified file-size explosions.
- Spaghetti growth from ad-hoc branching.
- Unnecessary wrappers, casts, or architecture-boundary leaks.

## License

MIT
