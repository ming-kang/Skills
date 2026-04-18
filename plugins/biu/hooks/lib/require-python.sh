#!/usr/bin/env bash
# biu/hooks/lib/require-python.sh
#
# Sourced by every biu hook script to resolve a Python interpreter.
# On success: exports BIU_PY with the python command.
# On failure: emits a one-time stderr note and calls `exit 0` so the hook
# stays fail-open (biu's guarantees are void, but Claude Code keeps running).
#
# Requires: ${CLAUDE_PLUGIN_DATA} (created on-demand by Claude Code when
# first referenced). Falls back to a temp marker in /tmp if unavailable.

BIU_PY="$(command -v python3 || command -v python || true)"

if [ -n "$BIU_PY" ]; then
  export BIU_PY
  return 0 2>/dev/null || exit 0
fi

# Python missing — emit warning once per install.
_biu_data_dir="${CLAUDE_PLUGIN_DATA:-${TMPDIR:-/tmp}/biu}"
_biu_marker="$_biu_data_dir/.python-missing-warned"

if [ ! -f "$_biu_marker" ]; then
  mkdir -p "$_biu_data_dir" 2>/dev/null || true
  {
    echo "[biu] python3 (or python) not found on PATH."
    echo "[biu] Verification and state-injection hooks are disabled until Python 3 is installed."
  } >&2
  # Best-effort marker; if we can't write it, the warning just repeats.
  : > "$_biu_marker" 2>/dev/null || true
fi

exit 0
