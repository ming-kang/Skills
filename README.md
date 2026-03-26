# Skills

A collection of Claude Code skills for common tasks. These skills can be used with Claude Code to extend its capabilities for specific domains.

## Available Skills

| Skill | Description |
|-------|-------------|
| `docx` | Generate and edit Word documents (.docx) with professional styling, charts, and track changes |
| `spec-coding` | Spec-driven workflow for complex development tasks with 5-phase planning and cross-session progress tracking |

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
└── spec-coding/            # Spec-driven complex development workflow skill
    └── SKILL.md            # 5-phase workflow definition
```

## Quick Start

### Using the docx Skill

```bash
# Check environment
<skill-path>/docx/scripts/docx env

# Initialize workspace
<skill-path>/docx/scripts/docx init

# Build and validate
<skill-path>/docx/scripts/docx build

# Validate a specific file
<skill-path>/docx/scripts/docx validate <file.docx>
```

### Running Tests

```bash
cd docx/scripts
pytest tests/ -v                    # Run all tests
pytest tests/test_validate_docx.py  # Run specific test file
```

## Development Notes

- `.claude/` directory is gitignored — do not commit
- `docx/validator/` contains pre-compiled binaries — do not modify
- `__pycache__/` and `.pyc` files are build artifacts
- When editing documents: always verify with `pandoc <file.docx> -t markdown --track-changes=all`

## License

MIT License
