import sys
import zipfile
from pathlib import Path


def find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "docx" / "scripts").exists():
            return parent
    raise RuntimeError("repo root not found")


REPO_ROOT = find_repo_root()
sys.path.insert(0, str(REPO_ROOT / "docx" / "scripts"))

from validate_docx import validate_document


CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
</Types>
"""

PACKAGE_RELS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

TOC_DOCUMENT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r>
        <w:instrText> TOC \\o "1-3" \\h \\z \\u </w:instrText>
      </w:r>
    </w:p>
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>
"""

INVALID_TABLE_DOCUMENT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:tbl>
      <w:tblPr>
        <w:tblW w:w="5000" w:type="dxa"/>
      </w:tblPr>
      <w:tr>
        <w:tc>
          <w:tcPr>
            <w:tcW w:w="5000" w:type="dxa"/>
          </w:tcPr>
          <w:p><w:r><w:t>Cell</w:t></w:r></w:p>
        </w:tc>
      </w:tr>
    </w:tbl>
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>
"""

SETTINGS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:zoom w:percent="100"/>
</w:settings>
"""


def write_validation_docx(path: Path, document_xml: str, *, include_settings: bool = True) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        zf.writestr("_rels/.rels", PACKAGE_RELS_XML)
        zf.writestr("word/document.xml", document_xml)
        if include_settings:
            zf.writestr("word/settings.xml", SETTINGS_XML)


def test_validate_docx_success_with_warning_cleans_workspace(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    docx_path = tmp_path / "toc.docx"
    write_validation_docx(docx_path, TOC_DOCUMENT_XML)

    errors, warnings = validate_document(docx_path)

    assert errors == []
    assert warnings == [
        'TOC: consider adding <w:updateFields w:val="true"/> in settings.xml for auto-update'
    ]
    assert list((tmp_path / ".docx-tmp").glob("docx-validate-docx-*")) == []


def test_validate_docx_preserves_workspace_on_validation_errors(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    docx_path = tmp_path / "invalid.docx"
    write_validation_docx(docx_path, INVALID_TABLE_DOCUMENT_XML, include_settings=False)

    errors, warnings = validate_document(docx_path)

    assert warnings == []
    assert errors == ["TABLE[1]: missing tblGrid (required for proper rendering)"]

    workspaces = list((tmp_path / ".docx-tmp").glob("docx-validate-docx-*"))
    assert len(workspaces) == 1
    assert (workspaces[0] / "extracted" / "word" / "document.xml").exists()
