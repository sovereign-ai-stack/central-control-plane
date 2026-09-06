"""
Request throttling and concurrency capping.

The audit found no throttle anywhere: one authenticated caller could saturate
embedding CPU and exhaust the vector store's connection pool, which on a GPU
model is direct cost amplification.

Two complementary controls, because they defend against different things:

- **Token bucket** limits the *rate* of requests, absorbing bursts while
  bounding sustained load.
- **Concurrency limiter** caps how many embeddings run *at once*. Rate alone
  does not protect a GPU: a handful of simultaneous large batches saturates it
  regardless of how few requests per minute arrived.

Keying: buckets are keyed on a **hash of the credential**, never the raw token,
so the limiter never holds secrets in memory. Enforcement sits at the handler
boundary, ahead of identity resolution, so it also protects the auth path.

Per-IP limiting is deliberately out of scope here — this layer has no socket and
cannot see one. That belongs at the ingress/proxy, and is noted in the config.
"""

from __future__ import annotations

import hashlib
import logging
import math
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

import yaml

logger = logging.getLogger(__name__)

ANONYMOUS_KEY = "anonymous"

# Bounded so an attacker rotating credentials cannot grow the limiter itself
# into a memory-exhaustion vector.
DEFAULT_MAX_TRACKED_KEYS = 10_000


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: float = 0.0
    remaining: float = 0.0

    @property
    def retry_after(self) -> int:
        """Whole seconds, rounded up — never advertise a too-early retry."""
        return max(1, math.ceil(self.retry_after_seconds)) if not self.allowed else 0


class TokenBucket:
    """
    Classic token bucket: `capacity` burst, refilled at `refill_per_second`.

    Uses a monotonic clock so a system clock change cannot grant free capacity.
    """

    __slots__ = ("_capacity", "_refill", "_tokens", "_updated")

    def __init__(self, capacity: float, refill_per_second: float, now: float) -> None:
        self._capacity = capacity
        self._refill = refill_per_second
        self._tokens = capacity
        self._updated = now

    def consume(self, now: float, amount: float = 1.0) -> RateLimitDecision:
        elapsed = max(0.0, now - self._updated)
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill)
        self._updated = now

        if self._tokens >= amount:
            self._tokens -= amount
            return RateLimitDecision(allowed=True, remaining=self._tokens)

        deficit = amount - self._tokens
        wait = deficit / self._refill if self._refill > 0 else float("inf")
        return RateLimitDecision(
            allowed=False, retry_after_seconds=wait, remaining=self._tokens
        )


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    enabled: bool = True
    # Sustained rate and burst allowance for authenticated callers.
    requests_per_minute: int = 120
    burst: int = 240
    # Ingestion is far heavier than retrieval (extraction + chunking + N
    # embeddings), so it gets its own, lower budget.
    ingest_requests_per_minute: int = 20
    ingest_burst: int = 40
    # Unauthenticated traffic shares one bucket; real per-client limiting for
    # anonymous callers requires an IP and belongs at the ingress.
    anonymous_requests_per_minute: int = 30
    anonymous_burst: int = 60
    max_tracked_keys: int = DEFAULT_MAX_TRACKED_KEYS
    # Simultaneous embedding operations. Rate limiting alone does not protect a
    # GPU from concurrent large batches.
    max_concurrent_embeddings: int = 8
    embedding_wait_seconds: float = 10.0

    def validate(self) -> None:
        from rag.app.errors import ApiValidationError

        positive = {
            "requests_per_minute": self.requests_per_minute,
            "burst": self.burst,
            "ingest_requests_per_minute": self.ingest_requests_per_minute,
            "ingest_burst": self.ingest_burst,
            "anonymous_requests_per_minute": self.anonymous_requests_per_minute,
            "anonymous_burst": self.anonymous_burst,
            "max_tracked_keys": self.max_tracked_keys,
            "max_concurrent_embeddings": self.max_concurrent_embeddings,
        }
        for name, value in positive.items():
            if value <= 0:
                raise ApiValidationError(f"{name} must be positive")
        if self.burst < self.requests_per_minute:
            # A burst below the sustained rate would throttle steady traffic.
            raise ApiValidationError("burst must be >= requests_per_minute")
        if self.embedding_wait_seconds < 0:
            raise ApiValidationError("embedding_wait_seconds must not be negative")


def credential_key(bearer_token: str | None) -> str:
    """
    Bucket key for a credential.

    Hashed so the limiter never stores a usable token, and truncated because a
    collision only shares a rate budget, never authority.
    """
    if not bearer_token:
        return ANONYMOUS_KEY
    return hashlib.sha256(bearer_token.encode("utf-8")).hexdigest()[:32]


class RateLimiter:
    """
    Per-key token buckets with bounded memory.

    Least-recently-used keys are evicted once `max_tracked_keys` is reached.
    Eviction can only ever *grant* a fresh budget, never revoke one, so it is
    safe under adversarial key rotation — the memory bound is the point.
    """

    def __init__(
        self,
        config: RateLimitConfig | None = None,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._config = config or RateLimitConfig()
        self._config.validate()
        self._clock = clock or time.monotonic
        self._buckets: OrderedDict[tuple[str, str], TokenBucket] = OrderedDict()
        self._lock = threading.Lock()

    @property
    def config(self) -> RateLimitConfig:
        return self._config

    @property
    def tracked_keys(self) -> int:
        return len(self._buckets)

    def check(self, bearer_token: str | None, *, scope: str = "read") -> RateLimitDecision:
        """
        Consume one token for `scope`. Does not raise — callers decide.

        Scopes have separate budgets so heavy ingestion cannot starve retrieval.
        """
        if not self._config.enabled:
            return RateLimitDecision(allowed=True)

        key = credential_key(bearer_token)
        capacity, refill = self._limits_for(key, scope)
        now = self._clock()

        with self._lock:
            bucket = self._buckets.get((key, scope))
            if bucket is None:
                bucket = TokenBucket(capacity, refill, now)
                self._buckets[(key, scope)] = bucket
                self._evict_if_needed()
            else:
                self._buckets.move_to_end((key, scope))
            decision = bucket.consume(now)

        if not decision.allowed:
            # Log the scope and hashed key only — never the credential.
            logger.warning("rate limit exceeded for scope=%s key=%s", scope, key[:8])
        return decision

    def enforce(self, bearer_token: str | None, *, scope: str = "read") -> None:
        """Raise `ApiRateLimitError` when the caller is over budget."""
        from rag.app.errors import ApiRateLimitError

        decision = self.check(bearer_token, scope=scope)
        if not decision.allowed:
            raise ApiRateLimitError(
                "rate limit exceeded", retry_after=decision.retry_after
            )

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()

    def _limits_for(self, key: str, scope: str) -> tuple[float, float]:
        config = self._config
        if key == ANONYMOUS_KEY:
            per_minute, burst = (
                config.anonymous_requests_per_minute,
                config.anonymous_burst,
            )
        elif scope == "ingest":
            per_minute, burst = config.ingest_requests_per_minute, config.ingest_burst
        else:
            per_minute, burst = config.requests_per_minute, config.burst
        return float(burst), per_minute / 60.0

    def _evict_if_needed(self) -> None:
        while len(self._buckets) > self._config.max_tracked_keys:
            self._buckets.popitem(last=False)


class ConcurrencyLimiter:
    """
    Caps simultaneous work, e.g. embedding batches.

    A rate limit bounds arrivals; this bounds what runs at once, which is what
    actually saturates a CPU or GPU.
    """

    def __init__(self, max_concurrent: int, wait_seconds: float = 10.0) -> None:
        if max_concurrent <= 0:
            raise ValueError("max_concurrent must be positive")
        self._semaphore = threading.BoundedSemaphore(max_concurrent)
        self._wait_seconds = wait_seconds
        self._max_concurrent = max_concurrent

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    def __enter__(self) -> Self:
        from rag.app.errors import ApiRateLimitError

        acquired = self._semaphore.acquire(timeout=self._wait_seconds)
        if not acquired:
            logger.warning(
                "embedding concurrency limit (%d) exceeded", self._max_concurrent
            )
            raise ApiRateLimitError(
                "service is at capacity",
                retry_after=max(1, int(self._wait_seconds)),
            )
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._semaphore.release()


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "config").is_dir():
            return parent
        if (parent / "rag" / "config").is_dir():
            return parent / "rag"
    return current.parents[1]


def load_rate_limit_config(path: Path | None = None) -> RateLimitConfig:
    config_path = path or _repo_root() / "config" / "rate_limit.yaml"
    if not config_path.exists():
        return RateLimitConfig()
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        return RateLimitConfig()
    block = raw.get("rate_limit", raw)
    if not isinstance(block, dict):
        return RateLimitConfig()
    config = _from_mapping(block)
    config.validate()
    return config


def _from_mapping(block: dict[str, Any]) -> RateLimitConfig:
    defaults = RateLimitConfig()
    return RateLimitConfig(
        enabled=bool(block.get("enabled", defaults.enabled)),
        requests_per_minute=int(
            block.get("requests_per_minute", defaults.requests_per_minute)
        ),
        burst=int(block.get("burst", defaults.burst)),
        ingest_requests_per_minute=int(
            block.get("ingest_requests_per_minute", defaults.ingest_requests_per_minute)
        ),
        ingest_burst=int(block.get("ingest_burst", defaults.ingest_burst)),
        anonymous_requests_per_minute=int(
            block.get(
                "anonymous_requests_per_minute", defaults.anonymous_requests_per_minute
            )
        ),
        anonymous_burst=int(block.get("anonymous_burst", defaults.anonymous_burst)),
        max_tracked_keys=int(block.get("max_tracked_keys", defaults.max_tracked_keys)),
        max_concurrent_embeddings=int(
            block.get("max_concurrent_embeddings", defaults.max_concurrent_embeddings)
        ),
        embedding_wait_seconds=float(
            block.get("embedding_wait_seconds", defaults.embedding_wait_seconds)
        ),
    )
