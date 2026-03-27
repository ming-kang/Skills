# Editing Guide

Focused reference for **editing existing `.docx` files** with `docx_lib.editing`. Use [`../SKILL.md`](../SKILL.md) for the shared Bash-first contract and common workflow entry, and use [`CreationGuide.md`](./CreationGuide.md) for new-document creation, TOC/layout/chart rules, and OpenXML build details.

This guide owns editing-specific depth only. It does not restate the full shell/platform contract from `SKILL.md`.

For local-first editing:

- Start from the task directory and follow the shared Bash CLI contract from `SKILL.md`
- Run `<skill-path>/scripts/docx preflight <input.docx>` before editing incoming external documents or templates
- Preserve the source document by default and write edits to a sibling `-edited` file
- Edit workspaces are visible under `./.docx-tmp/docx-edit-*` by default
- Workspace names follow `docx-<purpose>-<timestamp>-<pid>[-N]`, so editing runs appear as `docx-edit-...`
- Successful edits clean up by default; failed edits stay visible for debugging
- Relative paths resolve from the task root; on Windows Git Bash, `/c/...` and `C:\...` inputs normalize to the same absolute location before shell checks
- Add `<skill-path>/scripts` to `sys.path`, then import `docx_lib.editing`
- Validate the edited output with `<skill-path>/scripts/docx validate ...`, then confirm visible content with `pandoc`

### API-First Editing Principle

**Use `docx_lib.editing` for all editing operations.** Only manipulate raw XML (direct `<w:...>` element access) when `docx_lib.editing` does not cover the specific use case. If `python-docx` or `docx-js` seem necessary, treat them as a signal that the skill API is insufficient — report this gap rather than working around it with lower-quality libraries.

**Never fall back to `python-docx` or `docx-js`.** These libraries produce lower-quality output than direct OpenXML manipulation via `lxml` and can silently corrupt complex features (track changes, comments, styles, headers/footers). If the skill API lacks coverage for a needed operation, escalate the limitation rather than reaching for an inferior tool.

---

## 1. Quick Reference

### 1.1 Functions

| Function | Purpose |
|----------|---------|
| `edit_docx` | Preferred helper: optional preflight + default sibling `-edited.docx` output + `DocxContext` |
| `add_comment` | Add comment to paragraph with optional highlight |
| `reply_comment` | Reply to existing comment (threaded) |
| `resolve_comment` | Mark comment as resolved |
| `delete_comment` | Delete comment and all its replies |
| `insert_text` | Insert text at specific position (tracked) |
| `insert_paragraph` | Insert new paragraph after target (tracked) |
| `propose_deletion` | Mark text/paragraph for deletion (tracked) |
| `reject_insertion` | Reject another author's insertion |
| `restore_deletion` | Restore another author's deletion |
| `enable_track_changes` | Enable revision tracking in document |

### 1.2 Parameter Semantics

| Parameter | Meaning | Example |
|-----------|---------|---------|
| `para_text` | Text to locate the paragraph (partial OK, must be unique in document) | `"M-SVI index was"` |
| `comment` | Comment content (supports \\n for line breaks) | `"Please define M-SVI"` |
| `highlight` | Text to highlight for comment (optional, omit to highlight entire paragraph) | `"M-SVI"` |
| `after` | Insert new text after this string | `"method"` |
| `target` | Text to delete (if None, delete entire paragraph) | `"redundant phrase"` |
| `context` | Longer text containing target for disambiguation | `"使用的方法是"` |
| `comment_id` | ID returned by add_comment (string) | `"0"` |

### 1.3 Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `InvalidDocxError` | Preflight or package open failed before editing started | Run `<skill-path>/scripts/docx preflight <file.docx>` and inspect the preserved workspace |
| `DocxEditError` | Output path or package structure violates editing assumptions | Use a sibling `-edited.docx` output and keep input/output paths distinct |
| `ParagraphNotFoundError` | `para_text` not found in document | Use more/less specific text |
| `AmbiguousTextError` | Multiple paragraphs match `para_text` | Use more specific text or `context` |
| `CommentNotFoundError` | `comment_id` doesn't exist | Check ID from add_comment return |
| `ValueError` | `highlight`/`target` not found in paragraph | Verify text exists exactly |

### Recommended Workflow

Preferred scripted path for existing `.docx` inputs:

```python
from pathlib import Path
import sys

SKILL_PATH = Path(r"<skill-path>")
sys.path.insert(0, str(SKILL_PATH / "scripts"))

from docx_lib.editing import edit_docx, enable_track_changes, insert_text

with edit_docx("./report.docx", preflight=True) as ctx:
    enable_track_changes(ctx)
    insert_text(
        ctx,
        "Supports JSON format",
        after="JSON",
        new_text=" and XML",
    )

print("Edited file:", Path("./report-edited.docx").resolve())
```

Then verify from the same Bash shell:

```bash
<skill-path>/scripts/docx validate ./report-edited.docx
pandoc ./report-edited.docx -t markdown --track-changes=all
```

Use standalone `<skill-path>/scripts/docx preflight ./report.docx` when you want the normalization/debugging step to stay separate and visible.

If the task changes from editing an existing package to creating a new document or redesigning layout from scratch, stop here and switch to [`CreationGuide.md`](./CreationGuide.md).

### 1.4 Examples

```python
from pathlib import Path
import sys

SKILL_PATH = Path(r"<skill-path>")
sys.path.insert(0, str(SKILL_PATH / "scripts"))

from docx_lib.editing import (
    edit_docx,
    add_comment,
    reply_comment,
    propose_deletion,
    insert_text,
)

with edit_docx("./report.docx", preflight=True) as ctx:
    # Highlight a term
    cid = add_comment(ctx, "The API uses OAuth2 for authentication",
                      "Add a code example.",
                      highlight="OAuth2")

    # Highlight a long sentence
    add_comment(ctx, "The new caching layer reduces database queries by maintaining frequently accessed data in memory, which significantly improves response times for read-heavy workloads",
                "This claim needs benchmark data.",
                highlight="The new caching layer reduces database queries by maintaining frequently accessed data in memory, which significantly improves response times for read-heavy workloads")

    # Highlight entire paragraph (omit highlight parameter)
    add_comment(ctx, "This section describes the installation process",
                "Split into subsections.")

    # Reply to comment
    reply_comment(ctx, cid, "Will add example.")

    # Insert text
    insert_text(ctx, "Supports JSON format",
                after="JSON", new_text=" and XML")

    # Propose deletion
    propose_deletion(ctx, "This legacy feature will be removed",
                     target="legacy feature will be removed")
```

`<skill-path>` must point to this skill directory. For repo-local development from the repository root, `Path("./docx").resolve()` is the equivalent value. Use the same Bash CLI entry point for `preflight` and `validate` on macOS and on Windows Git Bash inside Claude Code, with relative paths resolving from the task root and `/c/...` / `C:\...` forms treated as the same location on Windows Git Bash.

`edit_docx(...)` is the preferred helper because it defaults to a sibling `-edited.docx` output and can run preflight inline. `DocxContext(input, output)` remains supported when you want explicit output naming or lower-level control.

### 1.5 Verification (Mandatory)

After editing, always verify:

```bash
pandoc ./report-edited.docx -t markdown --track-changes=all
```

Check for:
- `{++inserted text++}` — insertions
- `{--deleted text--}` — deletions
- `[text]{.comment-start id="0" author="Kimi"}` — comments

**If count mismatches expected edits, changes were not saved. Do not deliver.**

### 1.6 Workspace Controls

`edit_docx(input, preflight=True)` is the recommended entry point for most scripted edits. `DocxContext(input, output)` still works with the original two-argument form. For debugging or explicit workspace routing, use keyword-only overrides:

```python
with DocxContext(
    "./report.docx",
    "./report-edited.docx",
    task_root=".",
    work_root="./.docx-debug",
    keep_workspace=True,
    keep_failed_workspace=True,
) as ctx:
    insert_text(ctx, "Supports JSON format", after="JSON", new_text=" and XML")
```

| Control | Effect |
|---------|--------|
| `task_root=...` | Overrides the visible task root used to resolve relative workspace paths |
| `work_root=...` | Overrides the parent directory for `docx-edit-<timestamp>-<pid>[-N]` workspaces |
| `keep_workspace=True` | Retains successful edit workspaces |
| `keep_failed_workspace=False` | Opt out of the default keep-on-failure behavior |

If you do not pass keyword overrides, `DOCX_TASK_ROOT`, `DOCX_WORK_ROOT`, and `DOCX_KEEP_WORKSPACE` are still honored.

### 1.7 Preflight Before Editing

For existing user-provided `.docx` files, run preflight first so fixable OOXML ordering issues are normalized before `DocxContext(...)` touches the package:

```bash
<skill-path>/scripts/docx preflight ./report.docx
```

Possible outcomes:
- `clean` — no normalization changes were needed
- `fixable` — safe structural fixes were written in place
- `invalid` — unrecoverable issues remain; inspect the visible `./.docx-tmp/docx-preflight-*` workspace before attempting edits

`edit_docx(..., preflight=True)` uses this same preflight contract inline and raises `InvalidDocxError` if the package is still unsafe to edit.

---

## 2. Usage Patterns

### 2.1 Text Anchoring

This API uses **text as anchors** to locate positions. `insert_text` and `propose_deletion` modify paragraph text, which may invalidate anchors for subsequent operations. Plan operation order based on dependencies.

### 2.2 Highlight Selection

Highlight **what the comment is about**, not just where to anchor it. Flexibly choose word, phrase, clause, or sentence to ensure professionalism, accuracy, and readability.

When `highlight` is omitted, the entire paragraph is highlighted.

### 2.3 Disambiguation

When `highlight`, `after`, or `target` appears multiple times, use `context`:

```python
# Paragraph: "方法一很好。使用的方法是正确的。"
# Want second "方法"

add_comment(ctx, "使用的方法是正确的",
            "Which method?",
            highlight="方法",
            context="使用的方法是")  # Finds within this context
```

**Rules**:
- `context` must be unique in the paragraph
- Target text must be unique within `context`

### 2.4 Handling Others' Revisions

**Golden rule**: Never modify text inside another author's `<w:ins>` or `<w:del>`. Use nesting.

| Scenario | Function | Effect |
|----------|----------|--------|
| Reject their insertion | `reject_insertion(ctx, para_text, ins_text)` | Wraps their insertion in your deletion |
| Restore their deletion | `restore_deletion(ctx, para_text, del_text)` | Adds your insertion after their deletion |

### 2.5 Quality Standards

- **Minimal diff**: Change only what's necessary
- **Pair deletion with comment**: Always explain why content is removed
- **Match document language**: Chinese doc → Chinese comments

---

## 3. Troubleshooting

### 3.1 Common Errors

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `ParagraphNotFoundError` | Text doesn't exist or has extra spaces | Copy exact text from document |
| `AmbiguousTextError` | Text appears in multiple paragraphs | Use longer, more unique text |
| Comment not visible in Word | Verification not run | Run pandoc check before delivery |
| Reply not threaded | Wrong `comment_id` | Use ID returned by `add_comment` |

### 3.2 Verification Failed

If pandoc output doesn't show expected markers:

1. **Missing comments**: Check `add_comment` didn't raise error
2. **Missing revisions**: Ensure `enable_track_changes(ctx)` was called
3. **Wrong count**: Some edits failed silently — check each operation's target text exists
