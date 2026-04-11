# Skills

A collection of Claude Code skills for common tasks. These skills can be used with Claude Code to extend its capabilities for specific domains.

## Available Skills

| Skill | Description |
|-------|-------------|
| `docx` | Generate and edit Word documents (.docx) with professional styling, charts, and track changes |
| `spec-coding` | Modular workflow for complex development (v2.1.0) — reusable analysis, cycle planning in COMPASS, and single-task execution tracking |

## Directory Structure

```
skills-root/
├── docx/                    # Word document generation and editing skill
│   ├── SKILL.md            # Entry point + complete reference
│   ├── references/
│   │   └── EditingGuide.md # Python editing tutorial
│   ├── scripts/
│   │   ├── docx            # Unified CLI entry point (bash)
│   │   ├── docx_lib/       # Python library for editing
│   │   ├── validate_docx.py
│   │   ├── fix_element_order.py
│   │   └── generate_*.py   # Background/image generation helpers
│   ├── assets/templates/   # C# templates (Example.cs, CJKExample.cs)
│   └── validator/          # Pre-compiled OpenXML validator
│
└── spec-coding/            # Modular workflow for complex development
    ├── SKILL.md            # Entry point + 3 capability modules + archive workflow
    ├── references/
    │   └── blocked-protocol.md  # Blocked task handling protocol
    └── assets/templates/
        ├── COMPASS.md           # Current-cycle control file template
        ├── analysis/            # architecture.md, module-map.md
        └── progress/            # task.md (per-task progress tracker)
```

## Installation Guide

Run the following command

```powershell
npx skills install ming-kang/Skills
```

## License

MIT License
