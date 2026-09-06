"""
`WeaviateChunkStore` — production `ChunkStore` backed by Weaviate.

Isolation model (see schema.py for why):

    tenant       = company_id      -> native, shard-level isolation
    department   = server-side filter (ContainsAny over the authorized list)
    document     = server-side filter (ContainsAny over the authorized list)

All three are applied **inside the Weaviate query**. Nothing is filtered in
Python after the fact, and the adapter never constructs authorization scope of
its own — it receives an already-authorized `VectorSearchScope` and does exactly
what it says.

Consistency: Weaviate has no multi-object transactions (a probe confirmed a
partial batch commits). Atomicity is achieved by pairing client-side validation
with explicit compensation, and by relying on the existing document-status gate:
`SecureRetrievalEngine` only searches INDEXED documents, and a document is
PROCESSING for the whole of create/reindex, so intermediate vector state is never
reachable by a query.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, Self
from uuid import UUID

from rag.ingestion.types import StoredChunk
from rag.retrieval.errors import (
    RetrievalDimensionMismatchError,
    RetrievalModelMismatchError,
)
from rag.retrieval.ranking import rank_by_similarity
from rag.storage.chunk_validation import validate_chunk_batch
from rag.storage.config import WeaviateConfig
from rag.storage.errors import (
    StorageScopeTooLargeError,
    StorageWriteError,
)
from rag.storage.vector_search import (
    SEARCHABLE_DOCUMENT_STATUS,
    ScoredChunk,
    VectorSearchScope,
)
from rag.storage.weaviate.client import connect, consistency_level
from rag.storage.weaviate.mapping import (
    chunk_to_properties,
    chunk_to_vector,
    distance_to_similarity,
    properties_to_chunk,
    vector_from_object,
)
from rag.storage.weaviate.schema import (
    PROP_CHUNK_INDEX,
    PROP_DEPARTMENT_ID,
    PROP_DOCUMENT_ID,
    PROP_DOCUMENT_STATUS,
    PROP_EMBEDDING_DIMENSION,
    PROP_EMBEDDING_MODEL_ID,
    ensure_collection,
    tenant_name,
)

logger = logging.getLogger(__name__)


class WeaviateChunkStore:
    """Production chunk index. Satisfies the `ChunkStore` protocol."""

    def __init__(
        self,
        config: WeaviateConfig | None = None,
        *,
        client: Any = None,
        owns_client: bool | None = None,
    ) -> None:
        self._config = config or WeaviateConfig()
        self._config.validate()
        self._owns_client = owns_client if owns_client is not None else client is None
        self._client = client if client is not None else connect(self._config)
        self._collection = (
            ensure_collection(self._client, self._config.collection)
            if self._config.auto_create_collection
            else self._client.collections.get(self._config.collection)
        )
        # Document -> company, so delete/count can address the right tenant
        # without the caller having to supply scope for lifecycle operations.
        self._document_tenants: dict[UUID, str] = {}
        # Tenants are created once and never removed here, so a process-local
        # set avoids a network round trip on every store call.
        self._known_tenants: set[str] = set()

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    @property
    def config(self) -> WeaviateConfig:
        return self._config

    @property
    def client(self) -> Any:
        return self._client

    def ping(self) -> bool:
        """Round-trip the cluster so readiness reflects real connectivity."""
        try:
            return bool(self._client.is_ready())
        except Exception:  # noqa: BLE001 - any failure means "not ready"
            logger.warning("weaviate readiness probe failed")
            return False

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # writes
    # ------------------------------------------------------------------

    def replace_document_chunks(
        self,
        document_id: UUID,
        chunks: Sequence[StoredChunk],
    ) -> None:
        """
        Atomically swap a document's chunks.

        Weaviate offers no transaction, so this is validate -> insert -> commit,
        with compensation on failure:

        1. validate every chunk client-side (rejects the common failure modes
           before anything is written)
        2. record the pre-existing chunk ids
        3. insert the new chunks
        4. on failure, delete whatever was just inserted and re-raise, leaving
           the prior state intact
        5. on success, delete the superseded chunks
        """
        validate_chunk_batch(document_id, chunks)

        if not chunks:
            self.delete_by_document_id(document_id)
            return

        tenant = tenant_name(chunks[0].company_id)
        collection = self._tenant_collection(tenant)
        previous_ids = self._chunk_uuids_for_document(collection, document_id)
        new_ids = [chunk.chunk_id for chunk in chunks]

        try:
            self._insert_chunks(collection, chunks)
        except Exception as exc:
            self._compensate(collection, new_ids)
            raise StorageWriteError(
                "failed to persist document chunks; prior state was restored"
            ) from exc

        # Commit: drop superseded objects so no stale vector stays searchable.
        stale = [
            object_id for object_id in previous_ids if object_id not in set(new_ids)
        ]
        if stale:
            self._delete_by_ids(collection, stale)
        self._document_tenants[document_id] = tenant

    def delete_by_document_id(self, document_id: UUID) -> int:
        deleted = 0
        for tenant in self._candidate_tenants(document_id):
            collection = self._tenant_collection(tenant)
            result = collection.data.delete_many(
                where=self._document_filter(document_id)
            )
            deleted += int(getattr(result, "successful", 0) or 0)
        self._document_tenants.pop(document_id, None)
        return deleted

    def set_document_status(self, document_id: UUID, status: str) -> int:
        """
        Flip the searchability gate for a document's chunks.

        Weaviate has no bulk-update-by-filter, so this fetches the document's
        object ids and updates each. Failures propagate: a silent failure here
        would leave a document's searchability out of sync with its record.
        """
        updated = 0
        for tenant in self._candidate_tenants(document_id):
            collection = self._tenant_collection(tenant)
            for object_id in self._chunk_uuids_for_document(collection, document_id):
                collection.data.update(
                    uuid=object_id, properties={PROP_DOCUMENT_STATUS: status}
                )
                updated += 1
        return updated

    def count_by_document_id(self, document_id: UUID) -> int:
        total = 0
        for tenant in self._candidate_tenants(document_id):
            collection = self._tenant_collection(tenant)
            response = collection.aggregate.over_all(
                filters=self._document_filter(document_id), total_count=True
            )
            total += int(response.total_count or 0)
        return total

    def list_by_document_id(self, document_id: UUID) -> list[StoredChunk]:
        found: list[StoredChunk] = []
        for tenant in self._candidate_tenants(document_id):
            collection = self._tenant_collection(tenant)
            response = collection.query.fetch_objects(
                filters=self._document_filter(document_id),
                limit=self._fetch_all_limit(),
                include_vector=True,
            )
            for obj in response.objects:
                found.append(
                    properties_to_chunk(
                        dict(obj.properties),
                        embedding=vector_from_object(obj.vector),
                    )
                )
        found.sort(key=lambda chunk: chunk.chunk_index)
        return found

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------

    def search(
        self,
        query_vector,
        scope: VectorSearchScope,
        *,
        top_k: int,
        query_model_id: str,
        query_dimension: int,
    ) -> tuple[list[ScoredChunk], int]:
        if query_vector.ndim != 1 or query_vector.shape[0] != query_dimension:
            raise RetrievalDimensionMismatchError(
                f"query vector dimension {query_vector.shape} "
                f"does not match expected {query_dimension}"
            )

        # Fail closed on an empty scope: never issue an unrestricted query.
        # `allowed_document_ids is None` means "every INDEXED document in
        # scope"; an explicitly empty set means "nothing".
        if not scope.allowed_department_ids:
            return [], 0
        if scope.allowed_document_ids is not None and not scope.allowed_document_ids:
            return [], 0

        self._guard_scope_size(scope)
        collection = self._tenant_collection(tenant_name(scope.company_id))
        scope_filter = self._scope_filter(scope)

        if self._config.verify_model_compatibility:
            self._assert_compatible(
                collection, scope_filter, query_model_id, query_dimension
            )

        pool_size = int(
            collection.aggregate.over_all(
                filters=self._compatible_filter(
                    scope_filter, query_model_id, query_dimension
                ),
                total_count=True,
            ).total_count
            or 0
        )
        if pool_size == 0:
            return [], 0

        # HNSW is approximate and does not define tie order, so over-fetch and
        # re-rank deterministically before truncating to top_k.
        limit = min(max(top_k * self._config.overfetch_factor, top_k), pool_size)
        response = collection.query.near_vector(
            near_vector=[float(value) for value in query_vector],
            limit=limit,
            filters=self._compatible_filter(
                scope_filter, query_model_id, query_dimension
            ),
            return_metadata=self._distance_metadata(),
            # Vectors are never needed for retrieval output and must not be
            # exposed; leaving this off also keeps the payload small.
            include_vector=False,
        )

        scored: list[tuple[StoredChunk, float, UUID]] = []
        for obj in response.objects:
            chunk = properties_to_chunk(dict(obj.properties))
            self._assert_object_scope(chunk, scope)
            similarity = distance_to_similarity(
                getattr(obj.metadata, "distance", None)
            )
            scored.append((chunk, similarity, chunk.chunk_id))

        ranked = rank_by_similarity(scored, top_k=top_k)
        results = [ScoredChunk(chunk=item[0], score=item[1]) for item in ranked]
        return results, pool_size

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _tenant_collection(self, tenant: str) -> Any:
        if self._config.auto_create_tenants:
            self._ensure_tenant(tenant)
        return self._collection.with_tenant(tenant).with_consistency_level(
            consistency_level(self._config.consistency_level)
        )

    def _ensure_tenant(self, tenant: str) -> None:
        from weaviate.classes.tenants import Tenant

        if tenant in self._known_tenants:
            return
        try:
            existing = self._collection.tenants.get_by_name(tenant)
        except Exception:  # noqa: BLE001 - treat any lookup failure as "absent"
            existing = None
        if existing is None:
            try:
                self._collection.tenants.create([Tenant(name=tenant)])
            except Exception:  # noqa: BLE001 - concurrent creation is benign
                logger.debug("tenant %s already exists or was created concurrently", tenant)
        self._known_tenants.add(tenant)

    def _insert_chunks(self, collection: Any, chunks: Sequence[StoredChunk]) -> None:
        """
        Write a document's chunks.

        `insert_many` sends one request per slice; the batch context manager
        spins up worker threads per invocation, which dominates the cost for
        the modest per-document batches ingestion produces.
        """
        from weaviate.classes.data import DataObject

        size = max(self._config.batch_size, 1)
        for start in range(0, len(chunks), size):
            window = chunks[start : start + size]
            response = collection.data.insert_many(
                [
                    DataObject(
                        uuid=chunk.chunk_id,
                        properties=chunk_to_properties(chunk),
                        vector=chunk_to_vector(chunk),
                    )
                    for chunk in window
                ]
            )
            if getattr(response, "has_errors", False):
                errors = getattr(response, "errors", {}) or {}
                raise StorageWriteError(
                    f"{len(errors)} chunk(s) rejected by the vector store"
                )

    def _compensate(self, collection: Any, chunk_ids: Sequence[UUID]) -> None:
        """Remove objects written by a failed attempt. Best effort by design."""
        try:
            self._delete_by_ids(collection, chunk_ids)
        except Exception:  # noqa: BLE001 - compensation must not mask the cause
            # Orphaned vectors are unreachable (the document never reaches
            # INDEXED), but they must be observable for cleanup.
            logger.warning(
                "compensation failed; %d orphaned chunk object(s) may remain",
                len(chunk_ids),
            )

    @staticmethod
    def _delete_by_ids(collection: Any, chunk_ids: Sequence[UUID]) -> None:
        from weaviate.classes.query import Filter

        if not chunk_ids:
            return
        collection.data.delete_many(
            where=Filter.by_id().contains_any([str(cid) for cid in chunk_ids])
        )

    @staticmethod
    def _chunk_uuids_for_document(collection: Any, document_id: UUID) -> list[UUID]:
        from weaviate.classes.query import Filter

        response = collection.query.fetch_objects(
            filters=Filter.by_property(PROP_DOCUMENT_ID).equal(str(document_id)),
            limit=10_000,
            return_properties=[PROP_CHUNK_INDEX],
        )
        return [obj.uuid for obj in response.objects]

    @staticmethod
    def _document_filter(document_id: UUID) -> Any:
        from weaviate.classes.query import Filter

        return Filter.by_property(PROP_DOCUMENT_ID).equal(str(document_id))

    def _scope_filter(self, scope: VectorSearchScope) -> Any:
        """
        Mandatory server-side authorization filter.

        Company is already enforced by the tenant; department and document are
        enforced here because Weaviate multi-tenancy cannot nest.
        """
        from weaviate.classes.query import Filter

        clauses = [
            Filter.by_property(PROP_DEPARTMENT_ID).contains_any(
                [str(value) for value in scope.allowed_department_ids]
            )
        ]
        if scope.allowed_document_ids is None:
            # Searchability comes from the denormalised status, so retrieval no
            # longer enumerates every indexed document id per query.
            clauses.append(
                Filter.by_property(PROP_DOCUMENT_STATUS).equal(
                    SEARCHABLE_DOCUMENT_STATUS
                )
            )
        else:
            clauses.append(
                Filter.by_property(PROP_DOCUMENT_ID).contains_any(
                    [str(value) for value in scope.allowed_document_ids]
                )
            )
        return Filter.all_of(clauses)

    @staticmethod
    def _compatible_filter(
        scope_filter: Any, query_model_id: str, query_dimension: int
    ) -> Any:
        from weaviate.classes.query import Filter

        return Filter.all_of(
            [
                scope_filter,
                Filter.by_property(PROP_EMBEDDING_MODEL_ID).equal(query_model_id),
                Filter.by_property(PROP_EMBEDDING_DIMENSION).equal(query_dimension),
            ]
        )

    def _assert_compatible(
        self,
        collection: Any,
        scope_filter: Any,
        query_model_id: str,
        query_dimension: int,
    ) -> None:
        """
        Reproduce the in-memory contract: a mismatched stored chunk *raises*.

        Silently filtering incompatible vectors would change retrieval semantics
        without telling anyone, so the adapter explicitly looks for in-scope
        chunks that disagree with the query model or dimension.
        """
        from weaviate.classes.query import Filter

        # One round trip finds any incompatibility; a second, narrower query
        # only runs when something actually mismatched, so the common path
        # stays at a single aggregate.
        incompatible = collection.aggregate.over_all(
            filters=Filter.all_of(
                [
                    scope_filter,
                    Filter.any_of(
                        [
                            Filter.by_property(PROP_EMBEDDING_MODEL_ID).not_equal(
                                query_model_id
                            ),
                            Filter.by_property(PROP_EMBEDDING_DIMENSION).not_equal(
                                query_dimension
                            ),
                        ]
                    ),
                ]
            ),
            total_count=True,
        )
        if int(incompatible.total_count or 0) == 0:
            return

        mismatched_model = collection.aggregate.over_all(
            filters=Filter.all_of(
                [
                    scope_filter,
                    Filter.by_property(PROP_EMBEDDING_MODEL_ID).not_equal(
                        query_model_id
                    ),
                ]
            ),
            total_count=True,
        )
        if int(mismatched_model.total_count or 0) > 0:
            raise RetrievalModelMismatchError(
                "stored chunk embedding model does not match query model "
                f"{query_model_id!r}"
            )
        raise RetrievalDimensionMismatchError(
            "stored chunk dimension does not match query dimension "
            f"{query_dimension}"
        )

    def _guard_scope_size(self, scope: VectorSearchScope) -> None:
        if scope.allowed_document_ids is None:
            # No id list is sent, so there is no filter-size ceiling.
            return
        limit = self._config.max_scope_document_ids
        if len(scope.allowed_document_ids) > limit:
            # Fail closed. Truncating an authorization filter would return
            # unauthorized chunks, so an oversized scope is an error.
            raise StorageScopeTooLargeError(
                f"authorized document scope ({len(scope.allowed_document_ids)}) "
                f"exceeds max_scope_document_ids ({limit})"
            )

    @staticmethod
    def _assert_object_scope(chunk: StoredChunk, scope: VectorSearchScope) -> None:
        """
        Defence in depth: verify each returned object really is in scope.

        The tenant and filters should make this impossible; if it ever fires, a
        filter was not applied and failing loudly is the only safe response.
        """
        out_of_scope = (
            chunk.company_id != scope.company_id
            or chunk.department_id not in set(scope.allowed_department_ids)
        )
        if scope.allowed_document_ids is None:
            out_of_scope = out_of_scope or (
                chunk.document_status != SEARCHABLE_DOCUMENT_STATUS
            )
        else:
            out_of_scope = out_of_scope or (
                chunk.document_id not in scope.allowed_document_ids
            )
        if out_of_scope:
            raise StorageWriteError(
                "vector store returned an out-of-scope chunk; query was rejected"
            )

    @staticmethod
    def _distance_metadata() -> Any:
        from weaviate.classes.query import MetadataQuery

        return MetadataQuery(distance=True)

    def _candidate_tenants(self, document_id: UUID) -> list[str]:
        """
        Tenants that may hold a document.

        Lifecycle operations do not carry authorization scope, so a document
        first seen in this process is looked up in its known tenant; otherwise
        every tenant is considered. Reads stay scoped by `document_id`.
        """
        known = self._document_tenants.get(document_id)
        if known is not None:
            return [known]
        try:
            return list(self._collection.tenants.get().keys())
        except Exception:  # noqa: BLE001 - no tenants yet
            return []

    @staticmethod
    def _fetch_all_limit() -> int:
        return 10_000
