#!/usr/bin/env bash
# biu/hooks/lib/compute-state.sh
#
# Scans .spec/ and parses COMPASS.md to compute the current cycle state as
# JSON, emitted to stdout. The result is never written to disk; callers
# capture stdout directly.
#
# Silent exit 0 if .spec/ does not exist (biu not initialized in this project).
#
# Env: CLAUDE_PROJECT_DIR (preferred). Falls back to $PWD.

set -u

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
SPEC_DIR="$PROJECT_DIR/.spec"
COMPASS="$SPEC_DIR/COMPASS.md"
ANALYSIS_DIR="$SPEC_DIR/analysis"
TASKS_DIR="$SPEC_DIR/tasks"
GITIGNORE="$PROJECT_DIR/.gitignore"

if [ ! -d "$SPEC_DIR" ]; then
  # biu not initialized — nothing to compute.
  exit 0
fi

PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
  exit 0
fi

"$PY" - "$SPEC_DIR" "$COMPASS" "$ANALYSIS_DIR" "$TASKS_DIR" "$GITIGNORE" <<'PYEOF'
import json, os, re, sys
from datetime import datetime, timezone

spec_dir, compass_path, analysis_dir, tasks_dir, gitignore_path = sys.argv[1:6]

def read(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return None

# --- gitignore check ---
gi = read(gitignore_path) or ""
gitignore_ok = any(
    line.strip().rstrip('/') in ('.spec', '/.spec')
    for line in gi.splitlines()
)

# --- analysis completeness ---
required_analysis = ['project-overview.md', 'module-inventory.md', 'risk-assessment.md']
analysis_complete = all(
    os.path.isfile(os.path.join(analysis_dir, n)) and os.path.getsize(os.path.join(analysis_dir, n)) > 0
    for n in required_analysis
)

# --- COMPASS parsing ---
compass = read(compass_path)
compass_exists = compass is not None

current_status = ""
task_overview_filled = False
if compass_exists:
    m = re.search(r'^##\s+Current Status\s*\n(.+?)(?=^##\s|\Z)', compass, re.M | re.S)
    if m:
        current_status = m.group(1).strip()
    m = re.search(r'^##\s+Task Overview\s*\n(.+?)(?=^##\s|\Z)', compass, re.M | re.S)
    if m:
        body = m.group(1).strip()
        task_overview_filled = bool(body) and '<Populated by Phase 3>' not in body

# --- task inventory ---
task_counts = {'pending': 0, 'in_progress': 0, 'blocked': 0, 'complete': 0, 'skipped': 0}
active_task = None
if os.path.isdir(tasks_dir):
    task_files = sorted(
        f for f in os.listdir(tasks_dir)
        if f.startswith('task-') and f.endswith('.md')
    )
    for fn in task_files:
        body = read(os.path.join(tasks_dir, fn)) or ""
        m = re.search(r'^\*\*Status\*\*:\s*([A-Z_]+)', body, re.M)
        if not m:
            continue
        status = m.group(1).upper()
        if status == 'PENDING':
            task_counts['pending'] += 1
        elif status == 'IN_PROGRESS':
            task_counts['in_progress'] += 1
            if active_task is None:
                active_task = fn
        elif status == 'BLOCKED':
            task_counts['blocked'] += 1
        elif status == 'COMPLETE':
            task_counts['complete'] += 1
        elif status == 'SKIPPED':
            task_counts['skipped'] += 1
else:
    task_files = []

total_tasks = sum(task_counts.values())
resolved_tasks = task_counts['complete'] + task_counts['skipped']

# --- phase inference ---
# 0 Not Started | 1 Analysis | 2 Plan Refinement | 3 Task Decomposition
# 4 Implementation | 5 Ready to Archive
phase = 0
phase_label = "Not Started"

if not compass_exists:
    phase, phase_label = 1, "Analysis"
elif not analysis_complete:
    phase, phase_label = 1, "Analysis"
elif not task_overview_filled:
    phase, phase_label = 2, "Plan Refinement"
elif total_tasks == 0:
    phase, phase_label = 3, "Task Decomposition (in progress)"
elif total_tasks > 0 and resolved_tasks == total_tasks:
    phase, phase_label = 5, "Ready to Archive"
elif task_counts['in_progress'] > 0 or resolved_tasks > 0 or task_counts['blocked'] > 0:
    phase, phase_label = 4, "Implementation"
else:
    # All tasks PENDING and Task Overview filled → architect finished,
    # awaiting Hand-off confirmation from user.
    phase, phase_label = 3, "Task Decomposition (complete)"

state = {
    "cycle_exists": compass_exists,
    "gitignore_ok": gitignore_ok,
    "phase": phase,
    "phase_label": phase_label,
    "current_status": current_status,
    "analysis_complete": analysis_complete,
    "implementation_ready": phase >= 4,
    "tasks": {
        "count": total_tasks,
        "active": active_task,
        "pending": task_counts['pending'],
        "in_progress": task_counts['in_progress'],
        "blocked": task_counts['blocked'],
        "complete": task_counts['complete'],
        "skipped": task_counts['skipped'],
    },
    "updated_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
}

print(json.dumps(state, ensure_ascii=False))
PYEOF
