"""
Health and readiness tests (Phase 7).

The endpoint previously returned a hardcoded 200, so an instance with a dead
dependency still reported healthy. These assert the two questions an
orchestrator actually asks are answered separately and honestly.
"""

from __future__ import annotations

import pytest

from rag.app.health import (
    HealthService,
    HealthStatus,
    build_health_service,
)


class _Store:
    def __init__(self, healthy: bool = True, raises: bool = False) -> None:
        self._healthy = healthy
        self._raises = raises
        self.calls = 0

    def ping(self) -> bool:
        self.calls += 1
        if self._raises:
            raise ConnectionRefusedError("backend unreachable at 10.0.0.5:8080")
        return self._healthy


class TestLiveness:
    def test_liveness_is_ok_even_when_dependencies_are_down(self):
        service = HealthService({"chunk_store": lambda: False})
        report = service.liveness()
        assert report.ready is True
        assert report.http_status == 200

    def test_liveness_does_not_probe_dependencies(self):
        store = _Store()
        service = HealthService({"chunk_store": store.ping})
        service.liveness()
        # Restarting the process cannot fix a downstream outage, so liveness
        # must not depend on one.
        assert store.calls == 0


class TestReadiness:
    def test_all_healthy_is_ready(self):
        service = HealthService({"a": lambda: True, "b": lambda: True})
        report = service.readiness()
        assert report.ready is True
        assert report.http_status == 200
        assert all(dep.is_ok for dep in report.dependencies)

    def test_one_unhealthy_dependency_fails_readiness(self):
        service = HealthService({"embedding": lambda: True, "chunk_store": lambda: False})
        report = service.readiness()
        assert report.ready is False
        assert report.http_status == 503

    def test_raising_probe_is_reported_down_not_propagated(self):
        store = _Store(raises=True)
        service = HealthService({"chunk_store": store.ping})
        report = service.readiness()
        assert report.ready is False
        detail = report.to_dict()["dependencies"]["chunk_store"]
        assert detail["status"] == "down"
        assert detail["detail"] == "ConnectionRefusedError"

    def test_probe_failure_detail_never_leaks_connection_strings(self):
        store = _Store(raises=True)
        report = HealthService({"chunk_store": store.ping}).readiness()
        serialized = str(report.to_dict())
        assert "10.0.0.5" not in serialized
        assert "unreachable" not in serialized

    def test_one_dead_dependency_does_not_mask_the_others(self):
        service = HealthService(
            {
                "embedding": lambda: True,
                "chunk_store": lambda: False,
                "document_store": lambda: True,
            }
        )
        statuses = {
            dep.name: dep.status for dep in service.readiness().dependencies
        }
        assert statuses["embedding"] is HealthStatus.OK
        assert statuses["chunk_store"] is HealthStatus.DOWN
        assert statuses["document_store"] is HealthStatus.OK

    def test_every_dependency_is_probed(self):
        stores = {name: _Store() for name in ("a", "b", "c")}
        service = HealthService({name: s.ping for name, s in stores.items()})
        service.readiness()
        assert all(store.calls == 1 for store in stores.values())

    def test_latency_is_reported(self):
        report = HealthService({"a": lambda: True}).readiness()
        assert report.dependencies[0].latency_ms >= 0.0

    def test_no_dependencies_is_ready(self):
        assert HealthService().readiness().ready is True


class TestBuilder:
    def test_builds_probes_for_the_four_dependencies(self, rag_application):
        service = build_health_service(
            embedding_service=rag_application.embedding_service,
            chunk_store=rag_application.chunk_store,
            document_store=rag_application.document_store,
            identity_store=rag_application.identity_store,
        )
        assert set(service.dependency_names) == {
            "embedding",
            "chunk_store",
            "document_store",
            "identity_store",
        }

    def test_application_wires_all_four(self, rag_application):
        assert set(rag_application.health_service.dependency_names) == {
            "embedding",
            "chunk_store",
            "document_store",
            "identity_store",
        }

    def test_application_reports_ready(self, rag_application):
        assert rag_application.health_service.readiness().ready is True

    def test_absent_dependency_is_skipped(self):
        service = build_health_service(chunk_store=None, document_store=None)
        assert service.dependency_names == ()

    def test_backend_without_ping_is_not_assumed_broken(self):
        class NoProbe:
            pass

        service = build_health_service(chunk_store=NoProbe())
        assert service.readiness().ready is True


class TestRouterEndpoints:
    def test_liveness_route(self, rag_http_app):
        status, body = rag_http_app.dispatch("GET", "/api/v1/health", {})
        assert status == 200
        assert body["status"] == "ok"

    def test_readiness_route_reports_dependencies(
        self, retrieve_handler, rag_query_handler, rag_application
    ):
        from rag.app.router import RagHttpApplication

        app = RagHttpApplication(
            retrieve_handler,
            rag_query_handler,
            health_service=rag_application.health_service,
        )
        status, body = app.dispatch("GET", "/api/v1/health/ready", {})
        assert status == 200
        assert set(body["dependencies"]) == {
            "embedding",
            "chunk_store",
            "document_store",
            "identity_store",
        }

    def test_readiness_returns_503_when_a_dependency_is_down(
        self, retrieve_handler, rag_query_handler
    ):
        from rag.app.router import RagHttpApplication

        app = RagHttpApplication(
            retrieve_handler,
            rag_query_handler,
            health_service=HealthService({"chunk_store": lambda: False}),
        )
        status, body = app.dispatch("GET", "/api/v1/health/ready", {})
        assert status == 503
        assert body["status"] == "down"

    def test_health_routes_need_no_authentication(self, rag_http_app):
        # Probes come from infrastructure, not authenticated users.
        status, _ = rag_http_app.dispatch("GET", "/api/v1/health", {})
        assert status == 200

    def test_router_without_health_service_still_responds(
        self, retrieve_handler, rag_query_handler
    ):
        from rag.app.router import RagHttpApplication

        app = RagHttpApplication(retrieve_handler, rag_query_handler)
        assert app.dispatch("GET", "/api/v1/health", {})[0] == 200
        assert app.dispatch("GET", "/api/v1/health/ready", {})[0] == 200


class TestRealDependencyProbes:
    def test_document_store_ping(self, document_store):
        assert document_store.ping() is True

    def test_chunk_store_ping(self, chunk_store):
        assert chunk_store.ping() is True

    def test_identity_store_ping(self, identity_store):
        assert identity_store.ping() is True

    def test_embedding_health_check(self, embedding_service):
        assert embedding_service.health_check() is True

    def test_sqlite_store_ping_reconnects_after_close(self, tmp_path):
        """A closed connection is reopened, so a transient close is not fatal."""
        from rag.ingestion.store.sqlite_document_store import (
            MIGRATIONS,
            SqliteDocumentStore,
        )
        from rag.storage.db import SqliteDatabase

        store = SqliteDocumentStore(
            SqliteDatabase(tmp_path / "probe.db", migrations=MIGRATIONS)
        )
        assert store.ping() is True
        store.close()
        assert store.ping() is True
        store.close()

    def test_corrupt_database_raises_a_typed_storage_error(self, tmp_path):
        """A corrupt file must not surface as a raw driver exception."""
        from rag.ingestion.store.sqlite_document_store import MIGRATIONS
        from rag.storage.db import SqliteDatabase
        from rag.storage.errors import StorageBackendUnavailableError

        corrupt = tmp_path / "corrupt.db"
        corrupt.write_bytes(b"not a sqlite database" * 32)
        with pytest.raises(StorageBackendUnavailableError):
            SqliteDatabase(corrupt, migrations=MIGRATIONS)


@pytest.mark.parametrize("ready", [True, False])
def test_report_serialisation_round_trip(ready):
    service = HealthService({"a": lambda: ready})
    payload = service.readiness().to_dict()
    assert payload["status"] == ("ok" if ready else "down")
    assert "a" in payload["dependencies"]
