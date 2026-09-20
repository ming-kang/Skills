#!/usr/bin/env python3
"""Clean up leftover local processes started by the pptd skill.

The skill starts two kinds of background helper:

* the local editor host (`node scripts/serve.mjs`), which registers a lease file
  in ``<tempdir>/pptd-serve/`` and normally exits on idle or ``--stop``;
* the Windows debug browser used by the browser export / image-QA paths, which
  registers itself in ``<tempdir>/pptd-cdp.json`` and is reclaimed automatically
  after an idle period.

This command reclaims both by hand. It only ever touches processes the skill
itself started (a leased pid whose image name matches, or a registered debug
browser with the skill's own profile directory); a browser you pointed the skill
at through ``AGENT_BROWSER_CDP`` is never registered, so it is never killed.

Usage:
  python3 scripts/clean_processes.py            # report and clean
  python3 scripts/clean_processes.py --dry-run  # report only
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Reuse the registry helpers so both entry points agree on what "ours" means.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from export_pptx import (  # noqa: E402  (path set up above)
    CDP_REGISTRY_PATH,
    debug_chrome_is_ours,
    kill_debug_chrome,
    log,
    read_cdp_registry,
    write_cdp_registry,
)

SERVE_LEASE_DIRECTORY = Path(
    os.environ.get("TEMP") or os.environ.get("TMP") or tempfile.gettempdir()
) / "pptd-serve"


def process_alive(pid: Optional[int]) -> bool:
    if not pid or pid <= 0:
        return False
    if sys.platform == "win32":
        probe = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        # CSV rows look like "node.exe","1234","Console","1","12,345 K"; the
        # "no tasks match" notice has a single field, so guard on length. Match
        # the pid column only: a bare substring check also hits memory values.
        for row in probe.stdout.splitlines():
            fields = [part.strip('"') for part in row.strip().split('","')]
            if len(fields) >= 2 and fields[1] == str(pid):
                return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def kill_pid(pid: int) -> bool:
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/pid", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    else:
        try:
            os.kill(pid, 15)
        except OSError:
            return False
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if not process_alive(pid):
            return True
        time.sleep(0.3)
    return False


def editor_leases() -> List[Dict[str, Any]]:
    if not SERVE_LEASE_DIRECTORY.is_dir():
        return []
    leases = []
    for path in sorted(SERVE_LEASE_DIRECTORY.glob("*.json")):
        try:
            lease = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(lease, dict):
            leases.append({"file": path, "lease": lease})
    return leases


def clean(dry_run: bool) -> Dict[str, Any]:
    report: Dict[str, Any] = {"event": "clean", "dryRun": dry_run, "hosts": [], "browsers": []}

    for item in editor_leases():
        lease = item["lease"]
        pid = lease.get("pid")
        alive = process_alive(pid)
        entry = {
            "pid": pid,
            "url": lease.get("url"),
            "project": lease.get("projectRoot"),
            "leaseFile": str(item["file"]),
            "wasRunning": alive,
        }
        if alive and not dry_run:
            entry["stopped"] = kill_pid(pid)
            alive = process_alive(pid)
        if not alive:
            # Gone (killed now or already dead): drop the lease so --status
            # stops reporting it.
            if not dry_run:
                try:
                    item["file"].unlink()
                except OSError:
                    pass
            entry["leaseRemoved"] = not dry_run
        report["hosts"].append(entry)

    entries = read_cdp_registry()
    kept = []
    for entry in entries:
        ours = debug_chrome_is_ours(entry)
        item = {
            "port": entry.get("port"),
            "pid": entry.get("pid"),
            "ours": ours,
            "registry": str(CDP_REGISTRY_PATH),
        }
        stopped = False
        if ours and not dry_run:
            stopped = kill_debug_chrome(entry)
            item["stopped"] = stopped
        if not stopped:
            # Not ours, not running, or the kill failed: keep the registration.
            kept.append(entry)
        report["browsers"].append(item)
    if kept != entries and not dry_run:
        write_cdp_registry(kept)

    return report


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be cleaned without touching anything",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    report = clean(args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["hosts"] and not report["browsers"]:
        log("nothing to clean: no editor host or debug browser is registered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
