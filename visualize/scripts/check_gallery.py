#!/usr/bin/env python3
"""Gallery regression check — run the full validator suite against every
reference diagram so changes to the validator do not silently break the
examples that are the ground truth for the house style.

The gallery lives at ``assets/gallery/*.svg`` and ships one on-style
reference diagram per supported type.  Each file must pass the same
``validate_svg.Validator`` suite that is applied to generated output.

Run:  ``python3 scripts/check_gallery.py``
Exits 0 when every gallery SVG passes, 1 if any fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_svg import Validator  # type: ignore

GALLERY = Path(__file__).resolve().parent.parent / "assets" / "gallery"


def main() -> int:
    svg_files = sorted(GALLERY.glob("*.svg"))
    if not svg_files:
        print("check_gallery: no SVG files found in", GALLERY)
        return 1

    print("Checking gallery SVGs (validate_svg suite)")
    print("-" * 58)

    failed: list[str] = []
    for path in svg_files:
        name = path.name
        v = Validator(path, no_color=True)
        rc = v.run()
        if rc != 0:
            failed.append(name)
            print(f"  {name}  FAIL")
        else:
            print(f"  {name}  pass")

    print("-" * 58)
    if failed:
        print(f"FAIL ({len(failed)} of {len(svg_files)} gallery file(s) failed)")
        return 1
    print(f"OK — {len(svg_files)} gallery SVG(s) all pass the validator suite.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
