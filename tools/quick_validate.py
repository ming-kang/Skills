#!/usr/bin/env python3
"""Validate the SKILL.md frontmatter of one or more skill directories.

Adapted from ``scripts/quick_validate.py`` in the ``skill-creator`` skill of
anthropics/skills, distributed under the Apache License 2.0. Local changes:

  * read ``SKILL.md`` as UTF-8 explicitly — upstream used the platform default
    encoding, which fails on Windows as soon as a description contains a
    non-ASCII character such as an em dash;
  * accept several skill directories at once, and with no arguments validate
    every top-level ``<skill>/SKILL.md`` in this repository.

The checks are the ones an installer applies before it accepts a skill: the
frontmatter must parse as YAML, only the documented keys may appear, ``name``
must be kebab-case (max 64 chars), and ``description`` must be a string without
angle brackets (max 1024 chars). An unquoted ``: `` inside ``description`` is
the classic failure — YAML reads it as a nested mapping and ``npx skills add``
silently skips the skill.

Usage::

    python tools/quick_validate.py                 # every skill in the repo
    python tools/quick_validate.py pptd visualize  # specific skill folders

Requires PyYAML. Exits 1 when any skill fails.
"""

import re
import sys
from pathlib import Path

import yaml

ALLOWED_PROPERTIES = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
REPO_ROOT = Path(__file__).resolve().parent.parent


def validate_skill(skill_path):
    """Basic validation of a skill. Returns (is_valid, message)."""
    skill_path = Path(skill_path)

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"

    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return False, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    try:
        frontmatter = yaml.safe_load(match.group(1))
        if not isinstance(frontmatter, dict):
            return False, "Frontmatter must be a YAML dictionary"
    except yaml.YAMLError as e:
        return False, f"Invalid YAML in frontmatter: {e}"

    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected_keys:
        return False, (
            f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
            f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}"
        )

    if "name" not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if "description" not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    name = frontmatter.get("name", "")
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    if name:
        if not re.match(r"^[a-z0-9-]+$", name):
            return False, f"Name '{name}' should be kebab-case (lowercase letters, digits, and hyphens only)"
        if name.startswith("-") or name.endswith("-") or "--" in name:
            return False, f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"
        if len(name) > 64:
            return False, f"Name is too long ({len(name)} characters). Maximum is 64 characters."

    description = frontmatter.get("description", "")
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()
    if description:
        if "<" in description or ">" in description:
            return False, "Description cannot contain angle brackets (< or >)"
        if len(description) > 1024:
            return False, f"Description is too long ({len(description)} characters). Maximum is 1024 characters."

    compatibility = frontmatter.get("compatibility", "")
    if compatibility:
        if not isinstance(compatibility, str):
            return False, f"Compatibility must be a string, got {type(compatibility).__name__}"
        if len(compatibility) > 500:
            return False, f"Compatibility is too long ({len(compatibility)} characters). Maximum is 500 characters."

    return True, "Skill is valid!"


def discover_skills(root):
    """Every direct child directory of ``root`` that contains a SKILL.md."""
    return sorted(path.parent for path in Path(root).glob("*/SKILL.md"))


def main(argv):
    targets = [Path(arg) for arg in argv] or discover_skills(REPO_ROOT)
    if not targets:
        print(f"No SKILL.md found under {REPO_ROOT}")
        return 1

    failures = 0
    for target in targets:
        valid, message = validate_skill(target)
        print(f"{target.name}: {message}")
        failures += not valid
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
