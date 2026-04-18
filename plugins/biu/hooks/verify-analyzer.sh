#!/usr/bin/env bash
# biu/hooks/verify-analyzer.sh
#
# SubagentStop gate for matcher=analyzer.
# Pure bash; checks structural existence only (no wording/heading-text checks).
# Exit 2 + stderr blocks the subagent from stopping; Claude Code feeds the
# stderr back to the subagent so it can self-correct.

set -u

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
ANALYSIS_DIR="$PROJECT_DIR/.spec/analysis"
TEMPLATE="${CLAUDE_PLUGIN_ROOT}/skills/spec-coding/references/templates/analysis.md"
MIN_BYTES=200

# Drain stdin (hook input JSON, unused).
cat >/dev/null 2>&1 || true

missing=()

for fname in project-overview.md module-inventory.md risk-assessment.md; do
  path="$ANALYSIS_DIR/$fname"
  if [ ! -f "$path" ]; then
    missing+=("analysis/$fname is missing")
    continue
  fi
  bytes=$(wc -c <"$path" 2>/dev/null | tr -d ' \t\r\n')
  if [ -z "$bytes" ] || [ "$bytes" -lt "$MIN_BYTES" ]; then
    missing+=("analysis/$fname is empty or too short (need >= ${MIN_BYTES} bytes, got ${bytes:-0})")
    continue
  fi
  if ! grep -q '^## ' "$path" 2>/dev/null; then
    missing+=("analysis/$fname has no '## ' section heading")
  fi
done

if [ ${#missing[@]} -gt 0 ]; then
  {
    echo "[biu verify-analyzer] Analyzer outputs incomplete; cannot hand off yet:"
    for m in "${missing[@]}"; do echo "  - $m"; done
    echo "See template for the expected structure: $TEMPLATE"
  } >&2
  exit 2
fi

exit 0
