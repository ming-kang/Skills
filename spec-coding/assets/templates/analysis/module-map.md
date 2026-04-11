# Module Map

<!-- Long-lived map of the significant modules or architectural areas. -->

---

<!-- Repeat the entry below for each significant module, package, directory, or architectural area.
     Skip truly trivial files. Pick the granularity that will still be useful in later planning cycles. -->

## `<module-name>`

**Path**: `<relative/path>`
**Responsibility**: <!-- One sentence: what this area does -->
**Public API surface**: <!-- What it exposes to the rest of the codebase -->

**Internal dependencies**:
- `<other-module>` — why it depends on it

**External dependencies**:
- `<library>` — what it uses it for

**Size**: <!-- small / medium / large / very large -->
**Complexity rating**: <!-- low / medium / high / very high -->
**Complexity notes**: <!-- What would make future changes here hard -->

---

<!-- (repeat above block for each module) -->

---

## Dependency Summary

<!-- Summarize the dependency shape.
     Which modules are central? Which are leaves? Any circular dependencies? -->
