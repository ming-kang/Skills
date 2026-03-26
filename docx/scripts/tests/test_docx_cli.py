import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "docx" / "scripts" / "docx"
BASH_CANDIDATES = [
    os.environ.get("DOCX_TEST_BASH"),
    shutil.which("bash"),
    r"C:\Program Files\Git\bin\bash.exe",
]


def find_bash():
    for candidate in BASH_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    return None


BASH = find_bash()

if BASH is None:
    pytestmark = pytest.mark.skip(reason="Git Bash is required for docx CLI tests")


def run_cli(task_dir: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    return subprocess.run(
        [BASH, str(SCRIPT_PATH), *args],
        cwd=task_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=full_env,
        check=False,
    )


def assert_ok(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, (
        f"command failed with exit code {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def run_python(script: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def test_init_build_validate_roundtrip(tmp_path: Path):
    task_dir = tmp_path / "task"
    task_dir.mkdir()

    init_result = run_cli(task_dir, "init")
    assert_ok(init_result)
    assert (task_dir / ".docx" / "Program.cs").exists()
    assert (task_dir / ".docx" / "KimiDocx.csproj").exists()

    build_result = run_cli(task_dir, "build")
    assert_ok(build_result)
    assert (task_dir / "output.docx").exists()

    work_root = task_dir / ".docx-tmp"
    assert work_root.exists()
    assert list(work_root.glob("docx-task-*")) == []

    validate_result = run_cli(task_dir, "validate", "output.docx")
    assert_ok(validate_result)
    assert "Validation passed" in validate_result.stdout


def test_build_uses_unique_default_output_names(tmp_path: Path):
    task_dir = tmp_path / "task"
    task_dir.mkdir()

    assert_ok(run_cli(task_dir, "init"))
    assert_ok(run_cli(task_dir, "build"))
    assert_ok(run_cli(task_dir, "build"))

    assert (task_dir / "output.docx").exists()
    assert (task_dir / "output-2.docx").exists()


def test_keep_workspace_preserves_successful_temp_workspace(tmp_path: Path):
    task_dir = tmp_path / "task"
    task_dir.mkdir()

    assert_ok(run_cli(task_dir, "init"))
    assert_ok(run_cli(task_dir, "build", env={"DOCX_KEEP_WORKSPACE": "1"}))

    workspaces = list((task_dir / ".docx-tmp").glob("docx-task-*"))
    assert len(workspaces) == 1


def test_env_reports_workspace_contract_for_build_validate_and_edit(tmp_path: Path):
    task_dir = tmp_path / "task"
    task_dir.mkdir()

    result = run_cli(task_dir, "env")
    assert_ok(result)

    assert "=== Workspace Contract ===" in result.stdout
    assert "Build workspaces:" in result.stdout
    assert "docx-task-*" in result.stdout
    assert "Python validate/fix:" in result.stdout
    assert "docx-validate-all-*" in result.stdout
    assert "Python edit:" in result.stdout
    assert "docx-edit-*" in result.stdout
    assert "Editing overrides:" in result.stdout
    assert "keep_failed_workspace" in result.stdout


def test_help_mentions_editing_workspace_overrides(tmp_path: Path):
    task_dir = tmp_path / "task"
    task_dir.mkdir()

    result = run_cli(task_dir, "help")
    assert_ok(result)

    assert "Python Editing Runtime:" in result.stdout
    assert "DocxContext(input, output) keeps working unchanged." in result.stdout
    assert "task_root=..." in result.stdout
    assert "work_root=..." in result.stdout
    assert "keep_workspace=True|False" in result.stdout
    assert "keep_failed_workspace=True|False" in result.stdout


def test_edit_workflow_output_passes_validator(tmp_path: Path):
    task_dir = tmp_path / "task"
    task_dir.mkdir()

    assert_ok(run_cli(task_dir, "init"))
    assert_ok(run_cli(task_dir, "build"))

    edit_script = f"""
from pathlib import Path
import sys

repo = Path(r"{REPO_ROOT}")
sys.path.insert(0, str(repo / "docx" / "scripts"))

from docx_lib.editing import DocxContext, enable_track_changes, insert_text

source = Path(r"{task_dir / 'output.docx'}")
output = Path(r"{task_dir / 'output-edited.docx'}")

with DocxContext(str(source), str(output)) as ctx:
    enable_track_changes(ctx)
    insert_text(
        ctx,
        "KimiDocx local template generated this placeholder document.",
        after="placeholder",
        new_text=" locally",
    )
"""

    edit_result = run_python(edit_script, REPO_ROOT)
    assert_ok(edit_result)
    assert (task_dir / "output-edited.docx").exists()

    validate_result = run_cli(task_dir, "validate", "output-edited.docx")
    assert_ok(validate_result)
