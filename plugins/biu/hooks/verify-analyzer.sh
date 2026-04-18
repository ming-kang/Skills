#!/usr/bin/env bash
# biu/hooks/verify-analyzer.sh
#
# SubagentStop gate for matcher=analyzer.
# Exit 2 + stderr blocks the subagent from stopping and feeds back the list of
# missing artifacts so the subagent keeps working.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
ANALYSIS_DIR="$PROJECT_DIR/.spec/analysis"

# Consume and ignore stdin (hook input JSON).
cat >/dev/null 2>&1 || true

# shellcheck source=lib/require-python.sh
. "${CLAUDE_PLUGIN_ROOT}/hooks/lib/require-python.sh"

BIU_ANALYSIS_DIR="$ANALYSIS_DIR" "$BIU_PY" - <<'PYEOF'
import os, sys

d = os.environ["BIU_ANALYSIS_DIR"]

checks = [
    ("project-overview.md", ["## Technology Stack"], 100),
    ("module-inventory.md", None,                    60),   # at least one "## " entry
    ("risk-assessment.md", ["## Critical Risks", "## High Risks"], 60),
]

missing = []
for fname, headings, min_size in checks:
    path = os.path.join(d, fname)
    if not os.path.isfile(path):
        missing.append(f"analysis/{fname} is missing")
        continue
    try:
        with open(path, "r", encoding="utf-8") as f:
            body = f.read()
    except Exception as e:
        missing.append(f"analysis/{fname} unreadable ({e})")
        continue
    if len(body.strip()) < min_size:
        missing.append(f"analysis/{fname} is empty or too short (need >= {min_size} chars)")
        continue
    if fname == "module-inventory.md":
        # require at least one module header (## <something>)
        import re
        if not re.search(r"(?m)^##\s+\S", body):
            missing.append("analysis/module-inventory.md has no '## <module>' entries")
    elif headings:
        if not any(h in body for h in headings):
            missing.append(
                f"analysis/{fname} is missing required heading: one of {headings}"
            )

if missing:
    sys.stderr.write(
        "[biu verify-analyzer] Analyzer produced incomplete outputs; cannot hand off yet:\n"
    )
    for m in missing:
        sys.stderr.write(f"  - {m}\n")
    sys.stderr.write(
        "Please produce the missing artifacts (see the analysis.md template) before stopping.\n"
    )
    sys.exit(2)

sys.exit(0)
PYEOF
