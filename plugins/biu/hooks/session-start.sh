#!/usr/bin/env bash
# biu/hooks/session-start.sh
#
# SessionStart hook: compute biu cycle state on-demand and inject
# <biu-session-state> into Claude's context via hookSpecificOutput.additionalContext.
#
# Silent no-op when .spec/ does not exist (project not using biu).

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
SPEC_DIR="$PROJECT_DIR/.spec"

if [ ! -d "$SPEC_DIR" ]; then
  exit 0
fi

# shellcheck source=lib/require-python.sh
. "${CLAUDE_PLUGIN_ROOT}/hooks/lib/require-python.sh"

# Compute state on-demand; compute-state.sh prints the JSON to stdout on success.
STATE_JSON="$(bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/compute-state.sh" 2>/dev/null || true)"

if [ -z "$STATE_JSON" ]; then
  # compute-state failed or spec/ missing — stay silent.
  exit 0
fi

# Render state into <biu-session-state> block via python.
# Pass JSON via env var to avoid any shell interpolation pitfalls.
BIU_STATE="$STATE_JSON" "$BIU_PY" - <<'PYEOF'
import json, os, sys

state = json.loads(os.environ["BIU_STATE"])

tasks = state.get("tasks", {})
lines = ["<biu-session-state>"]
lines.append(f"- Cycle: {'active' if state.get('cycle_exists') else 'not started'}")
lines.append(f"- Phase: {state.get('phase', 0)} / {state.get('phase_label', '')}")
lines.append(f"- Gitignore ok: {str(state.get('gitignore_ok', False)).lower()}")
lines.append(f"- Analysis: {'complete' if state.get('analysis_complete') else 'incomplete'}")
lines.append(
    "- Tasks: {n} total ({ip} active, {c} complete, {p} pending, {b} blocked, {s} skipped)".format(
        n=tasks.get("count", 0),
        ip=tasks.get("in_progress", 0),
        c=tasks.get("complete", 0),
        p=tasks.get("pending", 0),
        b=tasks.get("blocked", 0),
        s=tasks.get("skipped", 0),
    )
)
if tasks.get("active"):
    lines.append(f"- Active task: {tasks['active']}")
cs = (state.get("current_status") or "").strip().replace("\n", " ")
if cs:
    lines.append(f"- Current Status: {cs}")
lines.append("- Note: trust this block; skip the COMPASS existence probe in Continuity Check.")
lines.append("</biu-session-state>")

out = {
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "\n".join(lines),
    }
}
print(json.dumps(out, ensure_ascii=False))
PYEOF
