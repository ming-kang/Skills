#!/usr/bin/env bash
# biu/hooks/inject-architect-context.sh
#
# SubagentStart hook for matcher=architect.
# Injects <biu-task-context> into the architect subagent's context so it has
# the confirmed plan, analysis summaries, the task template path, and the
# COMPASS update contract.

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
SPEC_DIR="$PROJECT_DIR/.spec"
COMPASS="$SPEC_DIR/COMPASS.md"
ANALYSIS_DIR="$SPEC_DIR/analysis"
TEMPLATE_PATH="${CLAUDE_PLUGIN_ROOT}/skills/spec-coding/references/templates/task.md"

# shellcheck source=lib/require-python.sh
. "${CLAUDE_PLUGIN_ROOT}/hooks/lib/require-python.sh"

BIU_COMPASS="$COMPASS" \
BIU_ANALYSIS_DIR="$ANALYSIS_DIR" \
BIU_TEMPLATE_PATH="$TEMPLATE_PATH" \
BIU_SPEC_DIR="$SPEC_DIR" \
"$BIU_PY" - <<'PYEOF'
import json, os

def read_head(p, max_chars=1200):
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = f.read()
    except Exception:
        return None
    if len(data) > max_chars:
        return data[:max_chars] + "\n...[truncated]"
    return data

spec_dir = os.environ.get("BIU_SPEC_DIR", "")
compass_path = os.environ.get("BIU_COMPASS", "")
analysis_dir = os.environ.get("BIU_ANALYSIS_DIR", "")
template_path = os.environ.get("BIU_TEMPLATE_PATH", "")

lines = [
    "<biu-task-context role=\"architect\">",
    "",
    "You are running as the `architect` subagent in the Biu spec-coding workflow (Phase 3).",
    "",
    "## Required outputs",
    f"- Create one file per Task under `{spec_dir}/tasks/` named `task-N-<short-name>.md`.",
    "  Each file MUST contain: `**Status**:`, `## Goal`, `## Subtasks`, `## Acceptance Criteria`.",
    f"- Update `{compass_path}`:",
    "  - Replace the `## Task Overview` placeholder with the real task list (one line per task).",
    "  - Update `## Current Status` to include `Phase 3 complete. Ready for Hand-off.` (or equivalent wording containing `Phase 3` and `Hand-off`).",
    "",
    f"## Template to follow",
    f"Read `{template_path}` for the exact task-file structure.",
]

compass_body = read_head(compass_path, 3000)
if compass_body:
    lines += [
        "",
        "## Current COMPASS.md",
        "```markdown",
        compass_body.rstrip(),
        "```",
    ]

lines += ["", "## Analysis summaries"]
for name in ("project-overview.md", "module-inventory.md", "risk-assessment.md"):
    path = os.path.join(analysis_dir, name)
    head = read_head(path, 800)
    if head:
        lines += [f"### {name}", "```markdown", head.rstrip(), "```", ""]

lines += [
    "## Completion gate",
    "A `SubagentStop` hook verifies that task files exist with the four core sections, and that COMPASS.md's Task Overview and Current Status are updated accordingly.",
    "If any requirement is missing, the hook will block your stop and feed back the list of missing items.",
    "</biu-task-context>",
]

out = {
    "hookSpecificOutput": {
        "hookEventName": "SubagentStart",
        "additionalContext": "\n".join(lines),
    }
}
print(json.dumps(out, ensure_ascii=False))
PYEOF
