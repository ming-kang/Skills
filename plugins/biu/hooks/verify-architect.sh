#!/usr/bin/env bash
# biu/hooks/verify-architect.sh
#
# SubagentStop gate for matcher=architect.
# Exit 2 + stderr blocks the subagent from stopping and feeds back the list of
# missing items so the subagent keeps working.

set -u

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
SPEC_DIR="$PROJECT_DIR/.spec"
COMPASS="$SPEC_DIR/COMPASS.md"
TASKS_DIR="$SPEC_DIR/tasks"

cat >/dev/null 2>&1

PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
  exit 0
fi

BIU_COMPASS="$COMPASS" BIU_TASKS_DIR="$TASKS_DIR" "$PY" - <<'PYEOF'
import os, re, sys

compass_path = os.environ["BIU_COMPASS"]
tasks_dir = os.environ["BIU_TASKS_DIR"]

missing = []

# 1. Tasks directory has at least one task-*.md
if not os.path.isdir(tasks_dir):
    missing.append("tasks/ directory is missing")
    task_files = []
else:
    task_files = sorted(
        f for f in os.listdir(tasks_dir)
        if f.startswith("task-") and f.endswith(".md")
    )
    if not task_files:
        missing.append("tasks/ is empty; at least one task-N-<name>.md is required")

# 2. Each task file has the four core sections
required_sections = ["**Status**:", "## Goal", "## Subtasks", "## Acceptance Criteria"]
for fn in task_files:
    path = os.path.join(tasks_dir, fn)
    try:
        body = open(path, "r", encoding="utf-8").read()
    except Exception as e:
        missing.append(f"tasks/{fn} unreadable ({e})")
        continue
    absent = [s for s in required_sections if s not in body]
    if absent:
        missing.append(f"tasks/{fn} is missing section(s): {', '.join(absent)}")

# 3. COMPASS.md Task Overview filled, Current Status at Hand-off
try:
    compass = open(compass_path, "r", encoding="utf-8").read()
except Exception:
    missing.append("COMPASS.md is missing or unreadable")
    compass = ""

m = re.search(r'^##\s+Task Overview\s*\n(.+?)(?=^##\s|\Z)', compass, re.M | re.S)
if not m:
    missing.append("COMPASS.md has no '## Task Overview' section")
else:
    body = m.group(1).strip()
    if not body:
        missing.append("COMPASS.md '## Task Overview' is empty")
    elif "<Populated by Phase 3>" in body:
        missing.append("COMPASS.md '## Task Overview' still contains the '<Populated by Phase 3>' placeholder")

m = re.search(r'^##\s+Current Status\s*\n(.+?)(?=^##\s|\Z)', compass, re.M | re.S)
if not m or "Phase 3" not in m.group(1) or "Hand-off" not in m.group(1):
    missing.append(
        "COMPASS.md '## Current Status' must mention 'Phase 3' and 'Hand-off' "
        "(e.g. 'Phase 3 complete. Ready for Hand-off.')"
    )

if missing:
    sys.stderr.write(
        "[biu verify-architect] Architect produced incomplete outputs; cannot hand off yet:\n"
    )
    for m in missing:
        sys.stderr.write(f"  - {m}\n")
    sys.stderr.write(
        "Please resolve the items above (see task.md template and the COMPASS update contract) before stopping.\n"
    )
    sys.exit(2)

sys.exit(0)
PYEOF
