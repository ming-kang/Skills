#!/usr/bin/env bash
# biu/hooks/inject-analyzer-context.sh
#
# SubagentStart hook for matcher=analyzer.
# Injects <biu-task-context> into the analyzer subagent's context so it
# knows the current cycle state, which templates to follow, and which
# files it must produce.

set -u

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
SPEC_DIR="$PROJECT_DIR/.spec"
TEMPLATE_PATH="${CLAUDE_PLUGIN_ROOT}/skills/spec-coding/references/templates/analysis.md"

PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
  exit 0
fi

# Compute state on-demand; stdout contains the JSON (may be empty if .spec/ missing).
STATE_TXT=$(bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/compute-state.sh" 2>/dev/null)

BIU_STATE_TEXT="$STATE_TXT" \
BIU_TEMPLATE_PATH="$TEMPLATE_PATH" \
BIU_SPEC_DIR="$SPEC_DIR" \
"$PY" - <<'PYEOF'
import json, os

spec_dir = os.environ.get("BIU_SPEC_DIR", "")
state_txt = os.environ.get("BIU_STATE_TEXT", "").strip()

lines = [
    "<biu-task-context role=\"analyzer\">",
    "",
    "You are running as the `analyzer` subagent in the Biu spec-coding workflow (Phase 1).",
    "",
    "## Required outputs",
    f"Write the following three files under `{spec_dir}/analysis/`:",
    "- `project-overview.md` — must contain a `## Technology Stack` heading",
    "- `module-inventory.md` — must contain at least one `## <module-path>` module entry",
    "- `risk-assessment.md` — must contain a `## Critical Risks` or `## High Risks` heading",
    "",
    f"## Template to follow",
    f"Read `{os.environ.get('BIU_TEMPLATE_PATH', '')}` for the exact section structure expected in each file.",
    "",
    "## Completion gate",
    "A `SubagentStop` hook verifies that all three files exist, are non-empty, and contain the required headings.",
    "If any file is missing or incomplete, the hook will block your stop and feed back the list of missing artifacts.",
    "Produce all three files before concluding.",
]
if state_txt:
    lines += [
        "",
        "## Current cycle state",
        "```json",
        state_txt,
        "```",
    ]
lines += ["</biu-task-context>"]

out = {
    "hookSpecificOutput": {
        "hookEventName": "SubagentStart",
        "additionalContext": "\n".join(lines),
    }
}
print(json.dumps(out, ensure_ascii=False))
PYEOF
