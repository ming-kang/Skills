#!/usr/bin/env python3
"""The local editor HTTP host for the headless export paths.

Serves the offline neo-ppt mirror plus one injected ``payload.json``, and —
when a project is mounted — the deck's local media under ``/__media__/``.
Both browser paths (PPTX export and image QA) get their host from here, so
they cannot disagree about how a deck reaches the editor.

``SKILL_DIR`` lives in ``pptd_common`` so this module and ``export_pptx.py``
share one definition of where the skill root is.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import unquote, urlparse

from pptd_common import SKILL_DIR, ExportError, log
from pptd_deck import IMAGE_MIME, build_payload, find_manifest, safe_project_path

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


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: Any) -> None:
        return


def resolve_editor_root() -> Path:
    """Locate the offline neo-ppt mirror (env override, else in-skill assets/editor)."""
    env = os.environ.get("PPTD_EDITOR_DIR") or os.environ.get("OPEN_KIMI_PPT_EDITOR")
    if env:
        return Path(env).expanduser().resolve()
    return SKILL_DIR / "assets" / "editor"


class EditorHost:
    """The running editor host: server, thread, URL and the media counter.

    Drivers shut the host down through ``shutdown()`` instead of poking at the
    server object, and read ``media_requests`` instead of reaching into a
    dynamically attached attribute.
    """

    def __init__(
        self,
        server: ThreadingHTTPServer,
        thread: threading.Thread,
        url: str,
        media_requests: Dict[str, int],
    ) -> None:
        self.server = server
        self.thread = thread
        self.url = url
        self._media_requests = media_requests

    @property
    def media_requests(self) -> int:
        """Media files the editor actually pulled from this host.

        A deck that references images but reports 0 is rendering placeholders.
        Only successful serves count: a 403/404 means the file never arrived.
        """
        return self._media_requests["count"]

    def shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def serve_local_editor(
    payload: Dict[str, Any],
    project_root: Optional[Path] = None,
) -> EditorHost:
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
            # Count at commit time (a 200 is on its way), not after streaming:
            # the client can finish reading before the handler returns.
            media_hits["count"] += 1
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
    return EditorHost(server, thread, url, media_hits)


def open_local_editor(
    manifest: Path, *, embed_media: bool = False
) -> Tuple[EditorHost, Dict[str, Any]]:
    """Build the payload and start the host that serves it, in one step.

    The two browser paths (image QA and the optional `--browser` export) must
    agree on how media is delivered. With `embed_media=False` (the default) the
    payload carries no base64 at all and the deck's media is served by the host
    instead; doing both halves in one call keeps them from drifting apart.
    """
    manifest = find_manifest(manifest)
    payload = build_payload(manifest, embed_media=embed_media)
    host = serve_local_editor(payload, project_root=manifest.parent)
    return host, payload
