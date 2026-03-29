# Windows Git Bash Regression Commands

This command set is the local-first baseline for the current migration cycle.
Run commands from the repository root with Git Bash.

## Core CLI checks

```bash
./docx/scripts/docx env
./docx/scripts/docx init
./docx/scripts/docx build
```

Expected baseline during current migration:
- `env` and `init` should succeed.
- `build` currently reaches restore/compile/run and then fails if workspace `Program.cs` does not generate the requested output file.

## Python regression checks

```bash
python -m pytest docx/scripts/docx_lib/editing/tests/test_xml_tolerance.py
python -m pytest docx/scripts/docx_lib/editing/tests/test_editing_smoke.py
python -m pytest docx/scripts/tests/test_validation_pipeline.py
```

Optional combined run:

```bash
python -m pytest \
  docx/scripts/docx_lib/editing/tests/test_xml_tolerance.py \
  docx/scripts/docx_lib/editing/tests/test_editing_smoke.py \
  docx/scripts/tests/test_validation_pipeline.py
```

## Template smoke check

```bash
dotnet build docx/assets/templates/KimiDocx.csproj
```

This verifies template project compile health independently of `docx build`.
