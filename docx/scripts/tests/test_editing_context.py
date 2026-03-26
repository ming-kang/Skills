import sys
import zipfile
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

from docx_lib.editing import DocxContext, insert_text
from docx_lib.workspace import DOCX_KEEP_WORKSPACE_ENV


CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""

PACKAGE_RELS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

DOCUMENT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r><w:t>Alpha beta gamma.</w:t></w:r>
    </w:p>
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>
"""


def write_edit_docx(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        zf.writestr("_rels/.rels", PACKAGE_RELS_XML)
        zf.writestr("word/document.xml", DOCUMENT_XML)


def read_document_xml(path: Path) -> str:
    with zipfile.ZipFile(path, "r") as zf:
        return zf.read("word/document.xml").decode("utf-8")


def test_docx_context_supports_explicit_task_and_work_root_overrides(tmp_path: Path):
    source = tmp_path / "input.docx"
    output = tmp_path / "output.docx"
    task_root = tmp_path / "task-root"
    task_root.mkdir()
    write_edit_docx(source)

    workspace_path = None

    with DocxContext(
        str(source),
        str(output),
        task_root=task_root,
        work_root="debug-workspaces",
        keep_workspace=True,
    ) as ctx:
        workspace_path = ctx.work_dir
        assert workspace_path.parent == task_root / "debug-workspaces"
        insert_text(ctx, "Alpha beta gamma.", after="Alpha", new_text=" patched")

    assert output.exists()
    assert workspace_path is not None
    assert workspace_path.exists()
    assert " patched" in read_document_xml(output)
    assert len(list((task_root / "debug-workspaces").glob("docx-edit-*"))) == 1


def test_docx_context_keep_workspace_override_beats_env(tmp_path: Path, monkeypatch):
    source = tmp_path / "input.docx"
    output = tmp_path / "output.docx"
    work_root = tmp_path / "explicit-work-root"
    write_edit_docx(source)
    monkeypatch.setenv(DOCX_KEEP_WORKSPACE_ENV, "1")

    with DocxContext(
        str(source),
        str(output),
        work_root=work_root,
        keep_workspace=False,
    ) as ctx:
        workspace_path = ctx.work_dir
        assert workspace_path.parent == work_root

    assert output.exists()
    assert not workspace_path.exists()
    assert list(work_root.glob("docx-edit-*")) == []


def test_docx_context_default_success_cleans_visible_workspace(tmp_path: Path, monkeypatch):
    source = tmp_path / "input.docx"
    output = tmp_path / "output.docx"
    write_edit_docx(source)
    monkeypatch.chdir(tmp_path)

    with DocxContext(str(source), str(output)) as ctx:
        workspace_path = ctx.work_dir
        assert workspace_path.parent == tmp_path / ".docx-tmp"

    assert output.exists()
    assert not workspace_path.exists()
    assert list((tmp_path / ".docx-tmp").glob("docx-edit-*")) == []


def test_docx_context_default_failure_preserves_visible_workspace(tmp_path: Path, monkeypatch):
    source = tmp_path / "input.docx"
    output = tmp_path / "output.docx"
    write_edit_docx(source)
    monkeypatch.chdir(tmp_path)
    workspace_path = None

    with pytest.raises(RuntimeError):
        with DocxContext(str(source), str(output)) as ctx:
            workspace_path = ctx.work_dir
            raise RuntimeError("expected edit failure")

    assert workspace_path is not None
    assert workspace_path.parent == tmp_path / ".docx-tmp"
    assert workspace_path.exists()
    assert (workspace_path / "word" / "document.xml").exists()
