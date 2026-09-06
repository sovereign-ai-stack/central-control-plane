"""
Liveness and readiness checks.

The previous `/api/v1/health` returned a hardcoded 200, so an instance with a
dead vector store or an unloaded embedding model still reported healthy and kept
receiving traffic. This separates the two questions an orchestrator actually
asks:

- **liveness** — is the process alive? cheap, no I/O, never fails on a
  dependency (restarting the process would not fix a downstream outage)
- **readiness** — can this instance serve requests? probes every dependency and
  reports 503 if any is down, so the instance is removed from rotation instead
  of failing user requests

Each probe is isolated: one dead dependency cannot mask another's status, and a
probe that raises is reported as `down` rather than propagating.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

STATUS_OK = "ok"
STATUS_DOWN = "down"


class HealthStatus(str, Enum):
    OK = STATUS_OK
    DOWN = STATUS_DOWN


@dataclass(frozen=True, slots=True)
class DependencyHealth:
    name: str
    status: HealthStatus
    latency_ms: float
    detail: str | None = None

    @property
    def is_ok(self) -> bool:
        return self.status is HealthStatus.OK

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 3),
        }
        if self.detail is not None:
            payload["detail"] = self.detail
        return payload


@dataclass(frozen=True, slots=True)
class HealthReport:
    ready: bool
    dependencies: tuple[DependencyHealth, ...] = field(default_factory=tuple)

    @property
    def http_status(self) -> int:
        return 200 if self.ready else 503

    def to_dict(self) -> dict[str, object]:
        return {
            "status": STATUS_OK if self.ready else STATUS_DOWN,
            "dependencies": {
                dependency.name: dependency.to_dict()
                for dependency in self.dependencies
            },
        }


class HealthService:
    """Aggregates dependency probes into a readiness verdict."""

    def __init__(self, probes: dict[str, Callable[[], bool]] | None = None) -> None:
        self._probes: dict[str, Callable[[], bool]] = dict(probes or {})

    @property
    def dependency_names(self) -> tuple[str, ...]:
        return tuple(self._probes)

    def register(self, name: str, probe: Callable[[], bool]) -> None:
        self._probes[name] = probe

    def liveness(self) -> HealthReport:
        """The process is running. Deliberately independent of dependencies."""
        return HealthReport(ready=True)

    def readiness(self) -> HealthReport:
        results = [self._probe(name, probe) for name, probe in self._probes.items()]
        return HealthReport(
            ready=all(result.is_ok for result in results),
            dependencies=tuple(results),
        )

    @staticmethod
    def _probe(name: str, probe: Callable[[], bool]) -> DependencyHealth:
        started = time.perf_counter()
        try:
            healthy = bool(probe())
            detail = None
        except Exception as exc:  # noqa: BLE001 - a raising probe means "down"
            healthy = False
            # The class name is safe to surface; the message may carry
            # connection strings or credentials, so it is logged, not returned.
            detail = type(exc).__name__
            logger.warning("health probe %s failed: %s", name, detail)
        elapsed_ms = (time.perf_counter() - started) * 1000
        return DependencyHealth(
            name=name,
            status=HealthStatus.OK if healthy else HealthStatus.DOWN,
            latency_ms=elapsed_ms,
            detail=detail,
        )


def build_health_service(
    *,
    embedding_service: object | None = None,
    chunk_store: object | None = None,
    document_store: object | None = None,
    identity_store: object | None = None,
) -> HealthService:
    """Wire the standard dependency probes, skipping any that are absent."""
    probes: dict[str, Callable[[], bool]] = {}
    if embedding_service is not None:
        probes["embedding"] = embedding_service.health_check
    if chunk_store is not None:
        probes["chunk_store"] = _ping_probe(chunk_store)
    if document_store is not None:
        probes["document_store"] = _ping_probe(document_store)
    if identity_store is not None:
        probes["identity_store"] = _ping_probe(identity_store)
    return HealthService(probes)


def _ping_probe(store: object) -> Callable[[], bool]:
    ping = getattr(store, "ping", None)
    if callable(ping):
        return ping
    # A backend without a probe is reported healthy rather than blocking
    # readiness; it cannot be checked, so it must not be assumed broken.
    return lambda: True
