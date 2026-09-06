"""
Weaviate connection management.

The client library is imported lazily so the rest of the system — and the whole
test suite on the in-memory backend — works without `weaviate-client` installed.
"""

from __future__ import annotations

from typing import Any

from rag.storage.config import WeaviateConfig
from rag.storage.errors import StorageBackendUnavailableError


def weaviate_available() -> bool:
    try:
        import weaviate  # noqa: F401
    except Exception:  # noqa: BLE001 - any import failure means unusable
        return False
    return True


def connect(config: WeaviateConfig) -> Any:
    """
    Open a connection using the supplied configuration.

    The API key is resolved from the environment here, never from config files.
    """
    try:
        import weaviate
        from weaviate.classes.init import Auth, Timeout
    except ImportError as exc:
        raise StorageBackendUnavailableError(
            "weaviate-client is not installed; install it or use the memory backend"
        ) from exc

    api_key = config.api_key()
    credentials = Auth.api_key(api_key) if api_key else None
    timeout = Timeout(
        init=config.timeout_init_seconds,
        query=config.timeout_query_seconds,
        insert=config.timeout_insert_seconds,
    )

    try:
        client = weaviate.connect_to_custom(
            http_host=config.host,
            http_port=config.http_port,
            http_secure=config.secure,
            grpc_host=config.host,
            grpc_port=config.grpc_port,
            grpc_secure=config.secure,
            auth_credentials=credentials,
            additional_config=weaviate.classes.init.AdditionalConfig(timeout=timeout),
        )
    except Exception as exc:
        raise StorageBackendUnavailableError(
            f"could not connect to Weaviate at {config.host}:{config.http_port}"
        ) from exc

    if not client.is_ready():
        client.close()
        raise StorageBackendUnavailableError(
            f"Weaviate at {config.host}:{config.http_port} is not ready"
        )
    return client


def consistency_level(name: str) -> Any:
    from weaviate.classes.config import ConsistencyLevel

    return getattr(ConsistencyLevel, name)
