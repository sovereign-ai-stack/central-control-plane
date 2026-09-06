from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from typing import Protocol, runtime_checkable
from uuid import UUID


def hash_token(raw_token: str) -> str:
    return sha256(raw_token.encode("utf-8")).hexdigest()


class EntityStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class CompanyRecord:
    id: UUID
    status: EntityStatus = EntityStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class DepartmentRecord:
    id: UUID
    company_id: UUID
    status: EntityStatus = EntityStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class UserRecord:
    id: UUID
    company_id: UUID
    status: EntityStatus = EntityStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class ApiTokenRecord:
    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime | None = None
    revoked_at: datetime | None = None


@runtime_checkable
class IdentityStore(Protocol):
    """
    Identity lookup boundary. Backend-agnostic.

    Accessor methods rather than exposed dictionaries: a database-backed store
    cannot hand out `dict` attributes, and `StoreIdentityProvider` previously
    reached into them directly.
    """

    def get_user(self, user_id: UUID) -> UserRecord | None:
        ...

    def get_company(self, company_id: UUID) -> CompanyRecord | None:
        ...

    def get_department(self, department_id: UUID) -> DepartmentRecord | None:
        ...

    def lookup_token(self, raw_token: str) -> ApiTokenRecord | None:
        ...

    def department_ids_for_user(self, user_id: UUID) -> tuple[UUID, ...]:
        ...

    def validate_user_memberships(
        self, user_id: UUID, company_id: UUID
    ) -> tuple[UUID, ...]:
        ...

    def register_company(self, company: CompanyRecord) -> None:
        ...

    def register_department(self, department: DepartmentRecord) -> None:
        ...

    def register_user(self, user: UserRecord, department_ids: Iterable[UUID]) -> None:
        ...

    def register_token(
        self,
        token_id: UUID,
        user_id: UUID,
        raw_token: str,
        *,
        expires_at: datetime | None = None,
        revoked_at: datetime | None = None,
    ) -> None:
        ...

    def ping(self) -> bool:
        ...


@dataclass
class InMemoryIdentityStore:
    """Deterministic in-memory identity store for tests and local development."""

    companies: dict[UUID, CompanyRecord] = field(default_factory=dict)
    departments: dict[UUID, DepartmentRecord] = field(default_factory=dict)
    users: dict[UUID, UserRecord] = field(default_factory=dict)
    user_departments: dict[UUID, tuple[UUID, ...]] = field(default_factory=dict)
    tokens: dict[str, ApiTokenRecord] = field(default_factory=dict)

    def register_company(self, company: CompanyRecord) -> None:
        self.companies[company.id] = company

    def register_department(self, department: DepartmentRecord) -> None:
        self.departments[department.id] = department

    def register_user(self, user: UserRecord, department_ids: Iterable[UUID]) -> None:
        self.users[user.id] = user
        self.user_departments[user.id] = tuple(department_ids)

    def register_token(
        self,
        token_id: UUID,
        user_id: UUID,
        raw_token: str,
        *,
        expires_at: datetime | None = None,
        revoked_at: datetime | None = None,
    ) -> None:
        self.tokens[hash_token(raw_token)] = ApiTokenRecord(
            id=token_id,
            user_id=user_id,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
            revoked_at=revoked_at,
        )

    def get_user(self, user_id: UUID) -> UserRecord | None:
        return self.users.get(user_id)

    def get_company(self, company_id: UUID) -> CompanyRecord | None:
        return self.companies.get(company_id)

    def get_department(self, department_id: UUID) -> DepartmentRecord | None:
        return self.departments.get(department_id)

    def lookup_token(self, raw_token: str) -> ApiTokenRecord | None:
        return self.tokens.get(hash_token(raw_token))

    def ping(self) -> bool:
        return True

    def department_ids_for_user(self, user_id: UUID) -> tuple[UUID, ...]:
        return self.user_departments.get(user_id, ())

    def validate_user_memberships(self, user_id: UUID, company_id: UUID) -> tuple[UUID, ...]:
        user = self.get_user(user_id)
        if user is None:
            raise KeyError(f"unknown user: {user_id}")
        if user.company_id != company_id:
            raise ValueError("department company mismatch for user")
        department_ids = self.department_ids_for_user(user_id)
        for department_id in department_ids:
            department = self.get_department(department_id)
            if department is None:
                raise ValueError(f"unknown department: {department_id}")
            if department.company_id != company_id:
                raise ValueError("department does not belong to user's company")
        return department_ids


def utc_now() -> datetime:
    return datetime.now(UTC)
