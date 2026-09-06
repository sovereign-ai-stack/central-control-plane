"""
Ingestion audit trail.

Retained as a compatibility alias: the implementation now lives in
`rag.audit.AuditLog`, which is shared with retrieval, bounded, and routed
through `logging`.
"""

from __future__ import annotations

from rag.audit import AuditLog

# Ingestion has always referred to this name; it is the same object now.
IngestAuditLog = AuditLog

__all__ = ["AuditLog", "IngestAuditLog"]
