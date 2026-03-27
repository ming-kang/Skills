#!/usr/bin/env python
"""
validate_all.py - Unified validation: element order fix + business rules check
One unzip, two checks

Usage: python validate_all.py <file.docx>

Combines:
  - fix_element_order: Auto-fix XML element ordering issues
  - validate_docx: Business rule validation (table grid, image aspect, comments)
"""

import sys
from docx_lib import preflight_docx


def validate_and_fix(docx_path):
    """
    Run the shared preflight / normalization contract.

    Returns: (fix_count, errors, warnings)
    """
    result = preflight_docx(docx_path, workspace_purpose="validate-all")
    return result.fixes, result.errors, result.warnings


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_all.py <file.docx>")
        sys.exit(1)

    docx_path = sys.argv[1]

    fixes, errors, warnings = validate_and_fix(docx_path)

    if fixes > 0:
        print(f"Normalized {fixes} structural issue(s)")

    for warn in warnings:
        print(f"Warning: {warn}")

    if errors:
        for err in errors:
            print(f"Error: {err}")
        sys.exit(1)
    else:
        print("Validation passed")
        sys.exit(0)


if __name__ == "__main__":
    main()
