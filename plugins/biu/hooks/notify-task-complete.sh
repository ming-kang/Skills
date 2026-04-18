#!/usr/bin/env bash
# biu/hooks/notify-task-complete.sh
#
# PostToolUse hook: when Edit/Write touches a .spec/tasks/task-*.md and that
# file now has Status: COMPLETE, inject a reminder telling Claude to STOP
# this turn and not auto-advance to the next Task.
#
# Soft enforcement only — the model can technically ignore the injected
# reminder. It exists to amplify the Behavioral Rule in SKILL.md, not to
# replace it. User does not see this hook output.

set -u

input=$(cat)

# Quick filter: stdin must mention a task file path.
case "$input" in
  *task-*'.md'*) ;;
  *) exit 0 ;;
esac

# Extract file_path from the JSON (best-effort; no jq dependency).
file_path=$(printf '%s' "$input" \
  | grep -oE '"file_path"[[:space:]]*:[[:space:]]*"[^"]+"' \
  | head -1 \
  | sed -E 's/.*"file_path"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')

# Unescape JSON \\ → \ (Windows paths come through doubly-escaped).
file_path=${file_path//\\\\/\\}

[ -z "$file_path" ] && exit 0
[ ! -f "$file_path" ] && exit 0

# Confirm by basename it really is a task file.
case "$(basename "$file_path")" in
  task-*.md) ;;
  *) exit 0 ;;
esac

# Only fire when the file currently shows Status: COMPLETE.
if ! grep -qE '^\*\*Status\*\*:[[:space:]]*COMPLETE' "$file_path" 2>/dev/null; then
  exit 0
fi

# Static reminder — no dynamic interpolation, no JSON-escaping landmines.
cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"<biu-task-completed>
A task file was just marked Status: COMPLETE.

STOP this turn now. Do NOT begin the next Task automatically. Per Behavioral Rule #2 in spec-coding SKILL.md, you must inform the user that the Task is complete and wait for explicit instruction (e.g. 'continue with Task N+1') before starting any new work.
</biu-task-completed>"}}
EOF

exit 0
