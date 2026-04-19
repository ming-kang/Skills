# Analysis Document Templates

These templates define the structure for the three documents produced by the analyzer subagent in Phase 1. Each template corresponds to one file in `.spec/analysis/`.

---

## Template: project-overview.md

````markdown
# Project Overview

## Summary

<1–3 sentence description of the project: what it does, who uses it, and its current state.>

## Technology Stack

| Category        | Technology          | Version   | Notes                        |
|-----------------|---------------------|-----------|------------------------------|
| Language        |                     |           |                              |
| Framework       |                     |           |                              |
| Build Tool      |                     |           |                              |
| Test Framework  |                     |           |                              |
| Key Libraries   |                     |           |                              |

## Entry Points

| Purpose              | Command / Path                        |
|----------------------|---------------------------------------|
| Build                |                                       |
| Run                  |                                       |
| Test                 |                                       |
| Lint / Format        |                                       |

## Directory Layout

<Annotated tree of top-level directories with one-line descriptions of each.>

## Architecture

**Pattern**: <Architectural pattern>

**Data flow**: <Describe how data moves through the system from entry point to output or storage. 2–4 sentences.>

**Cross-cutting concerns**:
- Authentication: <how it's handled>
- Logging: <how it's handled>
- Error handling: <how it's handled>
- Configuration: <how it's handled>
````

---

## Template: module-inventory.md

```markdown
# Module Inventory

One entry per logical module, package, or significant component.

---

## `<module-path>`

**Responsibility**: <What this module does — inferred from code, not just the name.>

**Public Surface**:
- `<FunctionOrClass>` — <brief description>
- ...

**Internal Dependencies**: `<other-module-1>`, `<other-module-2>`

**External Dependencies**: `<package-1>`, `<package-2>`

**Size**: ~N files, ~N lines

**Complexity**: Low | Medium | High | Critical

**Notes**: <Anything unusual worth flagging.>

---

<!-- Repeat for each module -->
```

---

## Template: risk-assessment.md

```markdown
# Risk Assessment

Risks are ranked by severity: Critical → High → Medium → Low.

---

## Critical Risks

### <Risk Name>

**Location**: `<file or module path>`

**Description**: <What the risk is and why it matters.>

**Impact**: <What breaks or becomes harder if this isn't handled carefully.>

**Suggested Mitigation**: <Concrete approach to address this risk.>

---

## High Risks

<!-- Same structure as Critical -->

---

## Medium Risks

<!-- Same structure -->

---

## Low Risks

<!-- Same structure -->

---

## Transformation Constraints

Issues that are not risks per se, but constrain how the transformation must proceed:

- <Constraint 1>
- <Constraint 2>
- ...
```
