"""
preflight.py - Shared template/input preflight and normalization helpers.

Preflight distinguishes three result classes:
  - clean: no fixes needed and no unrecoverable validation errors
  - fixable: normalization fixes were applied and the input is otherwise valid
  - invalid: unrecoverable validation errors remain; the source file is untouched
"""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from .business_rules import (
    check_comments_integrity,
    check_document_settings,
    check_image_aspect_ratio,
    check_section_margins,
    check_table_grid_consistency,
)
from .element_order import (
    fix_element_order_in_tree,
    fix_settings,
    fix_table_width_conservative,
)
from .workspace import create_runtime_workspace


@dataclass(frozen=True)
class PreflightResult:
    status: str
    fixes: int
    errors: list[str]
    warnings: list[str]
    applied_fixes: bool = False
    workspace_root: Path | None = None

    @property
    def is_valid(self) -> bool:
        return self.status in {"clean", "fixable"}


def extract_docx_package(docx_path: str | Path, extract_dir: str | Path) -> None:
    with zipfile.ZipFile(docx_path, "r") as archive:
        archive.extractall(extract_dir)


def normalize_extracted_docx(extract_dir: str | Path) -> int:
    extract_dir = Path(extract_dir)
    total_fixes = 0
    xml_files = [
        ("word/document.xml", False),
        ("word/styles.xml", False),
        ("word/numbering.xml", False),
        ("word/settings.xml", True),
    ]

    for rel_path, is_settings in xml_files:
        xml_path = extract_dir / rel_path
        if not xml_path.exists():
            continue

        tree = ET.parse(xml_path)
        root = tree.getroot()
        fixes = fix_element_order_in_tree(root)
        if is_settings:
            fixes += fix_settings(root)
        if rel_path == "word/document.xml":
            fixes += fix_table_width_conservative(root)
        if fixes > 0:
            tree.write(xml_path, encoding="UTF-8", xml_declaration=True)
            total_fixes += fixes

    word_dir = extract_dir / "word"
    if word_dir.exists():
        for xml_file in list(word_dir.glob("header*.xml")) + list(word_dir.glob("footer*.xml")):
            tree = ET.parse(xml_file)
            root = tree.getroot()
            fixes = fix_element_order_in_tree(root)
            if fixes > 0:
                tree.write(xml_file, encoding="UTF-8", xml_declaration=True)
                total_fixes += fixes

    return total_fixes


def validate_extracted_docx(extract_dir: str | Path) -> tuple[list[str], list[str]]:
    extract_dir = Path(extract_dir)
    errors: list[str] = []
    warnings: list[str] = []

    doc_path = extract_dir / "word" / "document.xml"
    if not doc_path.exists():
        return ["STRUCTURE: word/document.xml missing"], []

    tree = ET.parse(doc_path)
    root = tree.getroot()

    errors.extend(check_table_grid_consistency(root))
    errors.extend(check_image_aspect_ratio(root, extract_dir))
    errors.extend(check_comments_integrity(extract_dir))
    warnings.extend(check_section_margins(root))

    doc_errors, doc_warnings = check_document_settings(extract_dir)
    errors.extend(doc_errors)
    warnings.extend(doc_warnings)

    return errors, warnings


def repack_docx_package(docx_path: str | Path, extract_dir: str | Path) -> None:
    docx_path = Path(docx_path)
    extract_dir = Path(extract_dir)
    backup_path = docx_path.with_suffix(".docx.bak")
    shutil.copy2(docx_path, backup_path)

    try:
        with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as archive:
            all_files = [path for path in extract_dir.rglob("*") if path.is_file()]

            def sort_key(file_path: Path) -> tuple[int, str]:
                rel = str(file_path.relative_to(extract_dir))
                if rel == "[Content_Types].xml":
                    return (0, rel)
                if rel.startswith("_rels"):
                    return (1, rel)
                if rel.startswith("word/_rels"):
                    return (2, rel)
                return (3, rel)

            for file_path in sorted(all_files, key=sort_key):
                archive.write(file_path, file_path.relative_to(extract_dir))
    except Exception:
        shutil.copy2(backup_path, docx_path)
        raise
    finally:
        if backup_path.exists():
            backup_path.unlink()


def classify_preflight_result(*, fixes: int, errors: list[str]) -> str:
    if errors:
        return "invalid"
    if fixes > 0:
        return "fixable"
    return "clean"


def preflight_docx(
    docx_path: str | Path,
    *,
    workspace_purpose: str = "preflight",
) -> PreflightResult:
    docx_path = Path(docx_path)

    if not docx_path.exists():
        return PreflightResult(
            status="invalid",
            fixes=0,
            errors=[f"FILE: not found: {docx_path}"],
            warnings=[],
            applied_fixes=False,
            workspace_root=None,
        )

    run_succeeded = False
    workspace = create_runtime_workspace(workspace_purpose, contents_dir="extracted")
    extract_dir = workspace.work_dir

    try:
        try:
            extract_docx_package(docx_path, extract_dir)
        except zipfile.BadZipFile:
            return PreflightResult(
                status="invalid",
                fixes=0,
                errors=["STRUCTURE: File corrupted or not valid docx"],
                warnings=[],
                applied_fixes=False,
                workspace_root=workspace.root_dir,
            )

        fixes = normalize_extracted_docx(extract_dir)
        errors, warnings = validate_extracted_docx(extract_dir)
        status = classify_preflight_result(fixes=fixes, errors=errors)
        applied_fixes = status == "fixable" and fixes > 0

        if applied_fixes:
            repack_docx_package(docx_path, extract_dir)

        run_succeeded = status != "invalid"
        return PreflightResult(
            status=status,
            fixes=fixes,
            errors=errors,
            warnings=warnings,
            applied_fixes=applied_fixes,
            workspace_root=workspace.root_dir,
        )
    except ET.ParseError as exc:
        return PreflightResult(
            status="invalid",
            fixes=0,
            errors=[f"PARSE: {exc}"],
            warnings=[],
            applied_fixes=False,
            workspace_root=workspace.root_dir,
        )
    except Exception as exc:
        return PreflightResult(
            status="invalid",
            fixes=0,
            errors=[f"PARSE: {exc}"],
            warnings=[],
            applied_fixes=False,
            workspace_root=workspace.root_dir,
        )
    finally:
        workspace.cleanup(success=run_succeeded)
