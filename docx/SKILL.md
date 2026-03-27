---
name: docx
description: Generate and edit Word documents (.docx). Supports professional documents including covers, charts, track-changes editing, and more. Suitable for any .docx creation or modification task.
---

# Part 1: Quick Decisions

## When to Unzip vs Read

**To preserve ANY formatting from the source document, MUST unzip and parse XML.**

Read tool returns plain text only - fonts, colors, alignment, borders, styles are lost.

| Need | Method |
|------|--------|
| Text content only (summarize, analyze, translate) | Read tool is fine |
| Formatting info (copy styles, preserve layout, template filling) | Unzip and parse XML |
| Structure + comments/track changes | `pandoc input.docx -t markdown` |

## Core Principles

1. **Preserve formatting** - When editing existing documents, retain original formatting. Clone and modify, never recreate.
2. **Use the right stack** - C# OpenXML SDK for new-document creation, Python + lxml for existing-document editing.

**Never use python-docx/docx-js as fallback.** These libraries produce lower quality output than direct XML manipulation.

## Generator Script Lifecycle

Auxiliary scripts (`generate_backgrounds.py`, `generate_inkwash_backgrounds.py`, `generate_chart.py`) are optional helpers — not primary workflow entry points. They produce PNG image assets for use in document creation.

When agents use these scripts:
- **Explain what was produced** — e.g., "Generated background PNGs in `./`"
- **Explain local-only status** — PNGs are working files, not deliverables; they belong beside the task files
- **Offer cleanup** — When the user confirms the generated PNGs are no longer needed, delete them rather than leaving orphaned assets
- **Do not run these scripts unsolicited** — only invoke them when the document creation workflow genuinely calls for background or chart imagery

## Source Principle

**Template provided = Act as form-filler, not designer.**
- Format is the user's decision
- Task: replace placeholders, not redesign
- Like filling a PDF form - do not redesign

**No template = Act as designer.** Design freely based on scenario.

For `.doc` (legacy format), first convert with `libreoffice --headless --convert-to docx`.

## Choose the Smallest Relevant Path

| Need | Use | Read next |
|------|-----|-----------|
| Create a new document | Bash CLI + C# OpenXML SDK | [Creation Guide](./references/CreationGuide.md), `assets/templates/Example.cs`, `assets/templates/CJKExample.cs` |
| Edit an existing document | Bash CLI `preflight`/`validate` + `docx_lib.editing` | [Editing Guide](./references/EditingGuide.md) |
| Triage an incoming template or external `.docx` | `preflight` before editing or template-fill work | [Editing Guide](./references/EditingGuide.md) |
| Validate a finished document | `validate`, then `pandoc` for content verification | [Creation Guide](./references/CreationGuide.md) or [Editing Guide](./references/EditingGuide.md) |
| Build backgrounds or unsupported chart assets | Auxiliary scripts under `scripts/` | [Creation Guide](./references/CreationGuide.md) |

Do not broad-read everything by default. Pick the smallest relevant reference and stay there unless the task changes.

---

# Part 2: Supported Workflow

## Supported Shell Contract

- macOS: use Bash
- Windows inside Claude Code: use Git Bash and the same `<skill-path>/scripts/docx <command> [args]` entry point
- Run the CLI from the **task directory**, not from the skill directory
- Supported CLI entry point: `<skill-path>/scripts/docx <command> [args]`
- Relative paths resolve from the task directory / task root
- On Windows Git Bash, POSIX absolute paths like `/c/Users/name/report.docx` and drive-letter paths like `C:\Users\name\report.docx` normalize to the same absolute location before shell checks

`<skill-path>` is the actual local path to this skill directory.

**Mirrored Tree**: This skill ships as two identical copies at `docx/` and `.codex/skills/docx/`. Both trees must be kept in sync — any change to one must be applied to the other. Development-cycle tasks should verify sync before completion.

## Local-First Runtime Model

| Location | Default | Purpose |
|----------|---------|---------|
| Task root | current working directory | Base directory for relative input/output paths |
| Source workspace | `./.docx/` | Persistent place to edit `Program.cs` and `KimiDocx.csproj` |
| Temp work root | `./.docx-tmp/` | Per-run workspaces for build, preflight, validate, and edit operations |
| Create output | `./output.docx` | Unique sibling name if the default already exists |
| Edit output | sibling `-edited` file | Preserve the source `.docx` by default |

Successful runs remove the per-run workspace and remove the empty `./.docx-tmp/` root by default; failed runs stay visible for debugging.
Workspace names follow `docx-<purpose>-<timestamp>-<pid>[-N]`; the CLI build flow uses `docx-task-...`, while Python flows use labels such as `docx-preflight-...`, `docx-validate-all-...`, and `docx-edit-...`.

Environment overrides:
- `DOCX_TASK_ROOT`
- `DOCX_SOURCE_DIR`
- `DOCX_WORK_ROOT`
- `DOCX_OUTPUT_DIR`
- `DOCX_KEEP_WORKSPACE=1`
- `DOCX_ASSET_OUTPUT_DIR`

These overrides follow the same path contract: relative values resolve from the task root, and Windows Git Bash normalizes drive-letter inputs to POSIX shell paths before CLI file checks.

Local generated artifacts are not part of the shipped skill surface: source workspaces under `./.docx/`, temp workspaces under `./.docx-tmp/`, Python caches under `scripts/**/__pycache__/` or `.pytest_cache/`, template build outputs under `assets/templates/bin/` and `assets/templates/obj/`, and helper-generated PNG assets written beside the task or under `DOCX_ASSET_OUTPUT_DIR` should stay local-only and ignored.

## Command Set

| Command | Purpose |
|---------|---------|
| `env` | Show environment status (no changes) |
| `init` | Check dependencies and create `./.docx/` with template files |
| `build [out]` | Compile, run, validate, and write a local output file |
| `preflight FILE` | Normalize an incoming `.docx` and classify it as `clean`, `fixable`, or `invalid` before edit/build work |
| `validate FILE` | Validate an existing `.docx` resolved from the task root |

The CLI detects `dotnet`, the local OpenXML validator DLL, and `python`; reports `lxml` as required for Python editing; reports `pandoc` for visible-content verification and word counts; reports `playwright` plus Chromium for background asset scripts; and reports `matplotlib` plus `numpy` for chart asset scripts.

## Common Path: Create New Documents

```bash
cd <task-directory>
<skill-path>/scripts/docx env
<skill-path>/scripts/docx init
```

Then:
1. Edit `./.docx/Program.cs` and `./.docx/KimiDocx.csproj`
2. Use `assets/templates/Example.cs` for general structure or `assets/templates/CJKExample.cs` for CJK content
3. Run `<skill-path>/scripts/docx build [out]`
4. Verify content with `pandoc <generated-file>.docx -t plain`

Read next:
- [Creation Guide](./references/CreationGuide.md) for the build contract, validation flow, TOC/chart/layout details, and OpenXML reference
- `assets/templates/Example.cs` for full cover -> TOC -> body -> back-cover patterns
- `assets/templates/CJKExample.cs` for Chinese/CJK font and quote-escaping patterns

## Common Path: Edit Existing Documents

```bash
cd <task-directory>
<skill-path>/scripts/docx preflight ./report.docx
```

Then:
1. Use `edit_docx("./report.docx", preflight=True)` for the default sibling `-edited.docx` path, or `DocxContext(input, output)` for explicit control
2. Make comment / revision / insertion / deletion operations through `docx_lib.editing`
3. Run `<skill-path>/scripts/docx validate ./report-edited.docx`
4. Run `pandoc ./report-edited.docx -t markdown --track-changes=all`

Read next:
- [Editing Guide](./references/EditingGuide.md) for the editing API, workspace controls, verification, and troubleshooting

## Common Path: Validate or Triage Inputs

```bash
cd <task-directory>
<skill-path>/scripts/docx preflight ./incoming.docx
<skill-path>/scripts/docx validate ./incoming.docx
```

Use `preflight` before editing user-provided packages or template-fill work. Use `validate` on the output you plan to deliver. `pandoc` remains the source of truth for visible content.

## Reference Map

| Need | Smallest useful reference |
|------|---------------------------|
| Build contract, `Program.cs` output path, OpenXML rules, TOC, charts, layout | [Creation Guide](./references/CreationGuide.md) |
| Comments, revisions, `edit_docx`, `DocxContext`, editing workspaces, troubleshooting | [Editing Guide](./references/EditingGuide.md) |
| General document structure, sections, native chart patterns, headers/footers | `assets/templates/Example.cs` |
| CJK creation patterns | `assets/templates/CJKExample.cs` |
| Background-image HTML/CSS patterns and local PNG helpers (`DOCX_ASSET_OUTPUT_DIR`) | `scripts/generate_backgrounds.py`, `scripts/generate_inkwash_backgrounds.py` |
| matplotlib + numpy chart PNG helpers (`DOCX_ASSET_OUTPUT_DIR`) | `scripts/generate_chart.py` |
| Development cycle tasks on this skill (tightening, refactoring, verification) | Use the **spec-coding** workflow: `/spec-coding` — it manages analysis, planning, task tracking, and progress across the full development cycle |

---

# Part 3: Delivery Standard

## Universal Expectations

- **Document language = user conversation language** for filename, body text, headings, headers, TOC hints, chart labels, and every other visible string
- **Headers and footers are required by default** unless the scenario clearly should omit them; hide them on the cover with `TitlePage`
- **Preserve formatting when editing**; do not flatten an existing styled document into a generic rewrite
- **Do not mix creation and editing stacks casually**; create with C# OpenXML SDK, edit with Python + lxml

## Professional Completion Checklist

- Formal documents and creative deliverables should usually include a cover and back cover
- Documents with 3+ sections should add a TOC plus a refresh hint
- Prefer native Word charts for editable pie/bar/line-style visuals; use matplotlib only when the chart type is unsupported or genuinely more appropriate
- URLs must be clickable hyperlinks
- Multiple figures/tables should use numbering and cross-references
- Citation-heavy academic/legal/data-analysis work should implement the proper notes and jump targets instead of fake text references
- Generic Word defaults, high-saturation palettes, and mediocre styling are not acceptable output

## Content Constraints

- Specific word count: stay within +/-20%
- Specific page count: hit it exactly
- Range: stay inside the requested range
- Minimum: do not exceed 2x the requirement
- If the user gives an outline, follow it strictly
- If the user does not give an outline, pick a structure that matches the document type
- Think one step ahead for scenario completeness: signature blocks, attendee lists, grading areas, attachment lists, next-meeting info, and similar obvious requirements should not be omitted

## Deep References

- Use [Creation Guide](./references/CreationGuide.md) for TOC hint wording, chart-selection rules, color-direction ideas, pagination controls, formulas, headers/footers, and XML constraints
- Use [Editing Guide](./references/EditingGuide.md) for comments, revisions, anchor disambiguation, verification, and failure recovery
- Use the template files and auxiliary scripts only when they match the current task; do not force them into unrelated workflows
