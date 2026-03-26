"""
context.py - DocxContext for managing docx editing sessions.

NOTE: Uses lxml throughout for better namespace handling.
"""

import os
import zipfile
from pathlib import Path
from typing import Optional

from lxml import etree

from ..constants import NS
from ..workspace import RuntimeWorkspace, create_runtime_workspace
from .xml_tolerance import safe_parse_xml


class DocxEditError(Exception):
    """Base exception for docx editing errors."""
    pass


class ParagraphNotFoundError(DocxEditError):
    """Raised when paragraph text not found."""
    pass


class AmbiguousTextError(DocxEditError):
    """Raised when text appears multiple times without context."""
    pass


class CommentNotFoundError(DocxEditError):
    """Raised when comment ID not found."""
    pass


class DocxContext:
    """
    Context manager for editing docx files.

    Handles: unzip, parse, save, repack, cleanup.

    Usage:
        with DocxContext("input.docx", "output.docx") as ctx:
            add_comment(ctx, "M-SVI index", "Please define", highlight="M-SVI")
            insert_text(ctx, "The method", after="method", new_text=" and materials")
        # Automatically saves and repacks on exit

        with DocxContext(
            "input.docx",
            "output.docx",
            work_root="debug-workspaces",
            keep_workspace=True,
        ) as ctx:
            insert_text(ctx, "The method", after="method", new_text=" and materials")
        # Successful runs can be retained under an explicit visible work root

    Attributes (for internal use by editing functions):
        work_dir: Path to extracted docx
        doc_tree: Parsed document.xml ElementTree
        body: document.xml body element
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        *,
        task_root: str | Path | None = None,
        work_root: str | Path | None = None,
        keep_workspace: bool | None = None,
        keep_failed_workspace: bool = True,
    ):
        """
        Initialize context.

        Args:
            input_path: Path to input docx file
            output_path: Path for output docx file
            task_root: Optional visible task root override for workspace resolution
            work_root: Optional visible work root override for this editing session
            keep_workspace: Optional override for successful-workspace retention
            keep_failed_workspace: Whether failed sessions retain their workspace
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.task_root = task_root
        self.work_root_override = work_root
        self.keep_workspace = keep_workspace
        self.keep_failed_workspace = keep_failed_workspace
        self.work_dir: Optional[Path] = None
        self.doc_tree: Optional[etree._ElementTree] = None
        self.body = None
        self._workspace: Optional[RuntimeWorkspace] = None

    def __enter__(self) -> 'DocxContext':
        """Unzip and parse document."""
        # Validate input file exists
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_path}")

        self._workspace = create_runtime_workspace(
            "edit",
            task_root=self.task_root,
            work_root=self.work_root_override,
            keep_success=self.keep_workspace,
            keep_failure=self.keep_failed_workspace,
        )
        self.work_dir = self._workspace.work_dir

        try:
            # Unzip
            with zipfile.ZipFile(self.input_path, 'r') as z:
                z.extractall(self.work_dir)

            # Parse document.xml
            doc_path = self.work_dir / 'word' / 'document.xml'
            self.doc_tree = safe_parse_xml(doc_path)

            self.body = self.doc_tree.getroot().find(f'.//{{{NS["w"]}}}body')

            if self.body is None:
                raise DocxEditError("Invalid docx: document body not found")

            return self
        except Exception:
            if self._workspace is not None:
                self._workspace.cleanup(success=False)
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Save, repack, and cleanup."""
        run_succeeded = False

        try:
            if exc_type is None:
                # Save document.xml using lxml serialization
                doc_path = self.work_dir / 'word' / 'document.xml'
                xml_bytes = etree.tostring(
                    self.doc_tree.getroot(),
                    encoding='utf-8',
                    xml_declaration=True
                )
                with open(doc_path, 'wb') as f:
                    f.write(xml_bytes)

                # Repack with correct file order (OOXML requirement)
                with zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_DEFLATED) as z:
                    all_files = []
                    for root, dirs, files in os.walk(self.work_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, self.work_dir)
                            all_files.append((file_path, arcname))

                    # Sort by OOXML required order
                    def sort_key(item):
                        arcname = item[1]
                        if arcname == '[Content_Types].xml':
                            return (0, arcname)
                        elif arcname.startswith('_rels'):
                            return (1, arcname)
                        elif arcname.startswith('word/_rels'):
                            return (2, arcname)
                        else:
                            return (3, arcname)

                    for file_path, arcname in sorted(all_files, key=sort_key):
                        z.write(file_path, arcname)
                run_succeeded = True
        finally:
            if self._workspace is not None:
                self._workspace.cleanup(success=run_succeeded)

        return False  # Don't suppress exceptions

    def find_para(self, text: str):
        """
        Find paragraph containing text.

        Args:
            text: Text to search for (must be unique)

        Returns:
            Paragraph element

        Raises:
            ParagraphNotFoundError: If not found
            AmbiguousTextError: If multiple matches
        """
        matches = [p for p in self.body.findall('.//w:p', NS)
                   if text in ''.join(t.text or '' for t in p.findall('.//w:t', NS))]

        if len(matches) == 0:
            raise ParagraphNotFoundError(f"No paragraph contains '{text}'")
        if len(matches) > 1:
            raise AmbiguousTextError(f"'{text}' matches {len(matches)} paragraphs. Use more specific text.")

        return matches[0]

    def save_xml(self, rel_path: str, tree_or_element):
        """
        Save an XML tree or element to a relative path in work_dir.

        Args:
            rel_path: Relative path (e.g., 'word/comments.xml')
            tree_or_element: lxml ElementTree or Element to save
        """
        full_path = self.work_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Handle both ElementTree and Element
        if hasattr(tree_or_element, 'getroot'):
            root = tree_or_element.getroot()
        else:
            root = tree_or_element

        xml_bytes = etree.tostring(root, encoding='utf-8', xml_declaration=True)
        with open(full_path, 'wb') as f:
            f.write(xml_bytes)

    def parse_xml(self, rel_path: str) -> Optional[etree._ElementTree]:
        """
        Parse an XML file from work_dir.

        Args:
            rel_path: Relative path

        Returns:
            lxml ElementTree or None if file doesn't exist
        """
        full_path = self.work_dir / rel_path
        if full_path.exists():
            return safe_parse_xml(full_path)
        return None
