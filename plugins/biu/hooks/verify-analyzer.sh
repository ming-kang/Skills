#!/usr/bin/env bash
# biu/hooks/verify-analyzer.sh
#
# SubagentStop gate for matcher=analyzer.
# Pure bash; checks structural existence only (no wording/heading-text checks).
# Exit 2 + stderr blocks the subagent from stopping; Claude Code feeds the
# stderr back to the subagent so it can self-correct.

set -u

CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$0")")}"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
ANALYSIS_DIR="$PROJECT_DIR/.spec/analysis"
TEMPLATE="${CLAUDE_PLUGIN_ROOT}/skills/spec-coding/references/templates/analysis.md"
MIN_BYTES=500
MIN_HEADINGS=3

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
    missing+=("analysis/$fname is too short (${bytes:-0} bytes, minimum ${MIN_BYTES})")
    continue
  fi
  headings=$(grep -E -c $'^## \r?' "$path" 2>/dev/null || true)
  if [ "$headings" -lt "$MIN_HEADINGS" ]; then
    missing+=("analysis/$fname has insufficient structure ($headings headings, minimum ${MIN_HEADINGS})")
  fi
done

# Per-file required section names (beyond the generic 3-heading minimum):
#   - project-overview.md must have '## Summary' AND '## Architecture'
#   - module-inventory.md must have at least one '## `<module-path>`' entry
#   - risk-assessment.md must have at least one severity-tier heading
po="$ANALYSIS_DIR/project-overview.md"
if [ -f "$po" ]; then
  for required in Summary Architecture; do
    if ! grep -E -q "^## ${required}[[:space:]]*\$" "$po" 2>/dev/null; then
      missing+=("analysis/project-overview.md is missing required section '## ${required}'")
    fi
  done
fi

mi="$ANALYSIS_DIR/module-inventory.md"
if [ -f "$mi" ]; then
  if ! grep -E -q $'^## `' "$mi" 2>/dev/null; then
    missing+=("analysis/module-inventory.md has no '## \`<module-path>\`' module entry")
  fi
fi

ra="$ANALYSIS_DIR/risk-assessment.md"
if [ -f "$ra" ]; then
  if ! grep -E -q '^## (Critical|High|Medium|Low) Risks[[:space:]]*$' "$ra" 2>/dev/null; then
    missing+=("analysis/risk-assessment.md has no '## <Severity> Risks' heading")
  fi
fi

if [ ${#missing[@]} -gt 0 ]; then
  {
    echo "[biu verify-analyzer] Analyzer outputs incomplete; cannot hand off yet:"
    for m in "${missing[@]}"; do echo "  - $m"; done
    echo "See template for the expected structure: $TEMPLATE"
  } >&2
  exit 2
fi

exit 0
