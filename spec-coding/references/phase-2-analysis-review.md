# Phase 2: Analysis Review

**Goal**: Present findings to the user, propose architectural options, test the recommendation, and reach a confirmed direction before any planning begins.

---

## Step 1: Present the Analysis

Summarize the analysis for the user. Do not dump the full documents — synthesize. Cover:

1. **Project overview**: What this project is, its tech stack, approximate scale
2. **Key findings**: What you discovered that is relevant to the task — important modules, dependencies, patterns
3. **Risk highlights**: The top 2–3 risks from the risk register, with brief explanations of why they matter

Keep this to one focused message. The user can read the raw files if they want detail.

---

## Step 2: Propose Architectural Options

Propose **2–3 options** for how to approach the task. Always include one minimal option.

For each option:

| Field | Content |
|-------|---------|
| **Summary** | One sentence: what this approach does |
| **Effort** | S / M / L / XL |
| **Risk** | What could go wrong |
| **Builds on** | Which existing code or patterns it leverages |

State your recommendation explicitly. Do not hedge — pick one and say why.

---

## Step 3: Adversarial Test the Recommendation

Before presenting, attack your own recommendation internally:

1. **What would make this fail?** Identify the single most likely failure mode.
2. **If the attack holds**: Deform the design to survive it. Present the deformed version as the recommendation, noting what changed and why.
3. **If the attack shatters the approach entirely**: Discard that option and tell the user why it was eliminated. Promote your second-best option to recommendation and repeat the adversarial test.

Present the result of this process — the hardened recommendation — not your original unexamined first choice.

---

## Step 4: User Confirmation

Ask the user to confirm the direction. Do not proceed to Phase 3 until they do.

If the user pushes back or asks for changes:
- Minor adjustment (e.g., a constraint on the chosen approach): update the recommendation inline and confirm again
- Different option preferred: acknowledge, re-run adversarial test on that option, present result
- New option not yet proposed: explore it, assess it against the analysis, apply adversarial test, present

---

## Phase Boundary

Phase 2 is complete when the user has confirmed an architectural direction.

Update COMPASS.md:
- Fill in **Architecture direction confirmed** with one sentence: which option was chosen and why
- Add links to all three analysis documents in the Analysis section

Then proceed to Phase 3.
