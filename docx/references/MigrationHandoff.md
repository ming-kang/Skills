# DOCX Local-First Migration Handoff

This document summarizes what changed in the migration cycle, what was verified, and what remains intentionally out of scope.

## Scope Completed

- Replaced container-bound path defaults in `docx/scripts/docx` with local-first paths.
- Added portable Python interpreter resolution and unified Python invocation.
- Normalized template artifact handling to avoid tracking machine-specific `obj` metadata.
- Added regression coverage for XML tolerance, validation behavior, and editing smoke.
- Rewrote `docx/SKILL.md` to match tested local workflows and constraints.

## Final Verification Matrix (Windows Git Bash)

Commands executed:

```bash
./docx/scripts/docx env
./docx/scripts/docx init
./docx/scripts/docx build
./docx/scripts/docx validate "$HOME/.docx-skill/task7-minimal.docx"
python -m pytest docx/scripts/docx_lib/editing/tests/test_xml_tolerance.py \
  docx/scripts/docx_lib/editing/tests/test_editing_smoke.py \
  docx/scripts/tests/test_validation_pipeline.py
dotnet build docx/assets/templates/KimiDocx.csproj
```

Observed outcomes:

- `env`: pass
- `init`: pass
- `build`: reaches restore/compile/run, then fails when placeholder workspace `Program.cs` does not emit output
- `validate` on a generated minimal `.docx`: pass
- pytest matrix: pass (`14 passed`)
- template `dotnet build`: pass

## Supported Baseline After Migration

1. Local CLI workflow (`env`, `init`, `build`, `validate`) no longer depends on `/mnt` or `/tmp` conventions.
2. Python usage is portable and resolved at runtime (`DOCX_PYTHON` -> `python` -> `python3` -> `py -3`).
3. XML tolerance and validation code paths are regression-tested.
4. Editing API smoke path is regression-tested on a minimal `.docx`.

## Known Limits

1. Default workspace `Program.cs` is still a placeholder and does not generate a final `.docx` unless replaced with real implementation code.
2. `docx/validator/` remains a prebuilt binary dependency and is treated as opaque.
3. Optional features depending on `playwright` and `matplotlib` are not part of the required baseline.

## Operator Notes

- Use `docx/references/RegressionCommands.md` as the repeatable verification entrypoint.
- Keep generated template `bin/` and `obj/` outputs untracked.
