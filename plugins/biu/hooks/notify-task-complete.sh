#!/usr/bin/env bash
# biu/hooks/notify-task-complete.sh
#
# PostToolUse hook: when Edit/Write touches a .biu/tasks/task-*.md and that
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

# Confirm the file lives under .biu/tasks/. Any task-*.md elsewhere in the
# project (user notes, test fixtures, third-party templates) must not trigger
# the STOP reminder. Accept both forward-slash and backslash separators to
# tolerate raw Windows paths (in addition to Git-Bash-normalized ones).
case "$file_path" in
  *'.biu/tasks/task-'*'.md'|*'.biu\tasks\task-'*'.md') ;;
  *) exit 0 ;;
esac

# Only fire when the file currently shows Status: COMPLETE.
if ! grep -qE '^\*\*Status\*\*:[[:space:]]*COMPLETE' "$file_path" 2>/dev/null; then
  exit 0
fi

# Static reminder — no dynamic interpolation, no JSON-escaping landmines.
# Newlines inside additionalContext are emitted as literal backslash-n so the
# wire format stays strict JSON; Claude Code's JSON parser unescapes them to
# real newlines at display time.
cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"<biu-task-completed>\nA task file was just marked Status: COMPLETE.\n\nFirst, finish this turn's bookkeeping: flip the COMPASS Task Overview symbol from [~] to [x] (or [!]/[-] as appropriate), append any noteworthy decision to the Decision Log, and inform the user which Task was completed.\n\nThen STOP this turn. Do NOT begin the next Task automatically. Per Behavioral Rule #2 in spec-coding SKILL.md, wait for explicit user instruction (e.g. 'continue with Task N+1') before starting any new work.\n</biu-task-completed>"}}
EOF

exit 0
