#!/usr/bin/env python3
"""
Regression tests for validation behavior in local environments.
"""

import tempfile
import zipfile
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_all import validate_and_fix
from validate_docx import validate_document

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PKG_RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def create_minimal_docx(path: Path, paragraph_text: str = "Hello world") -> None:
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml"
            ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    rels = f"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="{PKG_RELS_NS}">
  <Relationship Id="rId1"
                Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
                Target="word/document.xml"/>
</Relationships>"""

    document_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{W_NS}">
  <w:body>
    <w:p><w:r><w:t>{paragraph_text}</w:t></w:r></w:p>
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>"""

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document_xml)


def test_validate_and_fix_missing_file_returns_consistent_tuple():
    fixes, errors, warnings = validate_and_fix("definitely-missing.docx")
    assert fixes == 0
    assert warnings == []
    assert len(errors) == 1
    assert errors[0].startswith("FILE: not found:")


def test_validate_and_fix_invalid_zip_returns_structure_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        invalid_path = Path(tmpdir) / "bad.docx"
        invalid_path.write_text("not-a-zip", encoding="utf-8")

        fixes, errors, warnings = validate_and_fix(str(invalid_path))
        assert fixes == 0
        assert warnings == []
        assert errors == ["STRUCTURE: File corrupted or not valid docx"]


def test_validate_and_fix_minimal_docx_has_no_errors_or_warnings():
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = Path(tmpdir) / "minimal.docx"
        create_minimal_docx(docx_path)

        fixes, errors, warnings = validate_and_fix(str(docx_path))
        assert isinstance(fixes, int)
        assert errors == []
        assert warnings == []


def test_validate_document_reports_structure_error_for_invalid_zip():
    with tempfile.TemporaryDirectory() as tmpdir:
        invalid_path = Path(tmpdir) / "bad.docx"
        invalid_path.write_text("not-a-zip", encoding="utf-8")

        errors, warnings = validate_document(str(invalid_path))
        assert warnings == []
        assert "STRUCTURE: File corrupted or not valid docx" in errors
