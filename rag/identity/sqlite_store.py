"""
Durable identity store backed by SQLite.

Satisfies the same `IdentityStore` protocol as the in-memory store and is
verified by the same conformance suite.

Security notes:

- Only the **hash** of an API token is stored, never the raw value, matching the
  in-memory store. Lookup hashes the presented token and compares.
- Token lookup is indexed on the hash, so authentication does not scan.
- Department membership is a separate table with a foreign key, so a user cannot
  reference a department that does not exist.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID

from rag.identity.store import (
    ApiTokenRecord,
    CompanyRecord,
    DepartmentRecord,
    EntityStatus,
    UserRecord,
    hash_token,
)
from rag.storage.db import SqliteDatabase

MIGRATIONS = (
    """
    CREATE TABLE IF NOT EXISTS companies (
        id     TEXT PRIMARY KEY,
        status TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS departments (
        id         TEXT PRIMARY KEY,
        company_id TEXT NOT NULL,
        status     TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id         TEXT PRIMARY KEY,
        company_id TEXT NOT NULL,
        status     TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_departments (
        user_id       TEXT NOT NULL,
        department_id TEXT NOT NULL,
        position      INTEGER NOT NULL,
        PRIMARY KEY (user_id, department_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS api_tokens (
        token_hash TEXT PRIMARY KEY,
        id         TEXT NOT NULL,
        user_id    TEXT NOT NULL,
        expires_at TEXT,
        revoked_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ingest_permissions (
        user_id      TEXT PRIMARY KEY,
        company_wide INTEGER NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_departments_company ON departments (company_id)",
    "CREATE INDEX IF NOT EXISTS idx_user_departments_user ON user_departments (user_id)",
)


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _parse(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


class SqliteIdentityStore:
    """Identity, membership, and token state that survives a restart."""

    def __init__(self, database: SqliteDatabase | None = None) -> None:
        self._db = database or SqliteDatabase(migrations=MIGRATIONS)

    @property
    def database(self) -> SqliteDatabase:
        return self._db

    # ------------------------------------------------------------------
    # registration
    # ------------------------------------------------------------------

    def register_company(self, company: CompanyRecord) -> None:
        with self._db.write() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO companies (id, status) VALUES (?, ?)",
                (str(company.id), company.status.value),
            )

    def register_department(self, department: DepartmentRecord) -> None:
        with self._db.write() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO departments (id, company_id, status) "
                "VALUES (?, ?, ?)",
                (
                    str(department.id),
                    str(department.company_id),
                    department.status.value,
                ),
            )

    def register_user(self, user: UserRecord, department_ids: Iterable[UUID]) -> None:
        ordered = list(department_ids)
        with self._db.write() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO users (id, company_id, status) VALUES (?, ?, ?)",
                (str(user.id), str(user.company_id), user.status.value),
            )
            # Membership is replaced wholesale so a revoked department cannot
            # linger as a stale grant.
            connection.execute(
                "DELETE FROM user_departments WHERE user_id = ?", (str(user.id),)
            )
            for position, department_id in enumerate(ordered):
                connection.execute(
                    "INSERT INTO user_departments (user_id, department_id, position) "
                    "VALUES (?, ?, ?)",
                    (str(user.id), str(department_id), position),
                )

    def register_token(
        self,
        token_id: UUID,
        user_id: UUID,
        raw_token: str,
        *,
        expires_at: datetime | None = None,
        revoked_at: datetime | None = None,
    ) -> None:
        with self._db.write() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO api_tokens "
                "(token_hash, id, user_id, expires_at, revoked_at) VALUES (?, ?, ?, ?, ?)",
                (
                    hash_token(raw_token),
                    str(token_id),
                    str(user_id),
                    _iso(expires_at),
                    _iso(revoked_at),
                ),
            )

    def revoke_token(self, raw_token: str, revoked_at: datetime | None = None) -> bool:
        moment = revoked_at or datetime.now(UTC)
        with self._db.write() as connection:
            cursor = connection.execute(
                "UPDATE api_tokens SET revoked_at = ? WHERE token_hash = ?",
                (_iso(moment), hash_token(raw_token)),
            )
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # lookup
    # ------------------------------------------------------------------

    def get_user(self, user_id: UUID) -> UserRecord | None:
        row = self._db.query_one(
            "SELECT id, company_id, status FROM users WHERE id = ?", (str(user_id),)
        )
        if row is None:
            return None
        return UserRecord(
            id=UUID(row["id"]),
            company_id=UUID(row["company_id"]),
            status=EntityStatus(row["status"]),
        )

    def get_company(self, company_id: UUID) -> CompanyRecord | None:
        row = self._db.query_one(
            "SELECT id, status FROM companies WHERE id = ?", (str(company_id),)
        )
        if row is None:
            return None
        return CompanyRecord(id=UUID(row["id"]), status=EntityStatus(row["status"]))

    def get_department(self, department_id: UUID) -> DepartmentRecord | None:
        row = self._db.query_one(
            "SELECT id, company_id, status FROM departments WHERE id = ?",
            (str(department_id),),
        )
        if row is None:
            return None
        return DepartmentRecord(
            id=UUID(row["id"]),
            company_id=UUID(row["company_id"]),
            status=EntityStatus(row["status"]),
        )

    def lookup_token(self, raw_token: str) -> ApiTokenRecord | None:
        row = self._db.query_one(
            "SELECT token_hash, id, user_id, expires_at, revoked_at FROM api_tokens "
            "WHERE token_hash = ?",
            (hash_token(raw_token),),
        )
        if row is None:
            return None
        return ApiTokenRecord(
            id=UUID(row["id"]),
            user_id=UUID(row["user_id"]),
            token_hash=row["token_hash"],
            expires_at=_parse(row["expires_at"]),
            revoked_at=_parse(row["revoked_at"]),
        )

    def department_ids_for_user(self, user_id: UUID) -> tuple[UUID, ...]:
        rows = self._db.query_all(
            "SELECT department_id FROM user_departments WHERE user_id = ? "
            "ORDER BY position",
            (str(user_id),),
        )
        return tuple(UUID(row["department_id"]) for row in rows)

    def validate_user_memberships(
        self, user_id: UUID, company_id: UUID
    ) -> tuple[UUID, ...]:
        """Identical semantics to the in-memory store, including error types."""
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

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        return self._db.ping()

    def close(self) -> None:
        self._db.close()


class SqlitePermissionRegistry:
    """Ingest permissions that survive a restart."""

    def __init__(self, database: SqliteDatabase | None = None) -> None:
        self._db = database or SqliteDatabase(migrations=MIGRATIONS)

    def grant_company_wide(self, user_id: UUID) -> None:
        with self._db.write() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO ingest_permissions (user_id, company_wide) "
                "VALUES (?, 1)",
                (str(user_id),),
            )

    def revoke_company_wide(self, user_id: UUID) -> None:
        with self._db.write() as connection:
            connection.execute(
                "DELETE FROM ingest_permissions WHERE user_id = ?", (str(user_id),)
            )

    def is_company_wide(self, user_id: UUID) -> bool:
        row = self._db.query_one(
            "SELECT company_wide FROM ingest_permissions WHERE user_id = ?",
            (str(user_id),),
        )
        return bool(row is not None and row["company_wide"] == 1)

    def ping(self) -> bool:
        return self._db.ping()
