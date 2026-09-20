#!/usr/bin/env python3
"""Export a PPTD project to PPTX.

Default path (preferred): local patched WASM writer
  scripts/local-export/export-pptd.mjs
  → offline, no network, no browser.

Optional --browser path: local neo-ppt editor mirror via agent-browser
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
import threading
import time
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple
from urllib.parse import unquote, urlparse

from pptd_browser import (
    BrowserSession,
    ensure_agent_browser,
    ensure_debug_chrome,
    find_download,
    open_export_dialog,
    ref_by_name,
    set_download_behavior,
    switch_state,
    wait_for_export_dialog,
    wait_for_editor_media,
)
from pptd_common import (
    PROXY_ENV_KEYS,
    ExportError,
    LocalExportUnavailable,
    default_downloads_dir,
    ensure_module,
    log,
    run_command,
    temporary_directory,
)
from pptd_deck import (
    IMAGE_MIME,
    build_local_project,
    build_payload,
    find_manifest,
    safe_project_path,
)
from pptd_pptx import is_pptx, patch_transitions, verify_output

SKILL_DIR = Path(__file__).resolve().parent.parent
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: Any) -> None:
        return


def resolve_editor_root() -> Path:
    """Locate the offline neo-ppt mirror (env override, else in-skill assets/editor)."""
    env = os.environ.get("PPTD_EDITOR_DIR") or os.environ.get("OPEN_KIMI_PPT_EDITOR")
    if env:
        return Path(env).expanduser().resolve()
    return SKILL_DIR / "assets" / "editor"


MEDIA_MOUNT = "__media__"
# What the editor may pull through the media mount: images and fonts by relative
# path. A deck directory holds nothing else the page needs over HTTP (manifest
# and pages already travel inside payload.json).
SERVE_MEDIA_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".avif",
    ".woff", ".woff2", ".ttf", ".otf", ".fntdata",
}
MEDIA_CONTENT_TYPES = {
    **IMAGE_MIME,
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".fntdata": "application/octet-stream",
}


def serve_local_editor(
    payload: Dict[str, Any],
    project_root: Optional[Path] = None,
) -> Tuple[ThreadingHTTPServer, threading.Thread, str]:
    """Serve the offline editor and inject payload.json for headless export.

    When `project_root` is given, the deck's local media is served from
    `/<MEDIA_MOUNT>/<relative path>` instead of being base64-inlined into the
    payload, and the host records that base URL in `payload["mediaBase"]` so the
    bridge fetches it instead of looking in `imageMap`.
    """
    editor_root = resolve_editor_root()
    # Announce the media mount *before* serializing: the payload is the only
    # channel that tells the bridge media is served rather than embedded.
    if project_root is not None:
        payload["mediaBase"] = f"/{MEDIA_MOUNT}/"
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    # How many media files the editor actually pulled: a deck that references
    # images but requests none is silently rendering placeholders.
    media_hits = {"count": 0}

    class LocalEditorHandler(QuietHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(editor_root), **kwargs)

        def _path(self) -> str:
            # Percent-decode first: "%2e%2e%2f" must be judged as ".." rather
            # than as a literal file name that happens not to exist.
            return urlparse(unquote(self.path)).path

        def _is_payload(self) -> bool:
            return self._path() in ("/payload.json", "payload.json")

        def _media_relative(self) -> Optional[str]:
            prefix = f"/{MEDIA_MOUNT}/"
            path = self._path()
            return path[len(prefix):] if path.startswith(prefix) else None

        def _serve_media(self, relative: str) -> None:
            if project_root is None:
                # No project mounted: the route does not exist.
                self.send_error(404, "No project mounted")
                return
            # The editor asks for some assets with a leading slash
            # ("/media/x.png"); drop it so the path stays project-relative.
            relative = relative.lstrip("/")
            media_hits["count"] += 1
            try:
                media_path = safe_project_path(project_root, relative)
            except ExportError:
                self.send_error(403, "Forbidden")
                return
            suffix = media_path.suffix.lower()
            if suffix not in SERVE_MEDIA_SUFFIXES:
                self.send_error(404, "Unsupported media type")
                return
            if not media_path.is_file():
                self.send_error(404, "Media not found")
                return
            self.send_response(200)
            self.send_header(
                "Content-Type", MEDIA_CONTENT_TYPES.get(suffix, "application/octet-stream")
            )
            self.send_header("Content-Length", str(media_path.stat().st_size))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                with media_path.open("rb") as handle:
                    shutil.copyfileobj(handle, self.wfile)

        def do_GET(self) -> None:  # noqa: N802
            relative = self._media_relative()
            if relative is not None:
                self._serve_media(relative)
                return
            if self._is_payload():
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                # No CORS header: the editor page is same-origin, and the payload
                # is the deck plus a pointer to where its media lives.
                self.send_header("Content-Length", str(len(payload_bytes)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload_bytes)
                return
            return SimpleHTTPRequestHandler.do_GET(self)

        def do_HEAD(self) -> None:  # noqa: N802
            relative = self._media_relative()
            if relative is not None:
                self._serve_media(relative)
                return
            if self._is_payload():
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload_bytes)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
            return SimpleHTTPRequestHandler.do_HEAD(self)

    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalEditorHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    url = f"http://{host}:{port}/?ndExport=1"
    if project_root is not None:
        log(f"local editor host: {url} (root={editor_root}, media={project_root})")
    else:
        log(f"local editor host: {url} (root={editor_root})")
    server.media_hits = media_hits
    return server, thread, url


def open_local_editor(
    manifest: Path, *, embed_media: bool = False
) -> Tuple[ThreadingHTTPServer, threading.Thread, str, Dict[str, Any]]:
    """Build the payload and start the host that serves it, in one step.

    The two browser paths (image QA and the optional `--browser` export) must
    agree on how media is delivered. With `embed_media=False` (the default) the
    payload carries no base64 at all and the deck's media is served by the host
    instead; doing both halves in one call keeps them from drifting apart.
    """
    manifest = find_manifest(manifest)
    payload = build_payload(manifest, embed_media=embed_media)
    server, thread, url = serve_local_editor(payload, project_root=manifest.parent)
    return server, thread, url, payload


LOCAL_EXPORT_DIR = Path(__file__).resolve().parent / "local-export"
LOCAL_EXPORT_MJS = LOCAL_EXPORT_DIR / "export-pptd.mjs"
# Single canonical patched WASM, shipped with the skill.
CANONICAL_WASM_NAME = "pptd_wasm_bg-DPPWdROu.wasm"


def resolve_local_wasm() -> Path:
    candidate = SKILL_DIR / "assets" / "editor" / "neo-ppt" / "assets" / CANONICAL_WASM_NAME
    if candidate.is_file():
        return candidate
    raise LocalExportUnavailable(
        "patched WASM not found. Expected "
        f"assets/editor/neo-ppt/assets/{CANONICAL_WASM_NAME} inside the skill; "
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
        cmd = [
            node,
            str(LOCAL_EXPORT_MJS),
            "--json",
            str(project_path),
            "-o",
            str(output),
            "--transition",
            transition if transition in ("fade", "none") else "fade",
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
    """Prefer local patched WASM; fall back to local neo-ppt browser UI.

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

    with temporary_directory(prefix="pptd-export-") as temp_name:
        temp_dir = Path(temp_name)
        download_dir = temp_dir / "downloads"
        download_dir.mkdir()
        # One call so the payload and the host agree on how media is delivered.
        server, thread, url, payload = open_local_editor(manifest)
        session = f"pptd-export-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        browser = BrowserSession(agent_browser, session, temp_dir, download_dir, cdp_port)
        downloads = default_downloads_dir()
        download_redirect = None
        try:
            log("opening the local neo-ppt editor")
            browser.open(url)
            # Keep the export ZIP out of the user's Downloads folder. The socket
            # must stay open until the download finished (see its docstring).
            download_redirect = set_download_behavior(browser, download_dir)
            browser.run(
                [
                    "wait",
                    "--fn",
                    'document.documentElement.dataset.deckStatus === "ready"',
                ],
                timeout=120,
            )
            # "ready" precedes the media fetches the host-served images need.
            wait_for_editor_media(browser)
            browser.run(["set", "viewport", "1280", "720"])
            dialog = open_export_dialog(browser)

            state = switch_state(dialog)
            if state is not None:
                switch_ref, checked, disabled = state
                if disabled and checked != embed_fonts:
                    log("warning: the font switch is disabled for this deck")
                elif checked != embed_fonts:
                    browser.run(["click", f"@{switch_ref}"])
                    dialog = wait_for_export_dialog(browser)
            elif embed_fonts:
                log("warning: the export dialog exposed no font switch")

            # Plain click (not agent-browser `download`) so Chrome saves to the
            # default Downloads folder; --download-path is broken on some Windows setups.
            started_at = time.time() - 1.0
            download_ref = ref_by_name(dialog, "下载", "button")
            log("generating PPTX in the local editor")
            browser.run(["click", f"@{download_ref}"], timeout=180)
            downloaded = find_download(
                (downloads, download_dir, temp_dir),
                timeout=90,
                since=started_at,
            )
            shutil.copy2(downloaded, output)
            try:
                if downloaded.resolve().parent == downloads.resolve():
                    downloaded.unlink(missing_ok=True)
            except OSError:
                pass
        finally:
            browser.close()
            if download_redirect is not None:
                try:
                    download_redirect.close()
                except Exception:  # noqa: BLE001 - the export is already done
                    pass
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

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
            "Optional --browser uses the local neo-ppt mirror (also offline)."
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
        help="force local neo-ppt browser UI path instead of Node WASM",
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
