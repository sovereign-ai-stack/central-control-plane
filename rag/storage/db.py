"""
SQLite connection management for the durable metadata stores.

Deliberately dependency-free: `sqlite3` is stdlib, so persistence adds no
package to the install. The seams here (parameterised SQL, a `Database`
abstraction, explicit migrations) are what make a PostgreSQL implementation a
second class rather than a rewrite.

Concurrency posture: **WAL journalling with one connection per thread.** WAL
allows concurrent readers alongside a single writer, and `busy_timeout` absorbs
writer contention instead of failing immediately. A thread-local connection
avoids sharing a `sqlite3.Connection` across threads, which the driver does not
support.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from rag.storage.errors import StorageBackendUnavailableError, StorageConfigurationError

MEMORY_PATH = ":memory:"
DEFAULT_BUSY_TIMEOUT_MS = 5_000


class SqliteDatabase:
    """
    A SQLite database with per-thread connections and applied migrations.

    `:memory:` is supported for tests, in which case a single shared connection
    is used because each new in-memory connection would otherwise get its own
    empty database.
    """

    def __init__(
        self,
        path: str | Path = MEMORY_PATH,
        *,
        migrations: Sequence[str] = (),
        busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS,
    ) -> None:
        self._path = str(path)
        self._is_memory = self._path == MEMORY_PATH
        self._busy_timeout_ms = busy_timeout_ms
        self._local = threading.local()
        self._shared: sqlite3.Connection | None = None
        self._write_lock = threading.Lock()

        if not self._is_memory:
            parent = Path(self._path).expanduser().resolve().parent
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise StorageConfigurationError(
                    f"cannot create database directory {parent}"
                ) from exc

        self._migrations = tuple(migrations)
        self._apply_migrations()

    @property
    def path(self) -> str:
        return self._path

    @property
    def is_memory(self) -> bool:
        return self._is_memory

    # ------------------------------------------------------------------
    # connections
    # ------------------------------------------------------------------

    def connection(self) -> sqlite3.Connection:
        """The calling thread's connection, opened on first use."""
        if self._is_memory:
            if self._shared is None:
                self._shared = self._connect()
            return self._shared
        existing = getattr(self._local, "connection", None)
        if existing is None:
            existing = self._connect()
            self._local.connection = existing
        return existing

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(
                self._path,
                timeout=self._busy_timeout_ms / 1000,
                check_same_thread=False,
                isolation_level=None,  # explicit transaction control
            )
        except sqlite3.Error as exc:
            raise StorageBackendUnavailableError(
                "could not open the metadata database"
            ) from exc

        connection.row_factory = sqlite3.Row
        # WAL permits concurrent readers with one writer; NORMAL is the
        # recommended durability pairing for WAL.
        if not self._is_memory:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute(f"PRAGMA busy_timeout={self._busy_timeout_ms}")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------

    def execute(self, sql: str, parameters: Sequence[Any] = ()) -> sqlite3.Cursor:
        try:
            return self.connection().execute(sql, tuple(parameters))
        except sqlite3.Error as exc:
            raise StorageBackendUnavailableError("database query failed") from exc

    def query_one(self, sql: str, parameters: Sequence[Any] = ()) -> sqlite3.Row | None:
        return self.execute(sql, parameters).fetchone()

    def query_all(self, sql: str, parameters: Sequence[Any] = ()) -> list[sqlite3.Row]:
        return list(self.execute(sql, parameters).fetchall())

    @contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        """
        A serialised write transaction.

        The lock keeps writers in this process from colliding; `busy_timeout`
        covers other processes. Any exception rolls the transaction back, so a
        failed multi-statement update never lands partially.
        """
        connection = self.connection()
        with self._write_lock:
            try:
                connection.execute("BEGIN IMMEDIATE")
            except sqlite3.Error as exc:
                raise StorageBackendUnavailableError(
                    "could not begin a database transaction"
                ) from exc
            try:
                yield connection
            except Exception:
                connection.execute("ROLLBACK")
                raise
            connection.execute("COMMIT")

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def _apply_migrations(self) -> None:
        if not self._migrations:
            return
        try:
            with self.write() as connection:
                for statement in self._migrations:
                    connection.execute(statement)
        except sqlite3.Error as exc:
            # A corrupt or unreadable file surfaces here; callers must see a
            # typed storage error, not a raw driver exception.
            raise StorageBackendUnavailableError(
                "could not initialise the metadata database"
            ) from exc

    def ping(self) -> bool:
        """Cheap liveness probe used by the readiness endpoint."""
        try:
            row = self.query_one("SELECT 1 AS ok")
        except StorageBackendUnavailableError:
            return False
        return bool(row is not None and row["ok"] == 1)

    def close(self) -> None:
        if self._shared is not None:
            self._shared.close()
            self._shared = None
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            self._local.connection = None
