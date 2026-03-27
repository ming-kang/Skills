#!/usr/bin/env python
"""
preflight_docx.py - Normalize and classify incoming docx inputs before edit/build workflows.

Usage: python preflight_docx.py <file.docx>
"""

import sys
from pathlib import Path

from docx_lib import preflight_docx


def main():
    if len(sys.argv) < 2:
        print("Usage: python preflight_docx.py <file.docx>")
        sys.exit(1)

    docx_path = Path(sys.argv[1])
    result = preflight_docx(docx_path)

    print(f"Preflight status: {result.status}")

    if result.status == "clean":
        print("No normalization changes were needed")
    elif result.status == "fixable":
        print(f"Normalized {result.fixes} structural issue(s) in place")
    elif result.fixes > 0:
        print(
            f"Detected {result.fixes} normalization candidate(s), "
            "but left the source file unchanged because unrecoverable errors remain"
        )

    for warning in result.warnings:
        print(f"Warning: {warning}")

    if result.errors:
        if result.workspace_root is not None:
            print(f"Inspect preserved workspace: {result.workspace_root}")
        for error in result.errors:
            print(f"Error: {error}")
        sys.exit(1)

    print("Preflight passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
