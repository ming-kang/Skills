"""
docx_lib.editing - High-level API for docx editing operations.

Usage:
    from docx_lib.editing import (
        DocxContext, edit_docx,
        add_comment, reply_comment, resolve_comment, delete_comment,
        insert_paragraph, insert_text, propose_deletion,
        reject_insertion, restore_deletion, enable_track_changes
    )

    with edit_docx("input.docx", preflight=True) as ctx:
        add_comment(ctx, "M-SVI index", "Please define", highlight="M-SVI")
        insert_text(ctx, "The method", after="method", new_text=" and materials")
    # Automatically preflights, saves, and repacks to input-edited.docx

    with DocxContext("input.docx", "output.docx", work_root="debug-workspaces", keep_workspace=True) as ctx:
        insert_text(ctx, "The method", after="method", new_text=" and materials")
    # Optional keyword arguments keep successful editing workspaces visible for debugging
"""

from .context import (
    DocxContext,
    DocxEditError,
    ParagraphNotFoundError,
    AmbiguousTextError,
    CommentNotFoundError,
    InvalidDocxError,
)
from .workflow import default_edited_output_path, edit_docx
from .comments import (
    add_comment,
    reply_comment,
    resolve_comment,
    delete_comment,
)
from .revisions import (
    insert_paragraph,
    insert_text,
    propose_deletion,
    reject_insertion,
    restore_deletion,
    enable_track_changes,
)

__all__ = [
    # Context
    'DocxContext',
    # Exceptions
    'DocxEditError',
    'ParagraphNotFoundError',
    'AmbiguousTextError',
    'CommentNotFoundError',
    'InvalidDocxError',
    'default_edited_output_path',
    'edit_docx',
    # Comments
    'add_comment',
    'reply_comment',
    'resolve_comment',
    'delete_comment',
    # Revisions
    'insert_paragraph',
    'insert_text',
    'propose_deletion',
    'reject_insertion',
    'restore_deletion',
    'enable_track_changes',
]
