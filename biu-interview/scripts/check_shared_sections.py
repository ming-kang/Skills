#!/usr/bin/env python3
"""Verify the shared "Biu Workflow" section is identical across the three skills.

The section between the "## Biu Workflow" heading and the next "## " heading is
deliberately duplicated in biu-interview / biu-decompose / biu-archive so each
skill is self-contained when loaded alone. Duplication drifts; this check makes
the drift loud. Run after editing any of the three SKILL.md files:

    python3 biu-interview/scripts/check_shared_sections.py

Exits 0 when all three copies are byte-identical, 1 otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

SKILLS = ("biu-interview", "biu-decompose", "biu-archive")
HEADING = "## Biu Workflow"


def find_root(start: Path) -> Path:
    for base in (start, *start.parents):
        if all((base / s / "SKILL.md").is_file() for s in SKILLS):
            return base
    sys.exit(f"check_shared_sections: could not find the three biu skills above {start}")


def shared_section(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index(HEADING)
    except ValueError:
        sys.exit(f"check_shared_sections: {path} has no '{HEADING}' heading")
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end]).rstrip()


def main() -> int:
    root = find_root(Path(__file__).resolve().parent)
    sections = {s: shared_section(root / s / "SKILL.md") for s in SKILLS}
    reference_skill = SKILLS[0]
    reference = sections[reference_skill]
    drift = False
    for skill in SKILLS[1:]:
        if sections[skill] == reference:
            continue
        drift = True
        ref_lines = reference.splitlines()
        got_lines = sections[skill].splitlines()
        for n, (a, b) in enumerate(zip(ref_lines, got_lines), start=1):
            if a != b:
                print(f"{skill}: first difference at shared-section line {n}:")
                print(f"  {reference_skill}: {a}")
                print(f"  {skill}: {b}")
                break
        else:
            longer = reference_skill if len(ref_lines) > len(got_lines) else skill
            print(f"{skill}: shared section length differs ({longer} has extra lines)")
    if drift:
        print("DRIFT — copy the corrected section to all three SKILL.md files, then re-run.")
        return 1
    print(f"OK — shared section identical across {', '.join(SKILLS)} "
          f"({len(reference.splitlines())} lines).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
