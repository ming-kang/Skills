#!/usr/bin/env python3
"""Export a PPTD project to PPTX.

Default path (preferred): local patched WASM writer
  scripts/local-export/export-pptd.mjs
  → offline, no network, no browser.

Optional --browser path: the local editor UI via agent-browser
  (same UI as `node scripts/serve.mjs`).

Image QA (`export_images.py`) uses the same local editor host.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

from pptd_browser import (
    EditorExportSession,
    ensure_agent_browser,
    ensure_debug_chrome,
    open_export_dialog,
    switch_state,
    wait_for_export_dialog,
)
from pptd_common import (
    SKILL_DIR,
    ExportError,
    LocalExportUnavailable,
    log,
    run_command,
)
from pptd_deck import build_local_project, find_manifest
from pptd_editor_host import open_local_editor
from pptd_pptx import patch_transitions, verify_output

LOCAL_EXPORT_DIR = Path(__file__).resolve().parent / "local-export"
LOCAL_EXPORT_MJS = LOCAL_EXPORT_DIR / "export-pptd.mjs"
# Single canonical patched WASM, shipped with the skill.
CANONICAL_WASM_NAME = "pptd_wasm_bg-DPPWdROu.wasm"


def resolve_local_wasm() -> Path:
    candidate = SKILL_DIR / "assets" / "editor" / "app" / CANONICAL_WASM_NAME
    if candidate.is_file():
        return candidate
    raise LocalExportUnavailable(
        "patched WASM not found. Expected "
        f"assets/editor/app/{CANONICAL_WASM_NAME} inside the skill; "
        "the skill folder is incomplete."
    )


def export_pptx_local(
    source: Path,
    output: Path,
    transition: str,
    force: bool = False,
) -> Dict[str, Any]:
    """Export via local patched official WASM (no cookie / no browser UI)."""
    if not LOCAL_EXPORT_MJS.is_file():
        raise LocalExportUnavailable(f"local exporter missing: {LOCAL_EXPORT_MJS}")
    wasm_path = resolve_local_wasm()
    node = shutil.which("node")
    if not node:
        raise LocalExportUnavailable("node is required for local WASM export")

    manifest = find_manifest(source)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not force:
        raise ExportError(f"output already exists (pass --force to replace it): {output}")

    log(f"local WASM export: {manifest} → {output}")
    log(f"defaults: transition={transition} (offline)")

    # Parse here and hand over JSON: the Node side has no guaranteed YAML
    # package next to the skill, and its python fallback is not portable.
    project = build_local_project(manifest)
    handle, project_json = tempfile.mkstemp(prefix="pptd-project-", suffix=".json")
    os.close(handle)
    project_path = Path(project_json)
    try:
        project_path.write_text(
            json.dumps(project, ensure_ascii=False), encoding="utf-8"
        )
        # No --transition: the writer's own slide transition is overwritten by
        # patch_transitions() below, so this side is the single owner of the
        # transition policy. (The flag remains for standalone mjs use.)
        cmd = [
            node,
            str(LOCAL_EXPORT_MJS),
            "--json",
            str(project_path),
            "-o",
            str(output),
            "--wasm",
            str(wasm_path),
        ]

        # run_command captures via a UTF-8 temp file: text=True + PIPE would
        # decode node's UTF-8 output with the GBK locale on zh-CN Windows.
        process = run_command(cmd, timeout=300)
    finally:
        project_path.unlink(missing_ok=True)
    if process.returncode != 0:
        raise ExportError(
            f"local WASM export failed ({process.returncode}):\n{process.stdout[-4000:]}"
        )

    slide_count = patch_transitions(output, transition)
    summary = verify_output(output, transition, expect_fonts=False)
    summary["transitionPatchedSlides"] = slide_count
    summary["output"] = str(output)
    summary["exporter"] = "local-wasm-patched"
    log(f"local export ok: {output} ({output.stat().st_size} bytes)")
    return summary


def export_pptx(
    source: Path,
    output: Path,
    transition: str,
    embed_fonts: bool,
    force: bool = False,
    prefer_local: bool = True,
) -> Dict[str, Any]:
    """Prefer local patched WASM; fall back to the local editor browser UI.

    The fallback is reserved for a missing local toolchain. Deck and output
    errors propagate, so a broken deck is reported instead of silently
    escalating to the browser path (which may install agent-browser and
    download a Chromium).
    """
    if prefer_local:
        if embed_fonts:
            log(
                "note: the local WASM path does not embed fonts; "
                "pass --browser if you need font embedding"
            )
        try:
            return export_pptx_local(source, output, transition, force=force)
        except LocalExportUnavailable as exc:
            log(
                f"local WASM toolchain unavailable ({exc}); falling back to the local "
                "browser editor — this path needs a Chromium-based browser"
            )

    manifest = find_manifest(source)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not force:
        raise ExportError(f"output already exists (pass --force to replace it): {output}")
    agent_browser = ensure_agent_browser()
    cdp_port = ensure_debug_chrome()

    log(f"manifest: {manifest}")
    log(
        f"defaults: transition={transition}, embed_fonts={'on' if embed_fonts else 'off'}"
    )

    # One call so the payload and the host agree on how media is delivered.
    host, payload = open_local_editor(manifest)
    with EditorExportSession(
        agent_browser, host, session_prefix="pptd-export", cdp_port=cdp_port
    ) as session:
        dialog = open_export_dialog(session.browser)

        state = switch_state(dialog)
        if state is not None:
            switch_ref, checked, disabled = state
            if disabled and checked != embed_fonts:
                log("warning: the font switch is disabled for this deck")
            elif checked != embed_fonts:
                session.browser.run(["click", f"@{switch_ref}"])
                dialog = wait_for_export_dialog(session.browser)
        elif embed_fonts:
            log("warning: the export dialog exposed no font switch")

        # Plain click (not agent-browser `download`) so Chrome saves to the
        # default Downloads folder; --download-path is broken on some Windows setups.
        log("generating PPTX in the local editor")
        downloaded = session.download_from_dialog(dialog, click_timeout=180)
        shutil.copy2(downloaded, output)
        try:
            if downloaded.resolve().parent == session.downloads.resolve():
                downloaded.unlink(missing_ok=True)
        except OSError:
            pass

    slide_count = patch_transitions(output, transition)
    summary = verify_output(output, transition, embed_fonts)
    summary["transitionPatchedSlides"] = slide_count
    summary["output"] = str(output)
    summary["exporter"] = "browser-local-editor"
    return summary


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export a PPTD project to PPTX. "
            "Default: local patched official WASM (offline). "
            "Optional --browser uses the local editor UI (also offline)."
        )
    )
    parser.add_argument("input", type=Path, help=".pptd manifest or project directory")
    parser.add_argument("--output", "-o", type=Path, help="output .pptx path")
    parser.add_argument(
        "--transition",
        choices=("fade", "none"),
        default="fade",
        help="slide transition written to every slide (default: fade)",
    )
    parser.add_argument(
        "--no-embed-fonts",
        dest="embed_fonts",
        action="store_false",
        default=True,
        help="disable font embedding (browser path; default: on when available)",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="force the local editor browser UI path instead of Node WASM",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing output file",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        output = args.output or find_manifest(args.input).with_suffix(".pptx")
        summary = export_pptx(
            args.input,
            output,
            args.transition,
            args.embed_fonts,
            args.force,
            prefer_local=not args.browser,
        )
    except (ExportError, OSError, subprocess.SubprocessError) as exc:
        print(f"pptd export failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
