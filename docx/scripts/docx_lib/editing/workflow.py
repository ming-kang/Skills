"""Recommended editing workflow helpers built on top of DocxContext."""

from __future__ import annotations

from pathlib import Path

from ..preflight import PreflightResult, preflight_docx
from .context import DocxContext, InvalidDocxError


def default_edited_output_path(input_path: str | Path) -> Path:
    source = Path(input_path)
    suffix = source.suffix or ".docx"
    return source.with_name(f"{source.stem}-edited{suffix}")


def _format_preflight_failure(input_path: Path, result: PreflightResult) -> str:
    lines = [
        f"Editing preflight failed for {input_path}.",
        "Fix the package before opening it with DocxContext.",
    ]

    if result.workspace_root is not None:
        lines.append(f"Inspect preserved preflight workspace: {result.workspace_root}")

    if result.errors:
        lines.append(f"Preflight errors: {'; '.join(result.errors)}")

    lines.append(
        "Run `docx preflight <file.docx>` directly if you want the standalone normalization/debugging step."
    )
    return " ".join(lines)


def edit_docx(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    preflight: bool = False,
    task_root: str | Path | None = None,
    work_root: str | Path | None = None,
    keep_workspace: bool | None = None,
    keep_failed_workspace: bool = True,
) -> DocxContext:
    """
    Return a DocxContext using the recommended local-first defaults.

    When `output_path` is omitted, the edited file is written beside the source
    using the `<name>-edited.docx` convention. When `preflight=True`, incoming
    documents are normalized first and invalid packages fail with actionable
    guidance before the editing workspace is created.
    """

    source = Path(input_path)
    target = Path(output_path) if output_path is not None else default_edited_output_path(source)

    preflight_result = None
    if preflight:
        preflight_result = preflight_docx(source)
        if preflight_result.status == "invalid":
            raise InvalidDocxError(_format_preflight_failure(source, preflight_result))

    ctx = DocxContext(
        str(source),
        str(target),
        task_root=task_root,
        work_root=work_root,
        keep_workspace=keep_workspace,
        keep_failed_workspace=keep_failed_workspace,
    )
    ctx.preflight_result = preflight_result
    return ctx


__all__ = ["default_edited_output_path", "edit_docx"]
