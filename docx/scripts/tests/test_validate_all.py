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

from validate_all import validate_and_fix


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

DOCUMENT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r>
        <w:t>Hello</w:t>
      </w:r>
    </w:p>
    {body_suffix}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>
"""

INVALID_TABLE_XML = """<w:tbl>
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
"""

MISORDERED_SETTINGS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:proofState w:spelling="clean" w:grammar="clean"/>
  <w:zoom w:percent="100"/>
</w:settings>
"""


def write_minimal_docx(
    path: Path,
    *,
    invalid_table: bool = False,
    include_misordered_settings: bool = False,
) -> None:
    body_suffix = INVALID_TABLE_XML if invalid_table else ""

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        zf.writestr("_rels/.rels", PACKAGE_RELS_XML)
        zf.writestr("word/document.xml", DOCUMENT_XML.format(body_suffix=body_suffix))
        if include_misordered_settings:
            zf.writestr("word/settings.xml", MISORDERED_SETTINGS_XML)


def test_validate_all_repack_path_cleans_workspace_by_default(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    docx_path = tmp_path / "needs-fix.docx"
    write_minimal_docx(docx_path, include_misordered_settings=True)

    fixes, errors, warnings = validate_and_fix(docx_path)

    assert fixes > 0
    assert errors == []
    assert warnings == []
    assert not docx_path.with_suffix(".docx.bak").exists()
    assert list((tmp_path / ".docx-tmp").glob("docx-validate-all-*")) == []

    with zipfile.ZipFile(docx_path, "r") as zf:
        settings_xml = zf.read("word/settings.xml").decode("utf-8")
    assert settings_xml.index("zoom") < settings_xml.index("proofState")


def test_validate_all_preserves_workspace_on_validation_errors(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    docx_path = tmp_path / "invalid.docx"
    write_minimal_docx(docx_path, invalid_table=True)

    fixes, errors, warnings = validate_and_fix(docx_path)

    assert fixes == 0
    assert warnings == []
    assert errors == ["TABLE[1]: missing tblGrid (required for proper rendering)"]

    workspaces = list((tmp_path / ".docx-tmp").glob("docx-validate-all-*"))
    assert len(workspaces) == 1
    assert (workspaces[0] / "extracted" / "word" / "document.xml").exists()
