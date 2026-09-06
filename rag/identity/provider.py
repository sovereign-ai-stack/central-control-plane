from __future__ import annotations

from typing import Protocol
from uuid import UUID

from rag.identity.store import ApiTokenRecord, IdentityStore, UserRecord


class IdentityProvider(Protocol):
    """Adapter boundary for identity lookup — swap for real DB/provider in production."""

    def get_user(self, user_id: UUID) -> UserRecord | None:
        ...

    def get_company_status(self, company_id: UUID) -> str | None:
        ...

    def lookup_token(self, raw_token: str) -> ApiTokenRecord | None:
        ...

    def department_ids_for_user(self, user_id: UUID, company_id: UUID) -> tuple[UUID, ...]:
        ...

    def department_belongs_to_company(self, company_id: UUID, department_id: UUID) -> bool:
        ...


class StoreIdentityProvider:
    """
    IdentityProvider backed by any `IdentityStore`.

    Depends on the protocol's accessors, not on concrete dictionaries, so the
    in-memory and SQLite stores are interchangeable here.
    """

    def __init__(self, store: IdentityStore) -> None:
        self._store = store

    @property
    def store(self) -> IdentityStore:
        return self._store

    def get_user(self, user_id: UUID) -> UserRecord | None:
        return self._store.get_user(user_id)

    def get_company_status(self, company_id: UUID) -> str | None:
        company = self._store.get_company(company_id)
        if company is None:
            return None
        return company.status.value

    def lookup_token(self, raw_token: str) -> ApiTokenRecord | None:
        return self._store.lookup_token(raw_token)

    def department_ids_for_user(self, user_id: UUID, company_id: UUID) -> tuple[UUID, ...]:
        return self._store.validate_user_memberships(user_id, company_id)

    def department_belongs_to_company(self, company_id: UUID, department_id: UUID) -> bool:
        department = self._store.get_department(department_id)
        return department is not None and department.company_id == company_id
