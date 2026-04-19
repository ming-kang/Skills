#!/usr/bin/env bash
# biu/hooks/verify-architect.sh
#
# SubagentStop gate for matcher=architect.
# Pure bash; checks structural existence only (no wording/phase-string checks).
# Exit 2 + stderr blocks the subagent from stopping; Claude Code feeds the
# stderr back to the subagent so it can self-correct.

set -u

CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$0")")}"
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

# 2. Each task file: Status field present, Status value is one of the five
#    valid literals, at least one '## ' heading, required sections present,
#    and at least one subtask checkbox under '## Subtasks'.
for path in "${task_files[@]:-}"; do
  [ -z "$path" ] && continue
  fname=$(basename "$path")

  # 2a. Status field present.
  if ! grep -E -q $'^\*\*Status\*\*:\r?' "$path" 2>/dev/null; then
    missing+=("tasks/$fname is missing the '**Status**:' field")
  fi

  # 2b. Status value is one of the five valid literals. The value can be
  #     followed by whitespace (incl. \r on CRLF files), an HTML comment
  #     marker '<!--' (used by the template to preserve the enum's
  #     discoverability), or end-of-line.
  if ! grep -E -q '^\*\*Status\*\*:[[:space:]]*(PENDING|IN_PROGRESS|BLOCKED|SKIPPED|COMPLETE)([[:space:]]|<!--|$)' "$path" 2>/dev/null; then
    missing+=("tasks/$fname Status value is not one of PENDING|IN_PROGRESS|BLOCKED|SKIPPED|COMPLETE")
  fi

  # 2c. At least one '## ' section heading.
  if ! grep -E -q $'^## \r?' "$path" 2>/dev/null; then
    missing+=("tasks/$fname has no '## ' section heading")
  fi

  # 2d. Required sections: Goal, Dependencies, Subtasks, Acceptance Criteria.
  #     [[:space:]]*$ tolerates trailing whitespace incl. CR on CRLF files.
  for section in Goal Dependencies Subtasks "Acceptance Criteria"; do
    if ! grep -E -q "^## ${section}[[:space:]]*\$" "$path" 2>/dev/null; then
      missing+=("tasks/$fname is missing required section '## ${section}'")
    fi
  done

  # 2e. At least one subtask checkbox under '## Subtasks'. Extract the
  #     section body (from the heading to the next '## ') with awk, then
  #     grep for a checkbox line.
  if ! awk '
    /^## Subtasks[[:space:]]*$/ { flag=1; next }
    /^## / { flag=0 }
    flag
  ' "$path" 2>/dev/null | grep -E -q '^- \[[ xX]\]'; then
    missing+=("tasks/$fname has no subtask checkbox under '## Subtasks'")
  fi
done

# 3. COMPASS.md exists and Task Overview placeholder removed.
if [ ! -f "$COMPASS" ]; then
  missing+=("COMPASS.md is missing")
elif grep -q '<Populated by Phase 3>' "$COMPASS" 2>/dev/null; then
  missing+=("COMPASS.md still contains the '<Populated by Phase 3>' placeholder in Task Overview")
fi

# 4. Task-count parity between COMPASS Task Overview lines and tasks/ files.
#    Matches any valid status symbol: space, x, ~, !, -.
if [ -f "$COMPASS" ]; then
  compass_task_lines=$(grep -cE '^- \[[ x~!-]\] Task ' "$COMPASS" 2>/dev/null || true)
  task_file_count=${#task_files[@]}
  if [ "${compass_task_lines:-0}" -ne "$task_file_count" ]; then
    missing+=("COMPASS Task Overview has ${compass_task_lines:-0} task lines but .spec/tasks/ has ${task_file_count} task files — counts must agree")
  fi
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
