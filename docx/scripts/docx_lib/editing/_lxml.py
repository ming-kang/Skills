"""Shared lxml import with actionable dependency guidance."""

try:
    from lxml import etree
except ImportError as exc:
    raise ImportError(
        "docx_lib.editing requires the Python package 'lxml'. "
        "Install it with `python -m pip install lxml` before using DocxContext or editing helpers."
    ) from exc


__all__ = ["etree"]
