"""GJB 438C Markdown-first document engineering suite."""

from .registry import DOCUMENT_TYPES, DocumentType, get_document_type
from .quality import audit_markdown
from .render import render_document
from .finalize import refresh_toc_cache

__all__ = [
    "DOCUMENT_TYPES",
    "DocumentType",
    "get_document_type",
    "audit_markdown",
    "render_document",
    "refresh_toc_cache",
]
__version__ = "0.2.0"
