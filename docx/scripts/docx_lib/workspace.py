"""
workspace.py - Shared visible workspace helpers for Python runtime flows.

This module freezes the Phase 1 contract for Python-side task/workspace handling:

- task root: `DOCX_TASK_ROOT` when set, otherwise the current working directory
- work root: `DOCX_WORK_ROOT` when set, otherwise `<task-root>/.docx-tmp`
- Windows Git Bash `/c/...` task/work-root inputs normalize to native absolute paths
- workspace naming: `docx-<purpose>-<timestamp>-<pid>[-N]`
- successful runs clean up by default unless `DOCX_KEEP_WORKSPACE=1`
- failed runs are preserved by default for debugging
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping


DOCX_TASK_ROOT_ENV = "DOCX_TASK_ROOT"
DOCX_WORK_ROOT_ENV = "DOCX_WORK_ROOT"
DOCX_KEEP_WORKSPACE_ENV = "DOCX_KEEP_WORKSPACE"

DEFAULT_WORK_ROOT_NAME = ".docx-tmp"
DEFAULT_WORKSPACE_PREFIX = "docx"
DEFAULT_KEEP_FAILURE = True

_WORKSPACE_LABEL_RE = re.compile(r"[^a-z0-9]+")
_WINDOWS_GIT_BASH_ABS_RE = re.compile(r"^/([a-zA-Z])(?:/(.*))?$")


def _get_env(env: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if env is None else env


def normalize_rooted_input_path(
    raw_path: str | Path,
    *,
    platform: str | None = None,
) -> str:
    path = os.path.expanduser(str(raw_path))
    current_platform = os.name if platform is None else platform

    if current_platform == "nt":
        normalized = path.replace("\\", "/")
        match = _WINDOWS_GIT_BASH_ABS_RE.fullmatch(normalized)
        if match is not None:
            drive = match.group(1).upper()
            remainder = match.group(2)
            if remainder:
                return f"{drive}:/{remainder}"
            return f"{drive}:/"

    return path


def _resolve_rooted_path(raw_path: str | Path, base_path: Path) -> Path:
    path = Path(normalize_rooted_input_path(raw_path))
    if path.is_absolute():
        return path
    return base_path / path


def normalize_workspace_label(label: str) -> str:
    normalized = _WORKSPACE_LABEL_RE.sub("-", label.strip().lower()).strip("-")
    return normalized or "run"


def resolve_task_root(
    task_root: str | Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
    base_dir: str | Path | None = None,
) -> Path:
    """
    Resolve the visible task root for Python runtime flows.

    Relative overrides are interpreted relative to the current working directory
    (or the provided `base_dir`) to match the CLI contract.
    """
    env_map = _get_env(env)
    base_path = Path.cwd() if base_dir is None else Path(base_dir)

    if task_root is None:
        raw_path = env_map.get(DOCX_TASK_ROOT_ENV)
        if raw_path:
            return _resolve_rooted_path(raw_path, base_path)
        return base_path

    return _resolve_rooted_path(task_root, base_path)


def resolve_work_root(
    *,
    task_root: str | Path | None = None,
    work_root: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    base_dir: str | Path | None = None,
) -> Path:
    """
    Resolve the visible work root for Python runtime flows.

    Relative `DOCX_WORK_ROOT` values remain task-root-relative, matching the
    Bash CLI behavior.
    """
    env_map = _get_env(env)
    resolved_task_root = resolve_task_root(task_root, env=env_map, base_dir=base_dir)

    if work_root is None:
        raw_path = env_map.get(DOCX_WORK_ROOT_ENV, DEFAULT_WORK_ROOT_NAME)
    else:
        raw_path = work_root

    return _resolve_rooted_path(raw_path, resolved_task_root)


def should_keep_successful_workspace(
    keep_success: bool | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> bool:
    if keep_success is not None:
        return keep_success
    return _get_env(env).get(DOCX_KEEP_WORKSPACE_ENV) == "1"


def _workspace_name(purpose: str, *, prefix: str = DEFAULT_WORKSPACE_PREFIX) -> str:
    label = normalize_workspace_label(purpose)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{label}-{timestamp}-{os.getpid()}"


def _create_unique_workspace_root(
    work_root: Path,
    purpose: str,
    *,
    prefix: str = DEFAULT_WORKSPACE_PREFIX,
) -> Path:
    work_root.mkdir(parents=True, exist_ok=True)
    stem = _workspace_name(purpose, prefix=prefix)

    counter = 1
    while True:
        name = stem if counter == 1 else f"{stem}-{counter}"
        candidate = work_root / name
        try:
            candidate.mkdir(parents=False, exist_ok=False)
            return candidate
        except FileExistsError:
            counter += 1


@dataclass(frozen=True)
class WorkspaceContract:
    task_root: Path
    work_root: Path
    keep_success: bool
    keep_failure: bool = DEFAULT_KEEP_FAILURE


@dataclass
class RuntimeWorkspace:
    purpose: str
    contract: WorkspaceContract
    root_dir: Path
    work_dir: Path
    cleaned: bool = False

    def retain(self) -> None:
        self.contract = WorkspaceContract(
            task_root=self.contract.task_root,
            work_root=self.contract.work_root,
            keep_success=True,
            keep_failure=True,
        )

    def cleanup(self, *, success: bool) -> bool:
        keep_workspace = self.contract.keep_success if success else self.contract.keep_failure
        if keep_workspace or self.cleaned or not self.root_dir.exists():
            return False

        shutil.rmtree(self.root_dir)
        self.cleaned = True
        # Remove empty work_root if no other workspaces remain
        try:
            work_root = self.contract.work_root
            if work_root.exists() and work_root.is_dir() and not any(work_root.iterdir()):
                work_root.rmdir()
        except Exception:
            pass
        return True

    def __enter__(self) -> "RuntimeWorkspace":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.cleanup(success=exc_type is None)
        return False


def resolve_workspace_contract(
    *,
    task_root: str | Path | None = None,
    work_root: str | Path | None = None,
    keep_success: bool | None = None,
    keep_failure: bool = DEFAULT_KEEP_FAILURE,
    env: Mapping[str, str] | None = None,
    base_dir: str | Path | None = None,
) -> WorkspaceContract:
    env_map = _get_env(env)
    return WorkspaceContract(
        task_root=resolve_task_root(task_root, env=env_map, base_dir=base_dir),
        work_root=resolve_work_root(
            task_root=task_root,
            work_root=work_root,
            env=env_map,
            base_dir=base_dir,
        ),
        keep_success=should_keep_successful_workspace(keep_success, env=env_map),
        keep_failure=keep_failure,
    )


def create_runtime_workspace(
    purpose: str,
    *,
    task_root: str | Path | None = None,
    work_root: str | Path | None = None,
    keep_success: bool | None = None,
    keep_failure: bool = DEFAULT_KEEP_FAILURE,
    env: Mapping[str, str] | None = None,
    base_dir: str | Path | None = None,
    contents_dir: str | None = None,
    prefix: str = DEFAULT_WORKSPACE_PREFIX,
) -> RuntimeWorkspace:
    """
    Create a visible per-run workspace under the configured work root.

    `contents_dir` lets callers keep a stable subdirectory such as `extracted`
    while still preserving the run root for debugging.
    """
    contract = resolve_workspace_contract(
        task_root=task_root,
        work_root=work_root,
        keep_success=keep_success,
        keep_failure=keep_failure,
        env=env,
        base_dir=base_dir,
    )
    root_dir = _create_unique_workspace_root(contract.work_root, purpose, prefix=prefix)
    work_dir = root_dir if contents_dir is None else root_dir / contents_dir
    work_dir.mkdir(parents=True, exist_ok=True)

    return RuntimeWorkspace(
        purpose=purpose,
        contract=contract,
        root_dir=root_dir,
        work_dir=work_dir,
    )
