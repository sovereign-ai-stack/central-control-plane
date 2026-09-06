from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from uuid import UUID


class IdentitySource(str, Enum):
    TRUSTED = "trusted"
    TOKEN = "token"


@dataclass(frozen=True, slots=True)
class TrustedIdentityPayload:
    """Semi-trusted payload from upstream platform — must pass verifier before use."""

    user_id: UUID
    company_id: UUID
    department_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class RagRetrieveRequest:
    """Inbound RAG retrieve request (identity fields only; query handled elsewhere)."""

    request_id: UUID
    query: str = ""
    trusted_identity: TrustedIdentityPayload | None = None


@dataclass(frozen=True, slots=True)
class IdentityContext:
    """Verified identity after resolution — input to AuthorizationContextBuilder."""

    user_id: UUID
    company_id: UUID
    department_ids: tuple[UUID, ...]
    source: IdentitySource
    request_id: UUID


class TrustedIdentityVerifier(Protocol):
    """Trust boundary for upstream identity payloads (mTLS/signature in production)."""

    def verify(self, payload: TrustedIdentityPayload, request_id: UUID) -> bool:
        """Return True if payload is authentic from the upstream auth platform."""
