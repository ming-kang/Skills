import sys
from pathlib import Path

import pytest


def find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "docx" / "scripts").exists():
            return parent
    raise RuntimeError("repo root not found")


REPO_ROOT = find_repo_root()
sys.path.insert(0, str(REPO_ROOT / "docx" / "scripts"))

from docx_lib.workspace import DOCX_KEEP_WORKSPACE_ENV, create_runtime_workspace


def test_create_runtime_workspace_uses_task_visible_defaults(tmp_path: Path):
    root_dir = None

    with create_runtime_workspace("validate", base_dir=tmp_path) as workspace:
        root_dir = workspace.root_dir
        assert workspace.contract.task_root == tmp_path
        assert workspace.contract.work_root == tmp_path / ".docx-tmp"
        assert workspace.root_dir.parent == tmp_path / ".docx-tmp"
        assert workspace.root_dir.name.startswith("docx-validate-")
        assert workspace.work_dir == workspace.root_dir
        assert workspace.work_dir.exists()

    assert root_dir is not None
    assert not root_dir.exists()


def test_create_runtime_workspace_supports_nested_contents_dir(tmp_path: Path):
    with create_runtime_workspace(
        "validate",
        base_dir=tmp_path,
        contents_dir="extracted",
    ) as workspace:
        assert workspace.work_dir == workspace.root_dir / "extracted"
        assert workspace.work_dir.exists()


def test_keep_workspace_env_preserves_successful_runs(tmp_path: Path):
    env = {DOCX_KEEP_WORKSPACE_ENV: "1"}

    with create_runtime_workspace("edit", base_dir=tmp_path, env=env) as workspace:
        root_dir = workspace.root_dir

    assert root_dir.exists()


def test_failed_runs_are_preserved_by_default(tmp_path: Path):
    root_dir = None

    with pytest.raises(RuntimeError):
        with create_runtime_workspace("edit", base_dir=tmp_path) as workspace:
            root_dir = workspace.root_dir
            raise RuntimeError("expected failure")

    assert root_dir is not None
    assert root_dir.exists()
