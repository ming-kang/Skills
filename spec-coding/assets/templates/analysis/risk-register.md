# Risk Register

<!-- Written by: spec-coding Phase 1 (Explore subagent) -->
<!-- Purpose: Technical risks, compatibility concerns, and complexity hotspots that could affect the plan -->

---

<!-- Risk entry format:
     - Severity: Critical / High / Medium / Low
     - Likelihood: Likely / Possible / Unlikely
     - Category: Complexity / Coupling / Missing tests / Platform-specific / External dependency / Compatibility / Other
-->

## Risk: `<short name>`

**Severity**: <!-- Critical / High / Medium / Low -->
**Likelihood**: <!-- Likely / Possible / Unlikely -->
**Category**: <!-- see categories above -->
**Location**: `<file path or module name>`

**Description**: <!-- What is the risk and why does it exist? -->

**Impact if realized**: <!-- What breaks or becomes hard if this risk materializes? -->

**Signals observed**: <!-- Concrete evidence from the code: missing tests, TODOs, fragile assumptions, etc. -->

---

<!-- (repeat above block for each risk) -->

---

## Hotspot Summary

<!-- Which 2-3 areas of the codebase are most likely to cause problems?
     Reference specific modules from module-map.md.
     This summary is used by Phase 2 to frame the architectural options. -->

## External Constraints

<!-- Things outside the codebase that constrain the approach:
     runtime environment, deployment targets, API compatibility requirements,
     third-party service limitations, regulatory requirements, etc. -->
