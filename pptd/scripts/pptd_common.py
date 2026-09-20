#!/usr/bin/env python3
"""Shared plumbing for the pptd export scripts.

Everything here is dependency-free standard library: process running with
UTF-8-safe capture, temp-directory helpers, on-demand pip installs, and the
one canonical list of proxy environment variables. The export scripts
(``export_pptx.py``, ``export_images.py``, ``clean_processes.py``) import from
this module instead of growing private copies of the same helpers.
"""

from __future__ import annotations

import importlib
import os
import site
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Sequence


class ExportError(RuntimeError):
    pass


# The skill root (scripts/..), shared by every module that resolves paths
# relative to it — one definition so the modules cannot drift apart.
SKILL_DIR = Path(__file__).resolve().parent.parent


class LocalExportUnavailable(ExportError):
    """The local WASM toolchain itself is missing.

    Only this narrow class is allowed to trigger the browser fallback: a
    malformed deck or an existing output file must surface as-is instead of
    quietly pulling in agent-browser and a Chromium download.
    """


def log(message: str) -> None:
    print(f"[pptd] {message}", file=sys.stderr, flush=True)


def run_command(
    command: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: int = 90,
) -> subprocess.CompletedProcess:
    """Capture merged stdout/stderr via a temp file.

    On Windows, agent-browser's detached daemon can inherit a PIPE handle and
    prevent EOF, deadlocking ``subprocess.run(stdout=PIPE)``. Decoding with the
    system locale (GBK on zh-CN Windows) can also raise UnicodeDecodeError.
    Writing to a UTF-8 file avoids both failures.
    """
    handle, sink_path = tempfile.mkstemp(prefix="pptd-", suffix=".log")
    os.close(handle)
    sink = Path(sink_path)
    output = ""
    try:
        with sink.open("w", encoding="utf-8", errors="replace") as out:
            returncode = subprocess.call(
                list(command),
                cwd=str(cwd) if cwd is not None else None,
                env=env,
                stdout=out,
                stderr=subprocess.STDOUT,
                timeout=timeout,
            )
        output = sink.read_text(encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired as exc:
        try:
            output = sink.read_text(encoding="utf-8", errors="replace")
        except OSError:
            output = ""
        raise subprocess.TimeoutExpired(
            cmd=list(command),
            timeout=timeout,
            output=output,
        ) from exc
    finally:
        try:
            sink.unlink(missing_ok=True)
        except OSError:
            # WinError 32: daemon may still hold the log file handle.
            pass
    return subprocess.CompletedProcess(list(command), returncode, output, None)


def temporary_directory(prefix: str) -> Any:
    # ignore_cleanup_errors avoids masking the real export error when a Windows
    # browser daemon still holds files under the temp tree (Python 3.10+).
    try:
        return tempfile.TemporaryDirectory(prefix=prefix, ignore_cleanup_errors=True)
    except TypeError:
        return tempfile.TemporaryDirectory(prefix=prefix)


def default_downloads_dir() -> Path:
    home = Path.home()
    candidates = []
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        candidates.append(Path(user_profile) / "Downloads")
    candidates.extend((home / "Downloads", home / "下载"))
    for path in candidates:
        if path.is_dir():
            return path
    return home / "Downloads"


def ensure_module(import_name: str, pip_name: str, purpose: str) -> Any:
    """Import ``import_name``, installing ``pip_name`` with pip --user on demand.

    The one implementation of the skill's "install a Python dependency at
    runtime" pattern (previously three near-identical copies). Lazy on purpose:
    importing this module must not run pip. After a --user install the new site
    directory is usually absent from sys.path (CPython only adds it when it
    exists at startup), so register it explicitly before retrying the import.
    """
    try:
        return importlib.import_module(import_name)
    except ImportError:
        pass
    log(f"{purpose}; installing {pip_name} with pip --user")
    process = run_command(
        [sys.executable, "-m", "pip", "install", "--user", pip_name],
        timeout=300,
    )
    if process.returncode != 0:
        raise ExportError(
            f"failed to install {pip_name} with pip --user:\n"
            f"{process.stdout[-2000:]}\n"
            f"Install it manually with: {sys.executable} -m pip install --user {pip_name}"
        )
    try:
        user_site = site.getusersitepackages()
    except AttributeError:  # pragma: no cover - non-standard site module
        user_site = None
    if isinstance(user_site, str) and os.path.isdir(user_site):
        site.addsitedir(user_site)
    importlib.invalidate_caches()
    try:
        return importlib.import_module(import_name)
    except ImportError as exc:
        raise ExportError(
            f"{pip_name} was installed but is still not importable; "
            f"restart the export or install it into {sys.executable} manually"
        ) from exc


# The one canonical list of proxy variables. Local endpoints (the editor host,
# the CDP browser) must never be tunneled through a corporate proxy, so every
# place that touches them strips exactly these keys — previously two hand-
# maintained lists that had already drifted apart (socks5 was missing from one).
PROXY_ENV_KEYS = (
    "http_proxy",
    "https_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "all_proxy",
    "ALL_PROXY",
    "socks5_proxy",
    "SOCKS5_PROXY",
)
