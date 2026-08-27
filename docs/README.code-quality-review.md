# Code Quality Review

An extremely strict maintainability review skill focused on structural simplification, abstraction quality, file size discipline, and spaghetti-condition prevention.

## Two Modes

The skill establishes which mode applies before doing anything else, because the two produce different deliverables.

| Mode | Scope | Closes with |
|---|---|---|
| **Change review** | A diff against main, a commit, a commit range, or uncommitted work | An approval verdict |
| **Codebase audit** | A directory, a module, a subsystem, or the whole project | A prioritized remediation list |

The difference is whether a baseline exists. With one, the skill can see direction and intent — what a change made worse. Without one, nothing is "new," so the code is judged as it stands. If a request is ambiguous ("review the auth code"), the skill asks rather than guesses.

## When to Use

- Before merging a branch that touches core modules.
- After a commit that feels like it added incidental complexity.
- On uncommitted changes when you want a structural sanity check.
- On a module or subsystem that feels like it's accumulating debt, regardless of what changed recently.
- On a whole project you've inherited or haven't looked at structurally in a while.

## What It Does

**Change review:** identifies the baseline → reads changed files in full → applies the overriding lens and six dimensions → grounds each finding in the surrounding unchanged code → assembles the report → states the verdict.

**Codebase audit:** establishes the boundary → surveys file sizes, layout, and dependency direction *without* reading everything → triages to hotspots → reads those in full and applies the same lens and dimensions → grounds each finding → assembles a remediation list, naming what it surveyed but did not read.

An audit is a sample. The skill is required to say so rather than let the report imply full coverage.

## The Overriding Lens

Structural simplification sits above the individual dimensions rather than beside them: is there a "code judo" move that deletes whole categories of complexity, instead of rearranging them? Every dimension finding gets re-examined through it — the best version of a branching complaint is usually a reframing that removes the branch.

## Review Dimensions

| # | Dimension | Core Question |
|---|-----------|---------------|
| 1 | File Size & Cohesion | How many unrelated concerns does this file carry? |
| 2 | Branching & Spaghetti Growth | Are conditionals sitting in flows they have nothing to do with? |
| 3 | Abstraction Quality | Is every abstraction earning its keep, or just adding indirection? |
| 4 | Type & Boundary Cleanliness | Are casts, optionality, or ad-hoc shapes obscuring real invariants? |
| 5 | Layer & Canonical Placement | Is logic in the right layer, reusing existing helpers? |
| 6 | Orchestration & Atomicity | Is independent work needlessly serialized, or state left half-applied? |

Both modes share these six. Signals phrased as deltas — "new," "crossing," "becoming" — get read in their state form during an audit: same defect, weaker evidence, since a delta shows intent and a state does not.

On file size: the 1000-line threshold is a tripwire that starts the cohesion question, not the answer to it. A UI component is suspect well below it; a table-driven constants file can run far past it and stay healthy.

## Evidence Bar

Structural findings are claims about code outside the immediate change unit or hotspot — that a simpler framing exists, that a canonical helper already covers this, that logic belongs elsewhere. The skill requires each one to name its evidence: the resulting shape and what it deletes, the helper's actual path, the target module and its dependency direction.

Concerns that can't be grounded are still raised, but as explicit questions rather than blocking feedback.

## Output Expectations

Strictness applies to the bar each finding must clear, not to the number of findings. The skill prefers a few high-conviction comments over a long list of nits, scales its ambition to what it's reviewing, and keeps blocking feedback, optional suggestions, and open questions visibly separate.

## Verdict

**Change review** does not approve merely because behavior is correct. It blocks on structural regressions, missed simplifications, unjustified file-size explosions or cohesion regressions, spaghetti growth, unnecessary wrappers and casts, and architecture-boundary leaks. Blocking feedback must itself clear the evidence bar.

**Codebase audit** has nothing to approve. It delivers a plan ordered by structural leverage rather than by the severity of individual smells, with a rough blast radius per item, split into "fix before building further here" and "fix opportunistically next time you touch this."

## License

MIT
