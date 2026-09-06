"""
Backend-agnostic `IdentityStore` conformance suite (Phase 7).

Both the in-memory and SQLite stores must behave identically, including error
types, since authorization decisions depend on them. Adds a durability section
and security assertions about token storage.
"""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest

from rag.identity.provider import StoreIdentityProvider
from rag.identity.sqlite_store import (
    MIGRATIONS,
    SqliteIdentityStore,
    SqlitePermissionRegistry,
)
from rag.identity.store import (
    CompanyRecord,
    DepartmentRecord,
    EntityStatus,
    IdentityStore,
    InMemoryIdentityStore,
    UserRecord,
    hash_token,
    utc_now,
)
from rag.ingestion.authz import IngestPermissionRegistry, PermissionRegistry
from rag.storage.db import SqliteDatabase

BACKENDS = ["in_memory", "sqlite"]
RAW_TOKEN = "tok_live_example_value"


@pytest.fixture(params=BACKENDS, ids=BACKENDS)
def store(request, tmp_path) -> IdentityStore:
    if request.param == "in_memory":
        return InMemoryIdentityStore()
    database = SqliteDatabase(tmp_path / "identity.db", migrations=MIGRATIONS)
    backend = SqliteIdentityStore(database)
    request.addfinalizer(backend.close)
    return backend


@pytest.fixture
def seeded(store):
    company = uuid4()
    other_company = uuid4()
    dept_a, dept_b = uuid4(), uuid4()
    user = uuid4()

    store.register_company(CompanyRecord(id=company))
    store.register_company(CompanyRecord(id=other_company))
    store.register_department(DepartmentRecord(id=dept_a, company_id=company))
    store.register_department(DepartmentRecord(id=dept_b, company_id=company))
    store.register_user(UserRecord(id=user, company_id=company), [dept_a, dept_b])
    store.register_token(uuid4(), user, RAW_TOKEN)
    return {
        "company": company,
        "other_company": other_company,
        "dept_a": dept_a,
        "dept_b": dept_b,
        "user": user,
    }


class TestProtocolConformance:
    def test_store_satisfies_the_protocol(self, store):
        assert isinstance(store, IdentityStore)

    def test_company_round_trip(self, store, seeded):
        company = store.get_company(seeded["company"])
        assert company is not None
        assert company.status == EntityStatus.ACTIVE

    def test_department_round_trip(self, store, seeded):
        department = store.get_department(seeded["dept_a"])
        assert department is not None
        assert department.company_id == seeded["company"]

    def test_user_round_trip(self, store, seeded):
        user = store.get_user(seeded["user"])
        assert user is not None
        assert user.company_id == seeded["company"]
        assert user.status == EntityStatus.ACTIVE

    def test_unknown_entities_are_none(self, store):
        assert store.get_user(uuid4()) is None
        assert store.get_company(uuid4()) is None
        assert store.get_department(uuid4()) is None

    def test_entity_status_is_preserved(self, store):
        disabled = uuid4()
        company = uuid4()
        store.register_company(CompanyRecord(id=company, status=EntityStatus.SUSPENDED))
        store.register_user(
            UserRecord(id=disabled, company_id=company, status=EntityStatus.DISABLED), []
        )
        assert store.get_user(disabled).status == EntityStatus.DISABLED
        assert store.get_company(company).status == EntityStatus.SUSPENDED

    def test_department_membership_order_is_stable(self, store, seeded):
        assert store.department_ids_for_user(seeded["user"]) == (
            seeded["dept_a"],
            seeded["dept_b"],
        )

    def test_user_without_departments(self, store):
        company, user = uuid4(), uuid4()
        store.register_company(CompanyRecord(id=company))
        store.register_user(UserRecord(id=user, company_id=company), [])
        assert store.department_ids_for_user(user) == ()

    def test_re_registering_a_user_replaces_memberships(self, store, seeded):
        # A revoked department must not linger as a stale grant.
        store.register_user(
            UserRecord(id=seeded["user"], company_id=seeded["company"]),
            [seeded["dept_a"]],
        )
        assert store.department_ids_for_user(seeded["user"]) == (seeded["dept_a"],)

    def test_ping_reports_healthy(self, store):
        assert store.ping() is True


class TestTokenHandling:
    def test_lookup_by_raw_token(self, store, seeded):
        record = store.lookup_token(RAW_TOKEN)
        assert record is not None
        assert record.user_id == seeded["user"]

    def test_unknown_token_is_none(self, store, seeded):
        assert store.lookup_token("tok_not_registered") is None

    def test_only_the_hash_is_stored(self, store, seeded):
        record = store.lookup_token(RAW_TOKEN)
        assert record.token_hash == hash_token(RAW_TOKEN)
        assert RAW_TOKEN not in record.token_hash

    def test_expiry_and_revocation_round_trip(self, store, seeded):
        expired_token = "tok_expired"
        revoked_token = "tok_revoked"
        moment = utc_now() - timedelta(days=1)
        store.register_token(uuid4(), seeded["user"], expired_token, expires_at=moment)
        store.register_token(uuid4(), seeded["user"], revoked_token, revoked_at=moment)

        assert store.lookup_token(expired_token).expires_at is not None
        assert store.lookup_token(revoked_token).revoked_at is not None

    def test_timestamps_are_timezone_aware(self, store, seeded):
        moment = utc_now() - timedelta(hours=2)
        store.register_token(uuid4(), seeded["user"], "tok_tz", expires_at=moment)
        assert store.lookup_token("tok_tz").expires_at.tzinfo is not None


class TestMembershipValidation:
    def test_valid_membership_returns_departments(self, store, seeded):
        assert store.validate_user_memberships(seeded["user"], seeded["company"]) == (
            seeded["dept_a"],
            seeded["dept_b"],
        )

    def test_unknown_user_raises_keyerror(self, store):
        with pytest.raises(KeyError):
            store.validate_user_memberships(uuid4(), uuid4())

    def test_company_mismatch_raises_valueerror(self, store, seeded):
        with pytest.raises(ValueError, match="company mismatch"):
            store.validate_user_memberships(seeded["user"], seeded["other_company"])

    def test_department_from_another_company_is_rejected(self, store, seeded):
        foreign_department = uuid4()
        store.register_department(
            DepartmentRecord(
                id=foreign_department, company_id=seeded["other_company"]
            )
        )
        store.register_user(
            UserRecord(id=seeded["user"], company_id=seeded["company"]),
            [foreign_department],
        )
        with pytest.raises(ValueError, match="does not belong"):
            store.validate_user_memberships(seeded["user"], seeded["company"])

    def test_unknown_department_is_rejected(self, store, seeded):
        store.register_user(
            UserRecord(id=seeded["user"], company_id=seeded["company"]), [uuid4()]
        )
        with pytest.raises(ValueError, match="unknown department"):
            store.validate_user_memberships(seeded["user"], seeded["company"])


class TestProviderIntegration:
    """`StoreIdentityProvider` must work against either backend."""

    def test_provider_reads_through_the_protocol(self, store, seeded):
        provider = StoreIdentityProvider(store)
        assert provider.get_user(seeded["user"]).id == seeded["user"]
        assert provider.get_company_status(seeded["company"]) == "active"
        assert provider.lookup_token(RAW_TOKEN).user_id == seeded["user"]
        assert provider.department_belongs_to_company(
            seeded["company"], seeded["dept_a"]
        )
        assert not provider.department_belongs_to_company(
            seeded["other_company"], seeded["dept_a"]
        )

    def test_provider_department_resolution(self, store, seeded):
        provider = StoreIdentityProvider(store)
        assert provider.department_ids_for_user(seeded["user"], seeded["company"]) == (
            seeded["dept_a"],
            seeded["dept_b"],
        )


class TestPermissionRegistry:
    @pytest.fixture(params=BACKENDS, ids=BACKENDS)
    def registry(self, request, tmp_path) -> PermissionRegistry:
        if request.param == "in_memory":
            return IngestPermissionRegistry()
        return SqlitePermissionRegistry(
            SqliteDatabase(tmp_path / "perm.db", migrations=MIGRATIONS)
        )

    def test_registry_satisfies_the_protocol(self, registry):
        assert isinstance(registry, PermissionRegistry)

    def test_grant_and_check(self, registry):
        user = uuid4()
        assert registry.is_company_wide(user) is False
        registry.grant_company_wide(user)
        assert registry.is_company_wide(user) is True

    def test_revoke(self, registry):
        user = uuid4()
        registry.grant_company_wide(user)
        registry.revoke_company_wide(user)
        assert registry.is_company_wide(user) is False

    def test_grant_is_idempotent(self, registry):
        user = uuid4()
        registry.grant_company_wide(user)
        registry.grant_company_wide(user)
        assert registry.is_company_wide(user) is True

    def test_ping(self, registry):
        assert registry.ping() is True


class TestDurability:
    def test_identity_survives_a_restart(self, tmp_path):
        path = tmp_path / "durable-identity.db"
        company, department, user = uuid4(), uuid4(), uuid4()

        first = SqliteIdentityStore(SqliteDatabase(path, migrations=MIGRATIONS))
        first.register_company(CompanyRecord(id=company))
        first.register_department(
            DepartmentRecord(id=department, company_id=company)
        )
        first.register_user(UserRecord(id=user, company_id=company), [department])
        first.register_token(uuid4(), user, RAW_TOKEN)
        first.close()

        second = SqliteIdentityStore(SqliteDatabase(path, migrations=MIGRATIONS))
        try:
            # This is the property whose absence caused an auth outage on restart.
            assert second.lookup_token(RAW_TOKEN).user_id == user
            assert second.get_user(user).company_id == company
            assert second.validate_user_memberships(user, company) == (department,)
        finally:
            second.close()

    def test_permissions_survive_a_restart(self, tmp_path):
        path = tmp_path / "durable-perm.db"
        user = uuid4()

        first = SqlitePermissionRegistry(SqliteDatabase(path, migrations=MIGRATIONS))
        first.grant_company_wide(user)

        second = SqlitePermissionRegistry(SqliteDatabase(path, migrations=MIGRATIONS))
        assert second.is_company_wide(user) is True

    def test_revocation_survives_a_restart(self, tmp_path):
        """A revoked token must stay revoked — the security-critical direction."""
        path = tmp_path / "durable-revoke.db"
        company, user = uuid4(), uuid4()

        first = SqliteIdentityStore(SqliteDatabase(path, migrations=MIGRATIONS))
        first.register_company(CompanyRecord(id=company))
        first.register_user(UserRecord(id=user, company_id=company), [])
        first.register_token(uuid4(), user, RAW_TOKEN)
        assert first.revoke_token(RAW_TOKEN) is True
        first.close()

        second = SqliteIdentityStore(SqliteDatabase(path, migrations=MIGRATIONS))
        try:
            assert second.lookup_token(RAW_TOKEN).revoked_at is not None
        finally:
            second.close()

    def test_in_memory_store_does_not_persist(self):
        company, user = uuid4(), uuid4()
        first = InMemoryIdentityStore()
        first.register_company(CompanyRecord(id=company))
        first.register_user(UserRecord(id=user, company_id=company), [])
        assert InMemoryIdentityStore().get_user(user) is None

    def test_raw_token_is_never_written_to_disk(self, tmp_path):
        """The database file must not contain the token in plaintext."""
        path = tmp_path / "token-safety.db"
        company, user = uuid4(), uuid4()
        store = SqliteIdentityStore(SqliteDatabase(path, migrations=MIGRATIONS))
        store.register_company(CompanyRecord(id=company))
        store.register_user(UserRecord(id=user, company_id=company), [])
        store.register_token(uuid4(), user, RAW_TOKEN)
        store.close()

        raw_bytes = path.read_bytes()
        assert RAW_TOKEN.encode() not in raw_bytes
        assert hash_token(RAW_TOKEN).encode() in raw_bytes
