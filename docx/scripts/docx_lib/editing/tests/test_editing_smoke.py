#!/usr/bin/env python3
"""
Smoke test for real editing behavior on a minimal docx package.
"""

import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import sys

SCRIPTS_DIR = Path(__file__).resolve().parents[3]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from docx_lib.editing import DocxContext, insert_text

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


def test_insert_text_smoke_creates_revision_markup():
    ns = {"w": W_NS}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        input_path = tmp / "input.docx"
        output_path = tmp / "output.docx"
        create_minimal_docx(input_path)

        with DocxContext(str(input_path), str(output_path)) as ctx:
            insert_text(ctx, "Hello world", after="Hello", new_text=" brave")

        assert output_path.exists()

        with zipfile.ZipFile(output_path, "r") as zf:
            document_xml = zf.read("word/document.xml")

        root = ET.fromstring(document_xml)
        assert len(root.findall(".//w:ins", ns)) == 1

        inserted_text_nodes = [node.text or "" for node in root.findall(".//w:ins//w:t", ns)]
        assert " brave" in inserted_text_nodes
