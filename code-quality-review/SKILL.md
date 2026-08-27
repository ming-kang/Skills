---
name: code-quality-review
description: Run an extremely strict maintainability review for abstraction quality, giant files, and spaghetti-condition growth. Use for a code quality review, deep code quality audit, or especially harsh maintainability review.
disable-model-invocation: true
---

# Code Quality Review

Perform a deep code quality audit of the code in scope. Rethink how the code should be structured and implemented, and report what a better version would look like — concretely enough to act on, without acting on it yourself. Work to improve abstractions, modularity, reduce spaghetti code, improve succinctness and legibility. Be ambitious — if there is a clear path to improving the implementation that involves restructuring some of the codebase, go for it. Be extremely thorough and rigorous. Measure twice, cut once.

The guiding instinct: there is almost always a "code judo" move — a restructuring that uses the existing architecture more effectively and makes a change dramatically simpler, smaller, and more elegant. Do not stop at "this could be a bit cleaner." Actively search for the move that deletes whole categories of complexity.

Strictness is about the bar each finding must clear, not the number of findings produced. A long list of ungrounded, low-conviction comments is a worse review than three that land.

## Review Modes

Establish which mode applies before anything else — it changes the scope, the workflow, and the closing verdict.

**Change review** — a diff against main, a specific commit, a commit range, or uncommitted work. You have a baseline, so you can see direction and intent: what this change made worse. Closes with an approval verdict.

**Codebase audit** — a directory, a module, a subsystem, or the whole project, with no reference point. Nothing is "new," so you judge the code as it stands. Closes with a prioritized remediation list.

If the request is ambiguous — "review the auth code" can mean either — ask which one is wanted instead of guessing. The two produce different deliverables.

## Workflow

### Change review

1. **Identify scope.** Establish the baseline: a diff against main, a specific commit, a commit range, or uncommitted changes.
2. **Read changed files in full.** Note line counts, module boundaries, and existing abstractions.
3. **Apply the overriding lens, then the review dimensions** to each meaningful change unit.
4. **Ground every structural finding.** Read the unchanged code a claim depends on — the call sites, the canonical helper you believe exists, the layer you want logic moved to. Measure twice, cut once: an ungrounded restructuring claim is a question, not a blocker.
5. **Assemble the report** per Output Expectations.
6. **State the verdict** against the approval bar.

### Codebase audit

1. **Establish the boundary.** Which directories or modules are in scope, and what is explicitly out.
2. **Survey before reading.** File sizes, directory layout, dependency direction, entry points. A whole-project audit does not fit in context — do not try to read everything.
3. **Triage to hotspots.** The largest files, the most-imported modules, the places where several concerns visibly collide, and whatever the survey suggests the rest depends on.
4. **Read the hotspots in full**, then apply the overriding lens and the review dimensions.
5. **Ground every structural finding** — same bar as above.
6. **Assemble a prioritized remediation list.** State what you surveyed but did not read. An audit is a sample; a report that hides its sampling reads as if it covered everything.

## The Overriding Lens: Structural Simplification

This is not one dimension among the others — it sits above them. Run it first, and re-run it after every finding below: the best version of a branching complaint is usually a reframing that deletes the branch entirely.

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

## Review Dimensions

Each dimension lists its rule, the signals that indicate a violation, and preferred remedies.

Several signals are phrased as deltas — "new," "crossing," "becoming." Those assume a baseline. In audit mode, read them in their state form: "a new conditional bolted onto an unrelated flow" becomes "a conditional that has nothing to do with this function's core job." The defect is identical; the evidence is weaker. A delta shows intent and direction, a state does not — so when you do have a baseline, prefer the delta and say what changed.

---

### 1. File Size & Cohesion

**Rule:** Judge a file by how many unrelated concerns it carries, not only by its length. Separately, do not let a change push a file past 1000 lines, or meaningfully grow an already-large file, without a very strong reason — treat that as a presumptive blocker.

**Signals:**
- A previously cohesive module becoming more coupled, more stateful, or harder to scan.
- The change leaving a file responsible for one more thing than it was before.
- A file crossing 1000 lines due to the change, or an already-large file receiving significant additions.
- Code that could clearly live in its own focused module.

**Remedies:**
- Extract helpers, subcomponents, or focused modules.
- Split along natural seams (data vs orchestration, feature-specific vs shared).

Calibrate the line threshold to the kind of file. A UI component or a busy orchestrator is already suspect well below 1000 lines; a table-driven constants or fixture file can run far longer and stay healthy. The threshold is a tripwire that starts the cohesion question — it is not the answer to it. In audit mode the tripwire is simply a file already past 1000 lines, and the question it opens is the same: how many unrelated concerns is this carrying?

---

### 2. Branching & Spaghetti Growth

**Rule:** Be highly suspicious of ad-hoc conditionals, scattered special cases, or one-off branches sitting in unrelated flows. "Weird if statements in random places" is a design problem, not a stylistic nit.

**Signals:**
- Conditionals bolted onto code paths they have nothing to do with.
- One-off booleans, nullable modes, or flags that complicate existing control flow.
- Narrow edge-case handling in the middle of an already busy function.
- Repeated conditionals that signal a missing model or missing helper.
- "Temporary" branching that has become, or is likely to become, permanent debt.

**Remedies:**
- Push the logic into a dedicated abstraction, helper, state machine, or policy object.
- Turn special-case logic into a simpler default flow with fewer exceptions.
- Replace condition chains with a typed model or explicit dispatcher.

---

### 3. Abstraction Quality

**Rule:** Every abstraction must earn its keep. Prefer direct, boring, maintainable code over hacky or magical code. Thin wrappers and identity abstractions that add indirection without buying clarity are code-quality problems.

**Signals:**
- Generic "magic" handling that hides simple structure.
- Thin wrappers or identity abstractions that add indirection without simplifying anything.
- Pass-through helpers that could be inlined with no loss of clarity.
- Copy-pasted logic where an extracted helper is the obvious move.

**Remedies:**
- Delete wrappers that do not meaningfully clarify the API.
- Extract a helper or pure function only when it genuinely reduces local complexity.
- Inline indirection that exists for no clear reason.

---

### 4. Type & Boundary Cleanliness

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

### 5. Layer & Canonical Placement

**Rule:** Keep logic in the canonical layer. Do not let feature logic leak into shared paths, and do not duplicate an existing helper when a canonical one exists.

**Signals:**
- Feature-specific logic sitting in general-purpose modules.
- Bespoke helpers where the codebase already has a canonical utility for the job.
- Implementation details leaking through APIs.
- Logic living in the wrong layer/package when it belongs somewhere more central.

**Remedies:**
- Move logic to the package/module/layer that already owns the concept.
- Reuse the existing canonical helper instead of introducing a near-duplicate.
- Move feature-specific logic behind a dedicated abstraction.

---

### 6. Orchestration & Atomicity

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

## Evidence Bar

Every structural finding is a claim about code you did not read as part of the change unit or hotspot: that a simpler framing exists, that a canonical helper already covers this, that the logic belongs in another layer. Do not make such a claim from a diff or a single file alone.

Before reporting one, name the evidence:

- **"There is a code-judo move here"** — sketch the resulting shape concretely enough to argue with, and say what disappears: which branches, which helper, roughly how many lines.
- **"A canonical helper already exists"** — give its path and symbol. If you have not found it, ask whether one exists instead of asserting that it does.
- **"This belongs in another layer"** — name the target module and confirm the dependency direction actually permits the move.
- **"This file is doing too much"** — name the distinct concerns you counted.

An ungrounded concern is still worth raising — as an explicit question, marked as one. A confidently-worded finding that turns out to be wrong costs more than the issue it would have caught: it burns the author's trust in the entire review, including the findings that were right.

This bar matters more in audit mode, and is easier to meet there. Without a diff to bound the work there is more room to drift into speculation — but the surrounding code you need as evidence is already in scope.

## Output Expectations

Prefer a small number of high-conviction findings over a long list of cosmetic notes.

- Do not flood the review with low-value nits when larger structural issues are present. Below a real structural finding, the nits are noise — cut them. This applies with more force in audit mode, where the raw number of possible findings is unbounded.
- Scale ambition to what you are reviewing. A 30-line bugfix does not warrant a module-rewrite proposal; a new subsystem invites one. An audit of an established module should expect to find real debt and say so plainly — while still leading with the few findings that carry the most leverage.
- Separate blocking feedback, optional suggestions, and ungrounded questions. Do not let the three blur together.
- Order findings by severity: structural regressions and missed simplifications first, cosmetic concerns last.

## Review Tone

Be direct, serious, and demanding about quality. Do not be rude, but do not soften major maintainability issues into mild suggestions.

Example phrasings:

- `this pushes the file past 1k lines. can we decompose first?`
- `this adds another special-case branch into an already busy flow. can we move this behind its own abstraction?`
- `this works, but it makes the surrounding code more tangled. let's keep the behavior and restructure.`
- `this refactor moves complexity around, but doesn't really delete it. can we make the model itself simpler?`
- `i think there's a code-judo move here — can we reframe this so these branches disappear?`

## Verdict

### Change review — approval bar

Do not approve merely because behavior seems correct. The bar is:

- No clear structural regression.
- No obvious missed code-judo simplification when such a path is visible.
- No unjustified file-size explosion, and no cohesion regression in a previously focused module.
- No spaghetti growth from ad-hoc branching in unrelated flows.
- No unnecessary wrappers, casts, or optionality obscuring the real design.
- No architecture-boundary leaks or canonical-helper duplication.

If any of these are present, leave explicit, actionable blocking feedback and push for a cleaner decomposition.

Blocking feedback must clear the evidence bar. If a concern is real but ungrounded, raise it as a question and let the rest of the review decide approval.

### Codebase audit — remediation list

There is nothing to approve. Deliver a plan instead:

- Order by structural leverage, not by the severity of individual smells. One fix that dissolves a whole category beats five that each clean one spot.
- Give each item a rough blast radius, so the reader can sequence the work.
- Separate "fix before building anything further here" from "fix opportunistically the next time you touch this."
- Do not present the list as exhaustive, and do not imply it can be done in one pass. Carry forward the sampling you named in the workflow.
