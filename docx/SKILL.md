---
name: docx
description: Local-first DOCX creation, editing, and validation workflow for Claude Code and Codex.
---

# DOCX Skill (Local-First)

This skill handles `.docx` work with a tested local workflow.
Use it when the user needs to create, edit, validate, or inspect Word documents.

## 1) Route By Intent

Choose one primary path first:

1. **Create new document**
Use C# OpenXML templates through `./scripts/docx`.

2. **Edit existing document**
Use Python + `lxml` editing APIs from `docx_lib.editing` to preserve structure and formatting.

3. **Validate existing document**
Run the script validator flow (`./scripts/docx validate <file.docx>`).

Do not mix creation and editing approaches in the same step unless the user explicitly asks.

## 2) Verified Command Workflow

Run commands from repository root:

```bash
./docx/scripts/docx env
./docx/scripts/docx init
./docx/scripts/docx build [optional-output-path]
./docx/scripts/docx validate <file.docx>
```

### Dependency Model

- Required: `dotnet`, one working Python interpreter
- Optional: `pandoc`, `playwright`, `matplotlib`

Python is auto-resolved in this order:

1. `DOCX_PYTHON` (if set)
2. `python`
3. `python3`
4. `py -3`

### Local Path Policy

Default local state root is `$HOME/.docx-skill`, with:

- workspace: `$HOME/.docx-skill/workspace`
- output: `$HOME/.docx-skill/output`

Optional overrides:

- `DOCX_STATE_DIR`
- `DOCX_WORK_DIR`
- `DOCX_OUTPUT_DIR`

The skill should not require fixed container paths.

## 3) Progressive Disclosure Execution

Keep the workflow concise first, then go deeper only when needed.

### Step A: Confirm task type

- New document generation
- Existing document modification
- Validation/debug only

### Step B: Apply the smallest reliable workflow

- For creation, initialize workspace and edit `Program.cs`.
- For editing, use `DocxContext` and editing APIs (comments/revisions).
- For validation, run script-level validation first, then drill into XML only on failure.

### Step C: Verify and report

- Report command outcomes and key failures directly.
- Do not claim support for behavior that was not executed.
- If output generation fails, state exact failure stage (`restore`, `compile`, `run`, `validate`).

## 4) Creation Path Rules

Use C# OpenXML templates under `docx/assets/templates/`.

Critical contract for generated programs:

```csharp
string outputFile = args.Length > 0 ? args[0] : /* local fallback */;
```

If `Program.cs` ignores `args[0]`, `./scripts/docx build` cannot verify output.

Current template baseline:

- `Program.cs` is a placeholder entrypoint.
- It demonstrates output-path contract but does not generate a full document by default.

## 5) Editing Path Rules

Use `docx/scripts/docx_lib/editing` APIs for existing documents:

- `DocxContext`
- comment operations (`add_comment`, `reply_comment`, `resolve_comment`, `delete_comment`)
- revision operations (`insert_text`, `insert_paragraph`, `propose_deletion`, `reject_insertion`, `restore_deletion`)

For complete patterns and edge cases, refer to:

- `docx/references/EditingGuide.md`

## 6) Validation Path Rules

Validation flow in `./scripts/docx validate`:

1. `validate_all.py` for XML order fixes + business-rule checks
2. `validator/Validator.dll` for OpenXML validation

Treat `docx/validator/` as a vendored binary dependency.
Do not modify validator binaries unless explicitly tasked.

## 7) Quality Constraints

1. Preserve formatting when editing existing docs.
2. Prefer direct OpenXML / XML workflows over `python-docx` or `docx-js`.
3. Keep document language consistent with the user request unless asked otherwise.
4. Match output scope to user request; avoid adding decorative features by default.
5. Explicitly call out known limitations instead of silently degrading output quality.

## 8) Regression Reference

Use this checked-in command matrix for repeatable local verification:

- `docx/references/RegressionCommands.md`

It is the baseline for Windows Git Bash in this migration cycle.

## 9) Known Current Limits

1. `./scripts/docx build` can still fail at output existence check if workspace `Program.cs` is unchanged placeholder code.
2. Optional tools (`playwright`, `matplotlib`) are capability extensions, not required baseline.
3. End-to-end behavior should be considered supported only when covered by the regression command set.
