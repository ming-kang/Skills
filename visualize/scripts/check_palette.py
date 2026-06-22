#!/usr/bin/env python3
"""Palette drift check — keep the three color sources byte-for-byte in sync.

The warm palette is defined in three places, and nothing else enforces that
they agree:

  1. ``references/style.md``     — the source of truth (human-edited table)
  2. ``scripts/svgkit.py``       — ``FAMILIES``, used to generate SVGs
  3. ``scripts/validate_svg.py`` — ``WARM_PALETTE``, the warm-color exemption list

Editing ``style.md`` and forgetting to mirror the change into ``svgkit.py``
produces a doc that quietly lies about the colors the skill actually emits.
``validate_svg.py`` cannot catch that: its cold-color check is a *hue* test
(``b > r + 12 and b >= g - 4``), and the old green and the new green are both
warm, so neither is flagged. This script closes that blind spot. It parses
``style.md``'s family table and asserts:

  * every family in ``style.md`` exists in ``svgkit.FAMILIES`` (and vice-versa),
  * every slot (fill / stroke / title / sub / line) matches byte-for-byte,
  * every hex a family defines is registered in ``validate_svg.WARM_PALETTE``.

Run:  ``python3 scripts/check_palette.py``
Exits 0 when the three sources agree, 1 on any drift. Run after any
style-token edit.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Both peers live next to this script; importing them directly works because
# Python prepends the script's own directory to sys.path — the same trick
# validate_svg.py relies on to `import svgkit`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgkit import FAMILIES  # type: ignore
from validate_svg import WARM_PALETTE, normalize_hex  # type: ignore

STYLE_MD = Path(__file__).resolve().parent.parent / "references" / "style.md"
SLOTS = ("fill", "stroke", "title", "sub", "line")


def _norm(value: str) -> str:
    """Comparable form: lowercase, no backticks, no spaces. Hex and rgba both survive."""
    return value.strip().lower().replace("`", "").replace(" ", "")


def parse_style_families(path: Path) -> dict[str, dict[str, str]]:
    """Parse the ``## Color families`` table in style.md -> {family: {slot: raw}}.

    Each data row is ``| **Name** | meaning | FILL | STROKE | TITLE | SUB | LINE |``.
    Header and ``|---|`` separator rows are skipped; the meaning cell is not
    captured (parts[1]) so the five color slots land at parts[2:7].
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.strip().lower().startswith("## color families"):
            start = i
            break
    if start is None:
        sys.exit(f"check_palette: could not find '## Color families' in {path}")

    families: dict[str, dict[str, str]] = {}
    in_table = False
    for ln in lines[start + 1:]:
        s = ln.strip()
        if not s.startswith("|"):
            if in_table and families:
                break  # a blank/text line ends the table once data has been seen
            continue
        in_table = True
        parts = s.split("|")
        if parts and parts[0].strip() == "":
            parts = parts[1:]
        if parts and parts[-1].strip() == "":
            parts = parts[:-1]
        if len(parts) < 7:
            continue
        name_cell = parts[0].strip()
        if "**" not in name_cell:
            continue  # column header ("Family") or the |---| rule row
        name = name_cell.replace("**", "").strip().lower()
        families[name] = {slot: _norm(v) for slot, v in zip(SLOTS, parts[2:7])}
    if not families:
        sys.exit(f"check_palette: no family rows parsed from {path}")
    return families


def main() -> int:
    doc = parse_style_families(STYLE_MD)
    svg = {fam: {slot: _norm(vals[slot]) for slot in SLOTS}
           for fam, vals in FAMILIES.items()}
    warm = {h.lower() for h in WARM_PALETTE}

    drift: list[str] = []

    # 1. same family set, both directions
    for fam in sorted(set(doc) - set(svg)):
        drift.append(f"family {fam!r} in style.md but missing from svgkit.FAMILIES")
    for fam in sorted(set(svg) - set(doc)):
        drift.append(f"family {fam!r} in svgkit.FAMILIES but missing from style.md table")

    # 2. slot-by-slot equality (style.md is the source of truth)
    for fam in sorted(set(doc) & set(svg)):
        for slot in SLOTS:
            if doc[fam][slot] != svg[fam][slot]:
                drift.append(
                    f"{fam}.{slot}: style.md={doc[fam][slot]!r} vs svgkit={svg[fam][slot]!r}"
                )

    # 3. every svgkit family hex is registered in the validator's exemption list
    for fam in sorted(svg):
        for slot in SLOTS:
            raw = FAMILIES[fam][slot]
            hx = normalize_hex(raw)
            if hx is not None and hx not in warm:
                drift.append(
                    f"{fam}.{slot}={raw!r} ({hx}) not in validate_svg.WARM_PALETTE"
                )

    print("Checking palette drift (style.md <-> svgkit <-> validate_svg)")
    print("-" * 58)
    if drift:
        for d in drift:
            print(f"  - {d}")
        print("-" * 58)
        print(f"DRIFT ({len(drift)} difference(s)) — mirror the change across "
              f"all three files, then re-run.")
        return 1
    slots = len(svg) * len(SLOTS)
    print(f"OK — {len(svg)} family/ies, {slots} slots, all three sources in sync.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
