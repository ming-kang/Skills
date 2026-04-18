#!/usr/bin/env bash
# biu/hooks/verify-architect.sh
#
# SubagentStop gate for matcher=architect.
# Pure bash; checks structural existence only (no wording/phase-string checks).
# Exit 2 + stderr blocks the subagent from stopping; Claude Code feeds the
# stderr back to the subagent so it can self-correct.

set -u

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
SPEC_DIR="$PROJECT_DIR/.spec"
COMPASS="$SPEC_DIR/COMPASS.md"
TASKS_DIR="$SPEC_DIR/tasks"
TEMPLATE="${CLAUDE_PLUGIN_ROOT}/skills/spec-coding/references/templates/task.md"

cat >/dev/null 2>&1 || true

missing=()

# 1. tasks/ exists and contains at least one task-*.md
if [ ! -d "$TASKS_DIR" ]; then
  missing+=("tasks/ directory is missing")
  task_files=()
else
  # POSIX-friendly enumeration; nullglob via shopt isn't always available.
  task_files=()
  for f in "$TASKS_DIR"/task-*.md; do
    [ -e "$f" ] && task_files+=("$f")
  done
  if [ ${#task_files[@]} -eq 0 ]; then
    missing+=("tasks/ is empty; at least one task-N-<name>.md is required")
  fi
fi

# 2. Each task file has Status field and at least one '## ' heading
for path in "${task_files[@]:-}"; do
  [ -z "$path" ] && continue
  fname=$(basename "$path")
  if ! grep -q '^\*\*Status\*\*:' "$path" 2>/dev/null; then
    missing+=("tasks/$fname is missing the '**Status**:' field")
  fi
  if ! grep -q '^## ' "$path" 2>/dev/null; then
    missing+=("tasks/$fname has no '## ' section heading")
  fi
done

# 3. COMPASS.md exists and Task Overview placeholder removed
if [ ! -f "$COMPASS" ]; then
  missing+=("COMPASS.md is missing")
elif grep -q '<Populated by Phase 3>' "$COMPASS" 2>/dev/null; then
  missing+=("COMPASS.md still contains the '<Populated by Phase 3>' placeholder in Task Overview")
fi

if [ ${#missing[@]} -gt 0 ]; then
  {
    echo "[biu verify-architect] Architect outputs incomplete; cannot hand off yet:"
    for m in "${missing[@]}"; do echo "  - $m"; done
    echo "See template for the expected task-file structure: $TEMPLATE"
  } >&2
  exit 2
fi

exit 0
