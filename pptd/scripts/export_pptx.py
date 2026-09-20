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
import base64
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid
import zipfile
import xml.etree.ElementTree as ET
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import unquote, urlparse

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

SKILL_DIR = Path(__file__).resolve().parent.parent
IMAGE_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_EMBEDDED_MEDIA_BYTES = 200 * 1024 * 1024
PPTX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"
)
FADE_TRANSITION_XML = (
    '<p:transition spd="fast" advClick="1"><p:fade/></p:transition>'
)
MIN_AGENT_BROWSER_VERSION = (0, 33, 2)
MIN_NODE_MAJOR = 18
NODE_INSTALL_HINT = "Install Node.js 18+ from https://nodejs.org, then retry."
EDITOR_MISSING_HINT = (
    "local neo-ppt editor not found. The skill folder is incomplete "
    "(expected assets/editor/ next to scripts/), or set PPTD_EDITOR_DIR "
    "to the editor directory."
)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: Any) -> None:
        return


def parse_version(output: str) -> Tuple[int, int, int]:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)\b", output)
    if not match:
        raise ExportError(f"could not parse agent-browser version from: {output.strip()}")
    return tuple(int(part) for part in match.groups())


def parse_node_version(output: str) -> Tuple[int, int, int]:
    match = re.search(r"v?(\d+)\.(\d+)\.(\d+)\b", output)
    if not match:
        raise ExportError(f"could not parse Node.js version from: {output.strip()}")
    return tuple(int(part) for part in match.groups())


def read_agent_browser_version(executable: str) -> Tuple[int, int, int]:
    process = run_command([executable, "--version"], timeout=30)
    if process.returncode != 0:
        raise ExportError(f"agent-browser --version failed:\n{process.stdout[-2000:]}")
    return parse_version(process.stdout)


def ensure_nodejs() -> str:
    executable = shutil.which("node")
    if not executable:
        raise ExportError(f"Node.js is not installed or not on PATH. {NODE_INSTALL_HINT}")

    process = run_command([executable, "--version"], timeout=30)
    if process.returncode != 0:
        raise ExportError(f"node --version failed:\n{process.stdout[-2000:]}")

    version = parse_node_version(process.stdout)
    if version[0] < MIN_NODE_MAJOR:
        raise ExportError(
            f"Node.js {MIN_NODE_MAJOR}+ is required; found "
            f"{'.'.join(map(str, version))} ({process.stdout.strip()}). {NODE_INSTALL_HINT}"
        )

    npm = shutil.which("npm")
    if not npm:
        raise ExportError(
            "npm is not installed or not on PATH. "
            f"npm ships with Node.js. {NODE_INSTALL_HINT}"
        )

    log(f"Node.js version: {'.'.join(map(str, version))}")
    return executable


def ensure_agent_browser() -> str:
    ensure_nodejs()

    executable = shutil.which("agent-browser")
    version = read_agent_browser_version(executable) if executable else None
    if version is not None and version >= MIN_AGENT_BROWSER_VERSION:
        log(f"agent-browser version: {'.'.join(map(str, version))}")
        return executable

    npm = shutil.which("npm")
    if not npm:
        reason = "not installed" if version is None else ".".join(map(str, version))
        raise ExportError(
            f"agent-browser {reason}; npm is required to install agent-browser@latest. "
            f"npm ships with Node.js. {NODE_INSTALL_HINT}"
        )

    current = "not installed" if version is None else ".".join(map(str, version))
    minimum = ".".join(map(str, MIN_AGENT_BROWSER_VERSION))
    log(f"agent-browser {current} is below {minimum}; installing agent-browser@latest")
    process = run_command(
        [npm, "install", "-g", "agent-browser@latest"],
        timeout=300,
    )
    if process.returncode != 0:
        raise ExportError(f"failed to install agent-browser@latest:\n{process.stdout[-4000:]}")

    executable = shutil.which("agent-browser")
    if not executable:
        raise ExportError("agent-browser@latest installed, but executable is not on PATH")
    version = read_agent_browser_version(executable)
    if version < MIN_AGENT_BROWSER_VERSION:
        raise ExportError(
            "agent-browser@latest is still below the required version "
            f"{minimum}: {'.'.join(map(str, version))}"
        )
    log(f"agent-browser upgraded to {'.'.join(map(str, version))}")
    return executable


DEBUG_CHROME_PORT = 9337
CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)
# Process names we are allowed to kill when reclaiming our own debug browser.
CDP_IMAGE_NAMES = ("chrome.exe", "msedge.exe", "chrome", "chromium", "chromium-browser", "google-chrome")
# One debug browser is reused across exports; after this much idle time the next
# run reclaims it so an interrupted export cannot leave one behind forever.
CDP_IDLE_MINUTES = float(os.environ.get("PPTD_DEBUG_CHROME_IDLE_MINUTES") or 60)
CDP_REGISTRY_PATH = Path(tempfile.gettempdir()) / "pptd-cdp.json"
# Fixed profile so relaunching joins the running browser instead of forking a
# second one. Also the signature `debug_chrome_is_ours` checks before reclaiming.
DEBUG_CHROME_PROFILE = Path(tempfile.gettempdir()) / "pptd-cdp-profile"


def agent_browser_has_chrome(executable: str) -> Optional[bool]:
    """Ask agent-browser itself whether it can drive a browser.

    agent-browser auto-detects system Chrome/Brave plus Playwright and Puppeteer
    caches; replicating that detection here would be fragile, so `doctor` output
    is the source of truth. Returns None when this CLI build has no `doctor`.
    """
    try:
        process = run_command([executable, "doctor"], timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    text = process.stdout or ""
    if "Unknown command" in text:
        return None
    if process.returncode != 0:
        return None
    in_chrome_section = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not line.startswith(("pass", "info", "warn", "fail")):
            in_chrome_section = line == "Chrome"
            continue
        if in_chrome_section and line.startswith("pass"):
            return True
    return False


def host_has_browser_cache() -> bool:
    """Broad fallback check used only when `agent-browser doctor` is unavailable."""
    home = Path.home()
    if os.name == "nt":
        roots = [home / ".cache" / "puppeteer", home / "AppData" / "Local" / "ms-playwright"]
        if any(Path(candidate).exists() for candidate in CHROME_CANDIDATES):
            return True
    elif sys.platform == "darwin":
        roots = [
            home / ".cache" / "puppeteer",
            home / "Library" / "Caches" / "ms-playwright",
        ]
        if any(
            Path(app).exists()
            for app in (
                "/Applications/Google Chrome.app",
                "/Applications/Chromium.app",
                "/Applications/Microsoft Edge.app",
                "/Applications/Brave Browser.app",
            )
        ):
            return True
    else:
        roots = [home / ".cache" / "ms-playwright", home / ".cache" / "puppeteer"]
        if any(
            shutil.which(name)
            for name in (
                "google-chrome",
                "google-chrome-stable",
                "chromium",
                "chromium-browser",
                "microsoft-edge",
                "msedge",
                "brave-browser",
            )
        ):
            return True
    return any(root.exists() and any(root.iterdir()) for root in roots)


def ensure_chromium(executable: str) -> None:
    """agent-browser drives Chrome over CDP. On a host with no usable browser at
    all (e.g. a Firefox-only machine), provision one with `agent-browser install`
    (Chrome for Testing, one-time download)."""
    available = agent_browser_has_chrome(executable)
    if available is None:
        available = host_has_browser_cache()
    if available:
        return
    log("agent-browser reports no usable browser; provisioning one via 'agent-browser install'")
    process = run_command([executable, "install"], timeout=900)
    if process.returncode != 0:
        raise ExportError(
            "agent-browser could not provision a browser (Chrome for Testing "
            "download failed). Install a Chromium-based browser manually, or run "
            "'agent-browser install' yourself.\n" + process.stdout[-4000:]
        )
    available = agent_browser_has_chrome(executable)
    if available is None:
        available = host_has_browser_cache()
    if not available:
        raise ExportError(
            "agent-browser install completed but no usable browser is available; "
            "install a Chromium-based browser manually."
        )
    log("agent-browser provisioned Chrome for Testing")


def process_image_name(pid: Optional[int]) -> Optional[str]:
    """Image name of a pid, or None when it cannot be determined.

    Used as a safety check before reclaiming a debug browser: a PID recorded in
    the registry may since have been recycled by an unrelated process.
    """
    if not pid:
        return None
    if sys.platform == "win32":
        try:
            process = run_command(["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"], timeout=20)
        except (OSError, subprocess.SubprocessError):
            return None
        for line in (process.stdout or "").splitlines():
            if not line.strip().startswith('"'):
                continue
            parts = [part.strip('"') for part in line.split('","')]
            if parts and parts[0].lower() in CDP_IMAGE_NAMES:
                return parts[0].lower()
        return None
    try:
        process = run_command(["ps", "-o", "comm=", "-p", str(pid)], timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    name = (process.stdout or "").strip().lower()
    return name if any(candidate in name for candidate in CDP_IMAGE_NAMES) else None


def process_command_line(pid: Optional[int]) -> Optional[str]:
    """Full command line of a pid, or None when it cannot be read.

    The strongest available signature that a browser process is *ours*: only the
    debug browser this skill started carries our `--user-data-dir`. A recycled
    pid that now belongs to someone else's Chrome fails this check.
    """
    if not pid:
        return None
    if sys.platform == "win32":
        query = (
            "Get-CimInstance Win32_Process -Filter \"ProcessId="
            f"{pid}\" | Select-Object -ExpandProperty CommandLine"
        )
        try:
            process = run_command(["powershell", "-NoProfile", "-Command", query], timeout=60)
        except (OSError, subprocess.SubprocessError):
            return None
        return (process.stdout or "").strip() or None
    try:
        process = run_command(["ps", "-o", "command=", "-p", str(pid)], timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return (process.stdout or "").strip() or None


def read_cdp_registry() -> List[Dict[str, Any]]:
    """Debug browsers this skill started (best effort; the file may be gone)."""
    try:
        value = json.loads(CDP_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    entries = value.get("instances") if isinstance(value, dict) else value
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def write_cdp_registry(entries: Sequence[Dict[str, Any]]) -> None:
    try:
        CDP_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        CDP_REGISTRY_PATH.write_text(
            json.dumps({"instances": list(entries)}, indent=2), encoding="utf-8"
        )
    except OSError:
        # The registry only exists so idle instances can be reclaimed later.
        pass


def registered_debug_chrome(port: int) -> Optional[Dict[str, Any]]:
    for entry in read_cdp_registry():
        if entry.get("port") == port and entry.get("pid"):
            return entry
    return None


def debug_chrome_is_ours(entry: Dict[str, Any]) -> bool:
    """Only reclaim browsers this skill started, with a matching signature.

    Three checks: the registry entry carries the skill's own profile directory,
    the pid still belongs to a browser process, and that process was launched
    with our profile. A pid that has since been recycled by an unrelated
    browser fails the last check, and a machine where the command line cannot
    be read fails it too — reclaiming is best effort, so "cannot tell" means
    "leave it alone" rather than "kill it".
    """
    pid = entry.get("pid")
    profile = str(entry.get("profile") or "")
    if not pid or os.path.basename(profile.rstrip("/\\")) != "pptd-cdp-profile":
        return False
    if process_image_name(pid) is None:
        return False
    command = process_command_line(pid)
    if command is None:
        return False
    # We launch with an unquoted `--user-data-dir=<profile>`; Chrome may also
    # quote the path when relaunching itself, so accept both spellings.
    return f"--user-data-dir={profile}" in command or f'--user-data-dir="{profile}"' in command


def kill_debug_chrome(entry: Dict[str, Any]) -> bool:
    """Terminate a registered debug browser. Never touches foreign browsers."""
    pid = entry.get("pid")
    if not debug_chrome_is_ours(entry):
        return False
    if sys.platform == "win32":
        run_command(["taskkill", "/pid", str(pid), "/T", "/F"], timeout=30)
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return False
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process_image_name(pid) is None:
            return True
        time.sleep(0.3)
    return process_image_name(pid) is None


def register_cdp_instance(port: int, profile: Path) -> None:
    """Record a debug browser we started so it can be reclaimed later."""
    now = time.time()
    entries = [entry for entry in read_cdp_registry() if entry.get("port") != port]
    entries.append(
        {
            "port": port,
            "pid": find_debug_chrome_pid(port),
            "profile": str(profile),
            "startedAt": now,
            "lastUsedAt": now,
        }
    )
    write_cdp_registry(entries)


def find_debug_chrome_pid(port: int) -> Optional[int]:
    """Best-effort pid of the browser listening on `port` (Windows only).

    Chrome spawns a launcher that hands off to the real browser, so the pid we
    need is the one owning the debugging socket, not the one we spawned.
    `netstat` gives the owner without extra dependencies.
    """
    try:
        process = run_command(["netstat", "-a", "-n", "-o"], timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    needle = f"127.0.0.1:{port}"
    for line in (process.stdout or "").splitlines():
        if "LISTENING" not in line or needle not in line:
            continue
        parts = line.split()
        if parts:
            try:
                return int(parts[-1])
            except ValueError:
                continue
    return None


def touch_cdp_registry(port: int) -> None:
    entries = read_cdp_registry()
    changed = False
    for entry in entries:
        if entry.get("port") == port:
            entry["lastUsedAt"] = time.time()
            changed = True
    if changed:
        write_cdp_registry(entries)


def reap_idle_debug_chrome(
    idle_minutes: Optional[float] = None, force: bool = False
) -> List[Dict[str, Any]]:
    """Reclaim debug browsers that have been idle for too long.

    The Windows export path keeps one debug browser alive so repeated exports
    reuse it instead of piling up processes. When the exporting process is
    killed, nothing closes it, so the next run reclaims whatever has been idle
    longer than the limit. A browser the user pointed us at through
    AGENT_BROWSER_CDP is never registered and therefore never reclaimed.

    `idle_minutes=0` disables reaping; `force=True` reclaims regardless of age
    (used by the explicit clean-up command).
    """
    limit = CDP_IDLE_MINUTES if idle_minutes is None else idle_minutes
    if limit <= 0 and not force:
        return []
    entries = read_cdp_registry()
    if not entries:
        return []
    now = time.time()
    kept: List[Dict[str, Any]] = []
    reaped: List[Dict[str, Any]] = []
    for entry in entries:
        try:
            last_used = float(entry.get("lastUsedAt") or entry.get("startedAt") or 0)
        except (TypeError, ValueError):
            last_used = 0
        idle_for = now - last_used
        if (force or idle_for >= limit * 60) and cdp_alive(int(entry.get("port") or 0)):
            if kill_debug_chrome(entry):
                log(
                    f"reclaimed idle debug browser on port {entry.get('port')} "
                    f"(idle {idle_for / 60:.0f} min)"
                )
                reaped.append(entry)
                continue
        entry["lastUsedAt"] = now if cdp_alive(int(entry.get("port") or 0)) else last_used
        kept.append(entry)
    if reaped:
        write_cdp_registry(kept)
    return reaped


def cdp_alive(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2):
            return True
    except OSError:
        return False


def ensure_debug_chrome() -> Optional[int]:
    """Return a CDP port for agent-browser to connect to (Windows only).

    On Windows agent-browser cannot launch Chrome itself: the Chrome launcher
    process hands off to a child and exits, which agent-browser mistakes for a
    crash ("Chrome exited early without writing DevToolsActivePort"). The
    export therefore always drives an externally started browser. An
    already-working AGENT_BROWSER_CDP wins and is never managed by us;
    otherwise a dedicated debug instance is started (or reused) on port 9337.
    Reuse is intentional — relaunching with the same profile joins the existing
    browser, so repeated exports reuse one instance instead of piling up
    processes — but every instance we start is registered so that
    `reap_idle_debug_chrome()` can reclaim one whose exporting process died.
    """
    if sys.platform != "win32":
        return None

    explicit = os.environ.get("AGENT_BROWSER_CDP")
    if explicit:
        try:
            if cdp_alive(int(explicit)):
                return int(explicit)
        except ValueError:
            pass
        log(f"AGENT_BROWSER_CDP={explicit} is not answering; starting a debug browser instead")

    port = DEBUG_CHROME_PORT
    override = os.environ.get("PPTD_DEBUG_CHROME_PORT")
    if override:
        try:
            port = int(override)
        except ValueError:
            log(f"ignoring invalid PPTD_DEBUG_CHROME_PORT={override!r}")

    reap_idle_debug_chrome()

    entry = registered_debug_chrome(port)
    if entry and debug_chrome_is_ours(entry) and cdp_alive(port):
        touch_cdp_registry(port)
        log(f"reusing debug browser on 127.0.0.1:{port} (pid {entry.get('pid')})")
        return port

    if cdp_alive(port):
        # Something answers CDP here but is not ours (a browser the user started
        # by hand): reuse it, never register and never reclaim it.
        log(f"using the CDP browser already listening on 127.0.0.1:{port}")
        return port

    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            # Port taken by something that is not a CDP endpoint.
            with socket.socket() as spare:
                spare.bind(("127.0.0.1", 0))
                port = spare.getsockname()[1]

    executable = next((c for c in CHROME_CANDIDATES if Path(c).is_file()), None)
    if executable is None:
        raise ExportError(
            "no Chrome or Edge found to drive the export; install Google Chrome, "
            "or start a browser with --remote-debugging-port yourself and set "
            "AGENT_BROWSER_CDP to that port"
        )
    profile = DEBUG_CHROME_PROFILE
    log(f"starting debug browser on port {port}: {executable}")
    subprocess.Popen(
        [
            executable,
            f"--user-data-dir={profile}",
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-position=-2400,0",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if cdp_alive(port):
            register_cdp_instance(port, profile)
            log(
                f"debug browser stays running on 127.0.0.1:{port} for reuse; "
                f"it is reclaimed automatically after {CDP_IDLE_MINUTES:.0f} idle minutes "
                "(close that window to stop it now; override with "
                "PPTD_DEBUG_CHROME_PORT / PPTD_DEBUG_CHROME_IDLE_MINUTES)"
            )
            return port
        time.sleep(0.5)
    raise ExportError(f"debug browser did not open CDP port {port} within 20s")


def find_manifest(source: Path) -> Path:
    source = source.expanduser().resolve()
    if source.is_file():
        if source.suffix.lower() != ".pptd":
            raise ExportError(f"input must be a .pptd file or project directory: {source}")
        return source
    if not source.is_dir():
        raise ExportError(f"input does not exist: {source}")
    manifests = sorted(source.rglob("*.pptd"))
    if not manifests:
        raise ExportError(f"no .pptd manifest found under: {source}")
    if len(manifests) > 1:
        choices = "\n  ".join(str(path) for path in manifests[:20])
        raise ExportError(
            "multiple .pptd manifests found; pass one manifest explicitly:\n  " + choices
        )
    return manifests[0]


def read_yaml_mapping(path: Path) -> Tuple[str, Dict[str, Any]]:
    yaml = ensure_module("yaml", "pyyaml", "PyYAML is required to read PPTD YAML")
    text = path.read_text(encoding="utf-8")
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ExportError(f"invalid YAML in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ExportError(f"expected a YAML mapping in {path}")
    return text, value


def safe_project_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise ExportError("page path must be a non-empty string")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ExportError(f"project path escapes the PPTD directory: {relative}") from exc
    return candidate


def collect_image_sources(pages_data: Iterable[Dict[str, Any]]) -> List[str]:
    """Local image sources actually referenced by the deck, in first-seen order.

    Scanning the project directory instead would sweep up unrelated files —
    notably the page renders under .qa-images/, which the visual-QA loop writes
    into the project root and regenerates on every round.
    """
    sources: List[str] = []
    seen = set()

    def visit(holder: Any) -> None:
        if not isinstance(holder, dict):
            return
        src = holder.get("src")
        if not isinstance(src, str) or not src.strip():
            return
        if re.match(r"^(https?://|data:)", src, re.IGNORECASE):
            return
        if src in seen:
            return
        seen.add(src)
        sources.append(src)

    for page in pages_data:
        if not isinstance(page, dict):
            continue
        background = page.get("background")
        if isinstance(background, dict) and background.get("type") == "image":
            visit(background)
        elements = page.get("elements")
        if not isinstance(elements, list):
            continue
        for element in elements:
            if not isinstance(element, dict):
                continue
            if element.get("elementType") == "image":
                visit(element)
            fill = element.get("fill")
            if isinstance(fill, dict) and fill.get("type") == "image":
                visit(fill)
    return sources


def build_image_map(root: Path, pages_data: Iterable[Dict[str, Any]]) -> Dict[str, str]:
    image_map: Dict[str, str] = {}
    total = 0
    for src in collect_image_sources(pages_data):
        path = safe_project_path(root, re.sub(r"^file://+", "", src))
        if not path.is_file():
            log(f"skip missing local image: {src}")
            continue
        suffix = path.suffix.lower()
        if suffix not in IMAGE_MIME:
            log(f"skip unsupported image type: {src}")
            continue
        size = path.stat().st_size
        if size > MAX_IMAGE_BYTES:
            log(f"skip local image over 20 MiB: {src}")
            continue
        if total + size > MAX_EMBEDDED_MEDIA_BYTES:
            raise ExportError(
                "local image payload exceeds 200 MiB; reduce media size or use remote URLs"
            )
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        image_map[src] = f"data:{IMAGE_MIME[suffix]};base64,{data}"
        total += size
    if image_map:
        log(f"prepared {len(image_map)} local image resource(s), {total} bytes")
    return image_map


def build_payload(manifest: Path, embed_media: bool = False) -> Dict[str, Any]:
    """Assemble the headless payload for the local editor.

    `embed_media=False` (the default) leaves `imageMap` empty: the deck's local
    media is served by the host that also serves the payload, so a deck with
    hundreds of high-resolution images no longer inflates the JSON (and the
    browser's memory) by a base64 factor. `embed_media=True` restores the old
    self-contained payload for hosts that cannot serve the project directory.
    """
    manifest_text, manifest_data = read_yaml_mapping(manifest)
    if manifest_data.get("version") != "v2":
        raise ExportError("local PPTX export currently requires PPTD version: v2")
    page_paths = manifest_data.get("pages")
    if not isinstance(page_paths, list) or not page_paths:
        raise ExportError("PPTD manifest must contain a non-empty pages list")

    root = manifest.parent.resolve()
    pages: List[Dict[str, str]] = []
    pages_data: List[Dict[str, Any]] = []
    for entry in page_paths:
        page_path = safe_project_path(root, entry)
        if not page_path.is_file():
            raise ExportError(f"missing page file: {entry}")
        page_text, page_data = read_yaml_mapping(page_path)
        if not isinstance(page_data.get("elements"), list):
            raise ExportError(f"page elements must be an array: {entry}")
        pages.append({"path": str(entry), "content": page_text})
        pages_data.append(page_data)

    title = str(manifest_data.get("title") or manifest.stem)
    return {
        "id": f"local-export-{uuid.uuid4().hex}",
        "title": title,
        "manifestPath": manifest.name,
        "manifestContent": manifest_text,
        "pages": pages,
        "imageMap": build_image_map(root, pages_data) if embed_media else {},
    }


def build_local_project(manifest: Path) -> Dict[str, Any]:
    """Pre-parsed project for the local WASM exporter (`export-pptd.mjs --json`).

    The Node side has no guaranteed YAML package next to the skill, so the
    parsing happens here, where PyYAML is already a hard dependency.
    """
    _, manifest_data = read_yaml_mapping(manifest)
    if manifest_data.get("version") != "v2":
        raise ExportError("local PPTX export currently requires PPTD version: v2")
    page_paths = manifest_data.get("pages")
    if not isinstance(page_paths, list) or not page_paths:
        raise ExportError("PPTD manifest must contain a non-empty pages list")

    root = manifest.parent.resolve()
    pages: List[Dict[str, Any]] = []
    for entry in page_paths:
        page_path = safe_project_path(root, entry)
        if not page_path.is_file():
            raise ExportError(f"missing page file: {entry}")
        _, page_data = read_yaml_mapping(page_path)
        if not isinstance(page_data.get("elements"), list):
            raise ExportError(f"page elements must be an array: {entry}")
        pages.append({"path": str(entry), "data": page_data})

    return {
        "manifestPath": str(manifest),
        "manifest": manifest_data,
        "pages": pages,
    }


def json_result(output: str) -> Dict[str, Any]:
    for line in reversed(output.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ExportError(f"agent-browser returned no JSON object:\n{output[-2000:]}")


def browser_cdp_url(browser: "BrowserSession") -> str:
    process = browser.run(["get", "cdp-url"], timeout=30)
    match = re.search(r"ws://\S+", process.stdout)
    if not match:
        raise ExportError(
            f"could not determine the browser CDP URL:\n{process.stdout[-500:]}"
        )
    return match.group(0)


def cdp_connect(cdp_url: str) -> Any:
    # websocket-client honors proxy env vars; the CDP endpoint is local, so
    # strip proxy settings instead of tunneling localhost through a proxy.
    websocket = ensure_module(
        "websocket", "websocket-client", "websocket-client is required for browser automation"
    )
    saved_proxy = {name: os.environ.pop(name) for name in PROXY_ENV_KEYS if name in os.environ}
    try:
        return websocket.create_connection(cdp_url, timeout=30, suppress_origin=True)
    finally:
        os.environ.update(saved_proxy)


def cdp_call(
    socket: Any,
    request_id: int,
    method: str,
    params: Dict[str, Any],
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Send one CDP command and wait for its reply."""
    message: Dict[str, Any] = {"id": request_id, "method": method, "params": params}
    if session_id:
        message["sessionId"] = session_id
    socket.send(json.dumps(message))
    while True:
        reply = json.loads(socket.recv())
        if reply.get("id") != request_id:
            continue
        if "error" in reply:
            raise ExportError(f"CDP {method} failed: {reply['error']}")
        return reply.get("result", {})


def set_download_behavior(browser: "BrowserSession", download_dir: Path, url_hint: str = "127.0.0.1") -> Optional[Any]:
    """Send the editor's downloads to `download_dir` instead of Downloads.

    The editor's export dialog saves a ZIP through an ordinary browser download.
    Polluting (and polling) the user's Downloads folder is the most fragile part
    of the export path: partial `.crdownload` files, name collisions with
    earlier exports, and downloads that never appear where we look. Redirecting
    the page removes all three; when it cannot be applied, callers still fall
    back to scanning the default Downloads folder.

    Returns the CDP socket that carries the setting, or None when the redirect
    could not be applied. **The caller must keep it open for the whole export
    and close it afterwards**: closing the connection discards the behavior, so
    a "set and forget" implementation silently does nothing.
    """
    try:
        cdp_url = browser_cdp_url(browser)
        socket = cdp_connect(cdp_url)
        try:
            targets = cdp_call(socket, 1, "Target.getTargets", {}).get("targetInfos", [])
            pages = [
                target
                for target in targets
                if target.get("type") == "page" and url_hint in str(target.get("url", ""))
            ]
            target = pages[0] if pages else next(
                (item for item in targets if item.get("type") == "page"), None
            )
            if target is None:
                raise ExportError("no browser page target to redirect downloads for")
            attached = cdp_call(
                socket,
                2,
                "Target.attachToTarget",
                {"targetId": target["targetId"], "flatten": True},
            )
            cdp_call(
                socket,
                3,
                "Page.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": str(download_dir)},
                attached.get("sessionId"),
            )
        except Exception:
            socket.close()
            raise
        log(f"browser downloads are redirected to {download_dir}")
        return socket
    except Exception as error:  # noqa: BLE001 - keep the Downloads fallback working
        log(f"note: could not redirect downloads ({error}); using the default Downloads folder")
        return None


class BrowserSession:
    def __init__(
        self,
        executable: str,
        session: str,
        cwd: Path,
        download_dir: Path,
        cdp_port: Optional[int] = None,
    ):
        self.executable = executable
        self.session = session
        self.cwd = cwd
        # Kept as a search root fallback; not passed to agent-browser. On Windows,
        # --download-path can be rewritten to a \\?\ path that cancels Chrome downloads.
        self.download_dir = download_dir
        self.env = os.environ.copy()
        self.env.setdefault("AGENT_BROWSER_DEFAULT_TIMEOUT", "60000")
        self.env.setdefault("AGENT_BROWSER_IDLE_TIMEOUT_MS", "180000")
        # Local editor host is 127.0.0.1; corporate HTTP(S)_PROXY would otherwise
        # intercept and 403 the offline export page. Same canonical list that
        # cdp_connect() strips, so the two cannot drift apart again.
        for key in PROXY_ENV_KEYS:
            self.env.pop(key, None)
        no_proxy = self.env.get("NO_PROXY") or self.env.get("no_proxy") or ""
        parts = {p.strip() for p in no_proxy.split(",") if p.strip()}
        parts.update({"127.0.0.1", "localhost", "::1"})
        joined = ",".join(sorted(parts))
        self.env["NO_PROXY"] = joined
        self.env["no_proxy"] = joined
        if cdp_port is not None:
            self.env["AGENT_BROWSER_CDP"] = str(cdp_port)

    def run(
        self,
        args: Sequence[str],
        *,
        timeout: int = 90,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        command = [self.executable, "--session", self.session, *args]
        process = run_command(command, cwd=self.cwd, env=self.env, timeout=timeout)
        if check and process.returncode != 0:
            raise ExportError(
                f"agent-browser command failed ({process.returncode}): "
                f"{' '.join(args)}\n{process.stdout[-4000:]}"
            )
        return process

    def open(self, url: str) -> None:
        # Avoid --download-path: agent-browser ≤0.33.2 + Chrome may cancel downloads
        # when given a verbatim Windows path. Files land in the default Downloads folder.
        self.run(["open", url], timeout=90)

    def snapshot(self) -> Dict[str, Any]:
        process = self.run(["snapshot", "-i", "-C", "--json"])
        return json_result(process.stdout)

    def close(self) -> None:
        self.run(["close"], timeout=20, check=False)


def snapshot_data(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    data = snapshot.get("data")
    if not isinstance(data, dict):
        raise ExportError(f"invalid agent-browser snapshot: {snapshot}")
    return data


def ref_by_name(snapshot: Dict[str, Any], name: str, role: Optional[str] = None) -> str:
    refs = snapshot_data(snapshot).get("refs")
    if not isinstance(refs, dict):
        raise ExportError("snapshot contains no interactive refs")
    matches = []
    for ref, metadata in refs.items():
        if not isinstance(metadata, dict) or metadata.get("name") != name:
            continue
        if role is not None and str(metadata.get("role", "")).lower() != role.lower():
            continue
        matches.append(ref)
    if not matches:
        raise ExportError(f"could not find {role or 'element'} named {name!r}")
    return matches[-1]


def switch_state(snapshot: Dict[str, Any]) -> Optional[Tuple[str, bool, bool]]:
    text = str(snapshot_data(snapshot).get("snapshot") or "")
    match = re.search(r"switch \[(?P<attrs>[^\]]*?)ref=(?P<ref>e\d+)\]", text)
    if not match:
        return None
    attrs = match.group("attrs")
    return match.group("ref"), "checked=true" in attrs, "disabled" in attrs


# The editor reports in-flight project/media fetches on this global; when the
# host serves media over HTTP (instead of inlining it into payload.json) the deck
# is "ready" before its images have arrived, and driving the UI too early loses
# them.
EDITOR_PENDING_FETCHES_JS = (
    "!(window.__NEODECK_PENDING_PROJECT_FETCHES__) || "
    "window.__NEODECK_PENDING_PROJECT_FETCHES__() === 0"
)


def wait_for_editor_media(browser: BrowserSession, timeout: float = 60.0) -> None:
    """Wait until the editor has fetched every media file it is going to."""
    try:
        browser.run(["wait", "--fn", EDITOR_PENDING_FETCHES_JS], timeout=timeout)
    except ExportError as error:
        raise ExportError(
            f"the editor is still loading media after {timeout:.0f}s; "
            "the render may be incomplete"
        ) from error


def open_export_dialog(browser: BrowserSession, timeout: float = 20.0) -> Dict[str, Any]:
    """Click 导出 and wait for the export dialog, retrying the click once.

    The editor's toolbar can swallow a click while it is still settling after a
    deck load (seen when a stale agent-browser session was attached to the
    browser). Re-snapshotting and clicking again after a short settle is much
    cheaper than failing the whole export.
    """
    last_error: Optional[Exception] = None
    for attempt in (1, 2):
        try:
            snapshot = browser.snapshot()
            export_ref = ref_by_name(snapshot, "导出", "button")
            browser.run(["click", f"@{export_ref}"])
            return wait_for_export_dialog(browser, timeout=timeout)
        except ExportError as error:
            last_error = error
            if attempt == 2:
                break
            time.sleep(1.0)
    raise last_error if last_error else ExportError("could not open the export dialog")


def wait_for_export_dialog(browser: BrowserSession, timeout: float = 20.0) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: Optional[Dict[str, Any]] = None
    while time.monotonic() < deadline:
        last = browser.snapshot()
        try:
            ref_by_name(last, "下载", "button")
            return last
        except ExportError:
            time.sleep(0.35)
    raise ExportError(f"export dialog did not become ready: {last}")


def is_pptx(path: Path) -> bool:
    if not path.is_file() or path.name.endswith(".crdownload"):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            if "ppt/presentation.xml" not in archive.namelist():
                return False
            content_types = archive.read("[Content_Types].xml")
            return PPTX_CONTENT_TYPE.encode("utf-8") in content_types
    except (OSError, KeyError, zipfile.BadZipFile):
        return False


def find_download(
    search_roots: Iterable[Path],
    timeout: float = 150.0,
    accept: Callable[[Path], bool] = is_pptx,
    *,
    since: Optional[float] = None,
) -> Path:
    deadline = time.monotonic() + timeout
    last_sizes: Dict[Path, int] = {}
    stable: Dict[Path, int] = {}
    while time.monotonic() < deadline:
        # Snapshot stats while collecting and tolerate races everywhere: the
        # search roots include the live Downloads folder, where Chrome renames
        # .crdownload files away between directory listing and stat().
        entries: List[Tuple[Path, float, int]] = []
        for root in search_roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                try:
                    info = path.stat()
                except OSError:
                    continue
                entries.append((path, info.st_mtime, info.st_size))
        for path, mtime, size in sorted(entries, key=lambda entry: entry[1], reverse=True):
            if since is not None and mtime < since:
                continue
            if size == last_sizes.get(path) and size > 0:
                stable[path] = stable.get(path, 0) + 1
            else:
                stable[path] = 0
            last_sizes[path] = size
            if stable[path] >= 1 and accept(path):
                return path
        time.sleep(0.5)
    visible = "\n  ".join(str(path) for path in last_sizes) or "(none)"
    raise ExportError(f"timed out waiting for download; observed files:\n  {visible}")


def replace_transition(slide_xml: bytes, transition: str) -> bytes:
    text = slide_xml.decode("utf-8")
    pattern = re.compile(
        r"<p:transition\b[^>]*(?:/>|>.*?</p:transition>)", re.DOTALL
    )
    text = pattern.sub("", text)
    if transition == "none":
        return text.encode("utf-8")

    # CT_Slide requires transition as a direct child after cSld/clrMapOvr and
    # before timing/extLst. Searching for the first p:extLst is incorrect:
    # shapes may contain their own nested extLst inside cSld, causing Office to
    # ignore a transition inserted there.
    color_map = re.search(
        r"<p:clrMapOvr\b[^>]*(?:/>|>.*?</p:clrMapOvr>)", text, re.DOTALL
    )
    common_slide = re.search(
        r"<p:cSld\b[^>]*(?:/>|>.*?</p:cSld>)", text, re.DOTALL
    )
    anchor = color_map or common_slide
    if anchor is None:
        raise ExportError("slide XML has no cSld/clrMapOvr insertion anchor")
    position = anchor.end()
    return (text[:position] + FADE_TRANSITION_XML + text[position:]).encode("utf-8")


def root_child_names(slide_xml: bytes) -> List[str]:
    try:
        root = ET.fromstring(slide_xml)
    except ET.ParseError as exc:
        raise ExportError(f"invalid slide XML: {exc}") from exc
    return [child.tag.rsplit("}", 1)[-1] for child in root]


def has_direct_fade_transition(slide_xml: bytes) -> bool:
    try:
        root = ET.fromstring(slide_xml)
    except ET.ParseError as exc:
        raise ExportError(f"invalid slide XML: {exc}") from exc
    transition = next(
        (child for child in root if child.tag.rsplit("}", 1)[-1] == "transition"),
        None,
    )
    if transition is None:
        return False
    return any(child.tag.rsplit("}", 1)[-1] == "fade" for child in transition)


def validate_transition_order(slide_xml: bytes, transition: str) -> None:
    names = root_child_names(slide_xml)
    transition_indexes = [index for index, name in enumerate(names) if name == "transition"]
    if transition == "none":
        if transition_indexes:
            raise ExportError("transition=none left a root-level transition")
        return
    if len(transition_indexes) != 1 or not has_direct_fade_transition(slide_xml):
        raise ExportError("slide does not contain exactly one root-level fade transition")
    transition_index = transition_indexes[0]
    for required_before in ("cSld", "clrMapOvr"):
        if required_before in names and names.index(required_before) > transition_index:
            raise ExportError(f"{required_before} appears after transition")
    for required_after in ("timing", "extLst"):
        if required_after in names and names.index(required_after) < transition_index:
            raise ExportError(f"{required_after} appears before transition")


def patch_transitions(pptx: Path, transition: str) -> int:
    temporary = pptx.with_name(f".{pptx.name}.{uuid.uuid4().hex}.tmp")
    slide_count = 0
    try:
        with zipfile.ZipFile(pptx, "r") as source, zipfile.ZipFile(temporary, "w") as target:
            target.comment = source.comment
            for info in source.infolist():
                data = source.read(info.filename)
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", info.filename):
                    data = replace_transition(data, transition)
                    slide_count += 1
                target.writestr(info, data, compress_type=info.compress_type)
        if slide_count == 0:
            raise ExportError("exported PPTX contains no slide XML")
        temporary.replace(pptx)
    finally:
        temporary.unlink(missing_ok=True)
    return slide_count


def verify_output(pptx: Path, transition: str, expect_fonts: bool) -> Dict[str, Any]:
    if not is_pptx(pptx):
        raise ExportError(f"output is not a valid PPTX ZIP: {pptx}")
    with zipfile.ZipFile(pptx) as archive:
        broken = archive.testzip()
        if broken:
            raise ExportError(f"PPTX CRC check failed at: {broken}")
        slide_names = [
            name
            for name in archive.namelist()
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        ]
        slide_xml = {name: archive.read(name) for name in slide_names}
        for data in slide_xml.values():
            validate_transition_order(data, transition)
        transition_hits = sum(has_direct_fade_transition(data) for data in slide_xml.values())
        if transition == "fade" and transition_hits != len(slide_names):
            raise ExportError("fade transition was not written to every slide")
        fonts = [
            name
            for name in archive.namelist()
            if name.startswith("ppt/fonts/") and not name.endswith("/")
        ]
        if expect_fonts and not fonts:
            log(
                "warning: embed-fonts was enabled, but the official writer produced no font part"
            )
        return {
            "slides": len(slide_names),
            "fadeTransitions": transition_hits,
            "fontParts": len(fonts),
            "bytes": pptx.stat().st_size,
        }


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
