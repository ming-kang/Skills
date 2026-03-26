#!/usr/bin/env python3
"""
Test cases for XML tolerance functions.
These tests verify that malformed XML (like duplicate attributes) can be handled.
"""

import pytest
import tempfile
import os
from xml.etree import ElementTree as ET

# Import the functions we'll implement
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from xml_tolerance import fix_duplicate_attributes, safe_parse_xml, safe_parse_xml_string


def write_temp_xml(xml_content: str) -> str:
    """Create a temp XML file that can be safely reopened and deleted on Windows."""
    fd, path = tempfile.mkstemp(suffix='.xml')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(xml_content)
    except Exception:
        os.unlink(path)
        raise
    return path


class TestFixDuplicateAttributes:
    """Test the fix_duplicate_attributes function."""

    def test_no_duplicates(self):
        """XML without duplicates should remain unchanged."""
        xml = '<root attr1="val1" attr2="val2">content</root>'
        result = fix_duplicate_attributes(xml)
        assert result == xml

    def test_simple_duplicate(self):
        """Simple duplicate attribute should keep first occurrence."""
        xml = '<root attr="val1" attr="val2">content</root>'
        result = fix_duplicate_attributes(xml)
        # Should keep first attr="val1", remove second
        assert 'attr="val1"' in result
        assert result.count('attr=') == 1

    def test_duplicate_with_namespace(self):
        """Duplicate namespaced attribute should be fixed."""
        xml = '<w:comment w:id="1" w:author="Test" w:id="2">content</w:comment>'
        result = fix_duplicate_attributes(xml)
        assert result.count('w:id=') == 1
        assert 'w:id="1"' in result

    def test_multiple_duplicates(self):
        """Multiple different duplicate attributes."""
        xml = '<elem a="1" b="2" a="3" b="4">text</elem>'
        result = fix_duplicate_attributes(xml)
        assert result.count('a=') == 1
        assert result.count('b=') == 1

    def test_complex_docx_comment_xml(self):
        """Real-world style comment XML with duplicates."""
        xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:comment w:id="0" w:author="Test" w:date="2026-01-08T00:00:00Z" w:id="1">
    <w:p><w:r><w:t>Comment text</w:t></w:r></w:p>
  </w:comment>
</w:comments>'''
        result = fix_duplicate_attributes(xml)
        # Should be parseable now
        root = ET.fromstring(result)
        assert root is not None

    def test_preserves_valid_structure(self):
        """Fixing duplicates should preserve overall XML structure."""
        xml = '''<root>
  <child attr="value" attr="dup"/>
  <other name="test"/>
</root>'''
        result = fix_duplicate_attributes(xml)
        root = ET.fromstring(result)
        assert len(root) == 2


class TestSafeParseXml:
    """Test the safe_parse_xml function."""

    def test_valid_xml_file(self):
        """Valid XML file should parse normally."""
        path = write_temp_xml('<?xml version="1.0"?><root><child/></root>')
        try:
            tree = safe_parse_xml(path)
            assert tree.getroot().tag == 'root'
        finally:
            os.unlink(path)

    def test_duplicate_attribute_file(self):
        """File with duplicate attributes should be auto-fixed."""
        xml_content = '<?xml version="1.0"?><root attr="1" attr="2"><child/></root>'
        path = write_temp_xml(xml_content)
        try:
            tree = safe_parse_xml(path)
            root = tree.getroot()
            assert root.tag == 'root'
            assert root.get('attr') == '1'  # First value kept
        finally:
            os.unlink(path)

    def test_comments_xml_with_duplicates(self):
        """Simulate real comments.xml with duplicate w:id."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:comment w:id="0" w:author="Author" w:date="2026-01-08T00:00:00Z" w:initials="A" w:id="0">
    <w:p><w:r><w:t>Test comment</w:t></w:r></w:p>
  </w:comment>
</w:comments>'''
        path = write_temp_xml(xml_content)
        try:
            tree = safe_parse_xml(path)
            root = tree.getroot()
            # Should have parsed successfully
            comments = root.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}comment')
            assert len(comments) == 1
        finally:
            os.unlink(path)

    def test_valid_xml_with_bom(self):
        """Files with a UTF-8 BOM should still parse."""
        xml_content = '\ufeff<?xml version="1.0"?><root><child>ok</child></root>'
        path = write_temp_xml(xml_content)
        try:
            tree = safe_parse_xml(path)
            assert tree.getroot().tag == 'root'
            assert tree.getroot().find('child').text == 'ok'
        finally:
            os.unlink(path)


class TestSafeParseXmlString:
    """Test in-memory tolerant parsing."""

    def test_duplicate_attributes_string(self):
        """String parsing should also recover duplicate attributes."""
        root = safe_parse_xml_string('<root attr="1" attr="2"><child/></root>')
        assert root.tag == 'root'
        assert root.get('attr') == '1'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
