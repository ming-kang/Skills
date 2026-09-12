"""Batch validation and machine-readable reports; standard library only."""

import argparse
import glob
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from .validator import CheckResult, Validator


def targets(inputs):
    seen = set()
    for raw in inputs:
        matches = sorted(glob.glob(raw, recursive=True)) if glob.has_magic(raw) else [raw]
        if not matches:
            yield Path(raw), f"no paths match {raw!r}"
        for match in matches:
            path = Path(match)
            try:
                paths = (sorted((file for file in path.rglob("*")
                                 if file.is_file() and file.suffix.lower() == ".svg"))
                         if path.is_dir() else [path])
                if not paths:
                    yield path, "directory contains no SVG files"
                for file in paths:
                    identity = os.path.normcase(str(file.resolve()))
                    if identity not in seen:
                        seen.add(identity)
                        yield file, None
            except OSError as exc:
                yield path, str(exc)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate SVG files, directories, or quoted glob patterns.")
    parser.add_argument("paths", nargs="+", help="SVG files or directories (searched recursively)")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("-q", "--quiet", action="store_true", help="print only warnings and errors")
    output.add_argument("--json", action="store_true", help="write one JSON report to stdout")
    parser.add_argument("--strict", action="store_true", help="exit 1 for warnings as well as errors")
    parser.add_argument("--no-color", action="store_true", help="disable terminal colors")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")

    reports = []
    for path, discovery_error in targets(args.paths):
        validator = Validator(path, no_color=args.no_color or not sys.stdout.isatty())
        if discovery_error:
            results = [CheckResult("Finding SVG files", "fail", discovery_error)]
        else:
            try:
                results = validator.collect()
            except Exception as exc:
                results = [CheckResult("Checking document", "fail", f"{type(exc).__name__}: {exc}",
                                       fix="Inspect the input that could not be validated.")]
        failures = sum(result.status == "fail" for result in results)
        warnings = sum(result.status == "warn" for result in results)
        status = "fail" if failures else "warn" if warnings else "pass"
        reports.append({"path": str(path), "status": status, "failures": failures,
                        "warnings": warnings, "checks": [asdict(result) for result in results]})
        if not args.json:
            visible = [result for result in results if not args.quiet or result.status != "pass"]
            if visible:
                print(f"Validating SVG: {path}")
                for result in visible:
                    validator.report(result)
    summary = {"files": len(reports), "failures": sum(report["failures"] for report in reports),
               "warnings": sum(report["warnings"] for report in reports)}
    if args.json:
        print(json.dumps({"files": reports, "summary": summary, "strict": args.strict}, indent=2))
    elif not args.quiet:
        print(f'{summary["files"]} file(s), {summary["failures"]} error(s), {summary["warnings"]} warning(s)')
    return int(bool(summary["failures"] or (args.strict and summary["warnings"])))
