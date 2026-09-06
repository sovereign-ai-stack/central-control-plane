"""
Shared audit trail.

Two problems with the previous ingestion-only log are fixed here:

1. **Retrieval was never audited.** `retrieval.executed` and
   `authz.chunk_blocked` are required by the security model but existed only in
   the specs. Without them there is no record of who read what, which is
   uninvestigable in a multi-tenant system.
2. **The log was an unbounded in-memory list.** It grew forever and vanished on
   restart. Events now also go through `logging`, so they reach whatever
   aggregator the deployment uses, and the in-process buffer is bounded.

**Never record raw queries or chunk content.** Audit records carry identifiers,
counts, and a query *hash* — enough to investigate an incident, not enough to
reconstruct the tenant's data from the log.
"""

from __future__ import annotations

import hashlib
import logging
from collections import deque
from collections.abc import Iterable
from uuid import UUID

from rag.ingestion.types import AuditEvent

logger = logging.getLogger("rag.audit")

DEFAULT_MAX_EVENTS = 1_000

EVENT_RETRIEVAL_EXECUTED = "retrieval.executed"
EVENT_CHUNK_BLOCKED = "authz.chunk_blocked"

# Fields that must never appear in an audit record.
FORBIDDEN_FIELDS = frozenset({"query", "content", "text", "embedding", "vector"})


def query_fingerprint(query: str) -> str:
    """SHA-256 of the query. The raw text is never stored."""
    return hashlib.sha256(query.encode("utf-8")).hexdigest()


class AuditLog:
    """
    Bounded in-process buffer plus structured logging.

    The buffer keeps the most recent events for tests and diagnostics; the
    logger is the durable path.
    """

    def __init__(self, max_events: int = DEFAULT_MAX_EVENTS) -> None:
        self._events: deque[AuditEvent] = deque(maxlen=max_events)

    @property
    def events(self) -> list[AuditEvent]:
        return list(self._events)

    def emit(self, name: str, request_id: UUID, **fields: object) -> None:
        self._reject_sensitive_fields(name, fields)
        event = AuditEvent(name=name, request_id=request_id, fields=fields)
        self._events.append(event)
        logger.info(
            "audit %s", name, extra={"audit_event": name, "request_id": str(request_id)}
        )

    def events_named(self, name: str) -> list[AuditEvent]:
        return [event for event in self._events if event.name == name]

    def clear(self) -> None:
        self._events.clear()

    @staticmethod
    def _reject_sensitive_fields(name: str, fields: dict[str, object]) -> None:
        """
        Fail loudly if a caller tries to audit raw content.

        A leak into the audit trail is a data leak with a long retention period,
        so this is enforced rather than documented.
        """
        offending = FORBIDDEN_FIELDS.intersection(fields)
        if offending:
            raise ValueError(
                f"audit event {name!r} must not carry raw content fields: "
                f"{sorted(offending)}"
            )


def emit_retrieval_executed(
    audit_log: AuditLog,
    *,
    request_id: UUID,
    user_id: UUID,
    company_id: UUID,
    department_count: int,
    query: str,
    candidate_count: int,
    returned_count: int,
    chunk_ids: Iterable[UUID],
    latency_ms: float,
) -> None:
    """Record a retrieval. Carries a query hash and chunk ids, never content."""
    audit_log.emit(
        EVENT_RETRIEVAL_EXECUTED,
        request_id,
        user_id=str(user_id),
        company_id=str(company_id),
        department_count=department_count,
        query_hash=query_fingerprint(query),
        candidate_count=candidate_count,
        returned_count=returned_count,
        chunk_ids=[str(value) for value in chunk_ids],
        latency_ms=round(latency_ms, 3),
    )


def emit_chunk_blocked(
    audit_log: AuditLog,
    *,
    request_id: UUID,
    user_id: UUID,
    company_id: UUID,
    blocked_chunk_ids: Iterable[UUID],
    reason: str,
) -> None:
    """
    Record chunks stripped by post-validation.

    Reaching this path means a store returned something outside the authorized
    scope, which is a critical signal: ids and a reason only, never content.
    """
    blocked = [str(value) for value in blocked_chunk_ids]
    audit_log.emit(
        EVENT_CHUNK_BLOCKED,
        request_id,
        user_id=str(user_id),
        company_id=str(company_id),
        blocked_chunk_ids=blocked,
        blocked_count=len(blocked),
        reason=reason,
    )
    logger.critical(
        "authz.chunk_blocked: %d chunk(s) outside authorized scope", len(blocked)
    )
