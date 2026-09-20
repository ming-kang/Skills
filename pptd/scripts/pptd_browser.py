#!/usr/bin/env python3
"""Browser automation for the optional pptd export paths.

Three layers live here:

* **Toolchain bootstrap** — ensuring Node.js and agent-browser exist (and are
  new enough), installing them on demand. The default PPTX export path never
  reaches this module; only the optional --browser path and image QA do.
* **Debug browser lifecycle** (Windows) — agent-browser cannot launch Chrome
  itself on Windows, so the export drives an externally started browser over
  CDP. Every browser this module starts is registered with a signature (our
  own profile directory + the pid's command line) and reclaimed after an idle
  period, so an interrupted export cannot leak a browser forever. Browsers
  the user pointed us at via AGENT_BROWSER_CDP are never registered, never
  touched.
* **UI driving** — the agent-browser session, CDP plumbing, download
  redirection and the export-dialog interactions.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from pptd_common import (
    PROXY_ENV_KEYS,
    ExportError,
    default_downloads_dir,
    ensure_module,
    log,
    run_command,
    temporary_directory,
)
from pptd_editor_host import EditorHost
from pptd_pptx import is_pptx

MIN_AGENT_BROWSER_VERSION = (0, 33, 2)
MIN_NODE_MAJOR = 18
NODE_INSTALL_HINT = "Install Node.js 18+ from https://nodejs.org, then retry."


def parse_version(output: str) -> Tuple[int, int, int]:
    """First ``major.minor.patch`` in ``output``; the ``v`` prefix is optional.

    One parser for both version probes: agent-browser prints "agent-browser
    0.33.2", Node prints "v22.11.0".
    """
    match = re.search(r"v?(\d+)\.(\d+)\.(\d+)\b", output)
    if not match:
        raise ExportError(f"could not parse version from: {output.strip()}")
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

    version = parse_version(process.stdout)
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


class EditorExportSession:
    """One driven editor-export run.

    Wraps the setup/teardown both browser paths (PPTX export and image QA)
    share — opening the editor page, redirecting downloads out of the user's
    Downloads folder, waiting for the deck *and* its host-served media, and
    shutting everything down in the right order — so the callers only drive
    their export dialog and read the downloaded file.

    Used as a context manager; the downloaded file only lives until the
    session exits, so consume it inside the ``with`` block.
    """

    def __init__(
        self,
        agent_browser: str,
        host: EditorHost,
        *,
        session_prefix: str,
        cdp_port: Optional[int] = None,
    ) -> None:
        self.host = host
        self.temporary = temporary_directory(prefix=f"{session_prefix}-")
        self.temp_dir = Path(self.temporary.name)
        self.download_dir = self.temp_dir / "downloads"
        self.download_dir.mkdir()
        # Kept as a search root: Chrome may still save to the default folder
        # when the redirect could not be applied.
        self.downloads = default_downloads_dir()
        self.browser = BrowserSession(
            agent_browser,
            f"{session_prefix}-{os.getpid()}-{uuid.uuid4().hex[:8]}",
            self.temp_dir,
            self.download_dir,
            cdp_port,
        )
        self._redirect = None
        log("opening the local neo-ppt editor")
        self.browser.open(host.url)
        # Keep the export ZIP out of the user's Downloads folder. The socket
        # must stay open until the download finished (see set_download_behavior).
        self._redirect = set_download_behavior(self.browser, self.download_dir)
        self.browser.run(
            [
                "wait",
                "--fn",
                'document.documentElement.dataset.deckStatus === "ready"',
            ],
            timeout=120,
        )
        # "ready" precedes the media fetches the host-served images need.
        wait_for_editor_media(self.browser)
        self.browser.run(["set", "viewport", "1280", "720"])

    def download_from_dialog(
        self,
        dialog: Dict[str, Any],
        *,
        accept: Callable[[Path], bool] = is_pptx,
        click_timeout: int = 180,
        find_timeout: float = 90.0,
    ) -> Path:
        """Click the dialog's 下载 button and wait for the resulting file."""
        started_at = time.time() - 1.0
        download_ref = ref_by_name(dialog, "下载", "button")
        self.browser.run(["click", f"@{download_ref}"], timeout=click_timeout)
        return find_download(
            (self.downloads, self.download_dir, self.temp_dir),
            timeout=find_timeout,
            accept=accept,
            since=started_at,
        )

    def close(self) -> None:
        self.browser.close()
        if self._redirect is not None:
            try:
                self._redirect.close()
            except Exception:  # noqa: BLE001 - the export is already done
                pass
        self.host.shutdown()
        self.temporary.cleanup()

    def __enter__(self) -> "EditorExportSession":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()


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


