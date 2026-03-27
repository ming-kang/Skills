#!/usr/bin/env python
"""
validate_docx.py - Custom business rule validation (not covered by OpenXML SDK)
Usage: python validate_docx.py <file.docx>

Checks (only what OpenXML SDK doesn't cover):
  - gridCol/tcW width consistency (table not skewed)
  - Image cx/cy proportional scaling (not distorted)
  - Comments 4-file sync integrity
  - tblGrid existence

Output format (high density, LLM-friendly):
  Error: TABLE[2]: gridCol[0].w=5000 != tc[0].tcW=4500
  Error: IMAGE[1]: aspect=1.60 != original=1.78 (will distort)
  Validation passed
"""

import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

# Import from shared library
from docx_lib import (
    check_table_grid_consistency,
    check_image_aspect_ratio,
    check_comments_integrity,
    check_document_settings,
)
from docx_lib.workspace import create_runtime_workspace


def validate_document(docx_path):
    """Validate docx document"""
    errors = []
    warnings = []
    run_succeeded = False
    workspace = create_runtime_workspace("validate-docx", contents_dir="extracted")
    extract_dir = workspace.work_dir

    try:
        # Extract docx
        with zipfile.ZipFile(docx_path, 'r') as zf:
            zf.extractall(extract_dir)

        # Check required files
        doc_path = extract_dir / 'word' / 'document.xml'
        if not doc_path.exists():
            errors.append("STRUCTURE: word/document.xml missing")
            return errors, warnings

        # Parse document.xml
        tree = ET.parse(doc_path)
        root = tree.getroot()

        # Business rule checks
        errors.extend(check_table_grid_consistency(root))
        errors.extend(check_image_aspect_ratio(root, extract_dir))
        errors.extend(check_comments_integrity(extract_dir))

        doc_errors, doc_warnings = check_document_settings(extract_dir)
        errors.extend(doc_errors)
        warnings.extend(doc_warnings)

        run_succeeded = not errors

    except zipfile.BadZipFile:
        errors.append("STRUCTURE: File corrupted or not valid docx")
    except Exception as e:
        errors.append(f"PARSE: {str(e)}")
    finally:
        workspace.cleanup(success=run_succeeded)

    return errors, warnings


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_docx.py <file.docx>")
        sys.exit(1)

    docx_path = sys.argv[1]

    if not Path(docx_path).exists():
        print(f"Error: FILE: not found: {docx_path}")
        sys.exit(1)

    errors, warnings = validate_document(docx_path)

    # Output warnings
    for warn in warnings:
        print(f"Warning: {warn}")

    # Output errors
    if errors:
        for err in errors:
            print(f"Error: {err}")
        sys.exit(1)
    else:
        print("Custom validation passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
