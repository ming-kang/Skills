# Module Map

<!-- Written: spec-coding Phase 1 (Explore subagent) -->
<!-- Purpose: Every module in the project with responsibility, dependencies, and complexity -->

---

<!-- Repeat the entry below for every significant module or component.
     "Module" means a file, directory, package, or logical unit -- pick the right granularity for the project.
     Do not omit modules because they seem unimportant. Flag them as "trivial" if needed. -->

## `<module-name>`

**Path**: `<relative/path>`
**Responsibility**: <!-- One sentence: what this module does -->
**Public API surface**: <!-- What it exports / exposes to the rest of the codebase -->

**Internal dependencies**:
- `<other-module>` — why it depends on it

**External dependencies**:
- `<library>` — what it uses it for

**Size**: <!-- trivial / small / medium / large / very large -->
**Complexity rating**: <!-- low / medium / high / very high -->
**Complexity notes**: <!-- What makes it complex, if rating is high or above -->

---

<!-- (repeat above block for each module) -->

---

## Dependency Summary

<!-- A high-level description of the dependency structure.
     Which modules are the most-depended-on? Which are leaves?
     Any circular dependencies? -->
