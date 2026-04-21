# Plan Template

This template defines the canonical structure of `.biu/plan.md`. It is the **single source of truth** for the confirmed task scope, constraints, and analysis entry points for a spec-coding cycle.

Every file that reads or writes plan.md (SKILL.md Phase 2, agents/architect.md, references/implementation.md) should reference this template instead of restating the structure inline.

---

## Template

```markdown
# Plan

## Task Definition

<One paragraph: what is being built or transformed, confirmed with the user in Phase 2.>

## Assumptions & Constraints

<Non-negotiable boundaries locked in during Phase 2.>

## Analysis

- [project-overview.md](./analysis/project-overview.md)
- [module-inventory.md](./analysis/module-inventory.md)
- [risk-assessment.md](./analysis/risk-assessment.md)
```

---

## Section semantics

| Section | Written by | Mutation pattern |
|---|---|---|
| `## Task Definition` | Phase 2 (main agent) | Written once; only changed if scope fundamentally shifts |
| `## Assumptions & Constraints` | Phase 2 (main agent) | Written once; only changed via explicit user decision |
| `## Analysis` | Phase 2 (main agent) | Links; may gain `*(Updated YYYY-MM-DD)*` annotation if analysis docs are revised mid-cycle |
