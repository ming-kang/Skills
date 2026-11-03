#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

from pptd_common import SKILL_DIR, ExportError, log, run_command
from pptd_deck import build_local_project, find_manifest
from pptd_pptx import patch_transitions, verify_output

LOCAL_EXPORTER = Path(__file__).resolve().parent / "export_pptd.mjs"
CANONICAL_WASM = SKILL_DIR / "assets" / "wasm" / "pptd_wasm_bg.wasm"


def ensure_node() -> str:
    node = shutil.which("node")
    if not node:
        raise ExportError("Node.js 18+ is required for WASM export")
    process = run_command([node, "--version"], timeout=10)
    match = re.search(r"v?(\d+)", process.stdout or "")
    if process.returncode != 0 or not match:
        raise ExportError("could not determine the Node.js version")
    if int(match.group(1)) < 18:
        raise ExportError(f"Node.js 18+ is required; found {process.stdout.strip()}")
    return node


def resolve_wasm(override: Path | None = None) -> Path:
    path = Path(override).expanduser().resolve() if override else CANONICAL_WASM
    if not path.is_file():
        raise ExportError(f"PPTD WASM writer not found: {path}")
    return path


def export_pptx(
    source: Path,
    output: Path,
    transition: str = "fade",
    force: bool = False,
    wasm: Path | None = None,
) -> dict[str, Any]:
    if transition not in {"fade", "none"}:
        raise ExportError("transition must be fade or none")
    if not LOCAL_EXPORTER.is_file():
        raise ExportError(f"Node exporter is missing: {LOCAL_EXPORTER}")
    node = ensure_node()
    wasm_path = resolve_wasm(wasm)
    manifest = find_manifest(source)
    output = Path(output).expanduser().resolve()
    if output.suffix.lower() != ".pptx":
        raise ExportError(f"output must have a .pptx extension: {output}")
    if output.exists() and not force:
        raise ExportError(f"output already exists (pass --force to replace it): {output}")

    project = build_local_project(manifest)
    for warning in project.get("warnings", []):
        log(f"warning: {warning}")
    output.parent.mkdir(parents=True, exist_ok=True)

    handle, raw_name = tempfile.mkstemp(
        prefix=f".{output.stem}-", suffix=".pptx", dir=output.parent
    )
    os.close(handle)
    raw_output = Path(raw_name)
    try:
        with tempfile.TemporaryDirectory(prefix="pptd-export-") as temp_dir:
            project_json = Path(temp_dir) / "project.json"
            project_json.write_text(
                json.dumps(project, ensure_ascii=False), encoding="utf-8"
            )
            process = run_command(
                [
                    node,
                    LOCAL_EXPORTER,
                    "--json",
                    project_json,
                    "--output",
                    raw_output,
                    "--wasm",
                    wasm_path,
                ],
                timeout=300,
            )
        if process.returncode != 0:
            raise ExportError(
                f"WASM export failed ({process.returncode}):\n{(process.stdout or '')[-4000:]}"
            )

        patched = patch_transitions(raw_output, transition)
        summary = verify_output(raw_output, transition)
        if output.exists() and not force:
            raise ExportError(f"output already exists (pass --force to replace it): {output}")
        raw_output.replace(output)
    finally:
        raw_output.unlink(missing_ok=True)

    summary.update(
        {
            "output": str(output),
            "exporter": "wasm",
            "transitionPatchedSlides": patched,
            "warnings": project.get("warnings", []),
        }
    )
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and export a PPTD v2 project with the bundled WASM writer"
    )
    parser.add_argument("input", type=Path, help=".pptd manifest or project directory")
    parser.add_argument("--output", "-o", type=Path, help="output .pptx path")
    parser.add_argument(
        "--transition",
        choices=("fade", "none"),
        default="fade",
        help="slide transition written to every slide (default: fade)",
    )
    parser.add_argument("--wasm", type=Path, help="override the bundled WASM writer")
    parser.add_argument("--force", action="store_true", help="replace an existing output")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        output = args.output or find_manifest(args.input).with_suffix(".pptx")
        summary = export_pptx(args.input, output, args.transition, args.force, args.wasm)
    except (ExportError, OSError, subprocess.SubprocessError) as exc:
        print(f"pptd export failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
