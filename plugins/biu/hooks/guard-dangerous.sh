#!/usr/bin/env bash
# biu/hooks/guard-dangerous.sh
# PreToolUse hook: blocks destructive Bash commands.
# Exit 0 allows, exit 2 + stderr blocks the tool call.

set -u

# Read PreToolUse JSON from stdin; extract tool_input.command.
PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
  # Without python, we cannot safely parse the JSON payload. Fail open.
  exit 0
fi
CMD=$("$PY" -c '
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get("tool_input", {}).get("command", ""))
except Exception:
    print("")
' 2>/dev/null)

# If no command, nothing to guard.
[ -z "$CMD" ] && exit 0

block() {
  echo "[biu guard] Blocked: $1" >&2
  echo "[biu guard] If this is intentional, run the command manually in your shell." >&2
  exit 2
}

# --- Rule 1: rm -rf sensitive targets without a clear sub-path ---
# Matches rm with any combination of -r/-f flags targeting top-level sensitive dirs.
if echo "$CMD" | grep -Eq '(^|[[:space:]])rm[[:space:]]+([^|&;]*-[rRfF]+[fFrR]*|[^|&;]*-[rR][[:space:]]+-[fF]|[^|&;]*-[fF][[:space:]]+-[rR])'; then
  # Extract the tail after `rm ...flags...` and check targets.
  # Keep it simple: look for suspicious tokens anywhere in the command.
  if echo "$CMD" | grep -Eq '(^|[[:space:]/"\x27])(/|\$HOME|~|\.git|node_modules|\.spec)([[:space:]"\x27]|$|/[[:space:]"\x27]|/$)'; then
    block "rm -rf targeting a sensitive top-level path (/, \$HOME, ~, .git, node_modules, .spec) without a concrete sub-path. Specify a deeper path (e.g. '.spec/archived/2026-04-17-01/') if you really need to clean it."
  fi
fi

# --- Rule 2: bare `git reset --hard` with no ref ---
# `git reset --hard` alone discards the working tree; require an explicit ref.
if echo "$CMD" | grep -Eq '(^|[[:space:]])git[[:space:]]+reset[[:space:]]+--hard([[:space:]]*$|[[:space:]]*(\||&|;|$))'; then
  block "'git reset --hard' without a ref will discard uncommitted work. Specify a ref explicitly (e.g. 'git reset --hard HEAD~1' or 'git reset --hard origin/main')."
fi

# --- Rule 3: git push --force / -f to protected branch (main or master) ---
# Protected when the refspec targets main or master.
if echo "$CMD" | grep -Eq '(^|[[:space:]])git[[:space:]]+push[[:space:]].*(-f([[:space:]]|$)|--force([[:space:]]|$|=))'; then
  # Look for refs like `origin main`, `origin master`, `origin HEAD:main`, or `:main`.
  if echo "$CMD" | grep -Eq '([[:space:]]|:)(main|master)([[:space:]]|$)'; then
    block "'git push --force' to a protected branch (main/master). Force-push to a feature branch instead, or coordinate with the team before rewriting protected history."
  fi
fi

exit 0
