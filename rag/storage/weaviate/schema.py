"""
Weaviate collection schema for RAG chunks.

Design decisions, verified against Weaviate 1.36 rather than assumed:

- **`tenant = company_id`.** Weaviate multi-tenancy is single-level and
  shard-based, so the tenant key can encode exactly one dimension. Company is the
  correct one: it is the hard security boundary, and a probe confirmed a query in
  one tenant cannot see an identical vector stored in another.

  `tenant = "company:department"` was rejected: a user authorized for three
  departments would need three separate queries, which breaks `top_k` and
  `pool_size` semantics, and it would demote the company boundary to a
  string-prefix convention.

- **Department and document stay as mandatory server-side filters.** Since
  multi-tenancy cannot nest, these are enforced with `ContainsAny` inside the
  query — never by filtering results in Python.

- **`vectorizer = none`.** Chunks arrive already embedded and carry the model id
  they were produced with. Server-side vectorization would silently use a
  different model from the one ingestion recorded.
"""

from __future__ import annotations

from typing import Any

# Property names are also the filter keys, so they are defined once here.
PROP_CHUNK_ID = "chunk_id"
PROP_DOCUMENT_ID = "document_id"
PROP_COMPANY_ID = "company_id"
PROP_DEPARTMENT_ID = "department_id"
PROP_DOCUMENT_VERSION = "document_version"
PROP_CHUNK_INDEX = "chunk_index"
PROP_CONTENT = "content"
PROP_CONTENT_HASH = "content_hash"
PROP_EMBEDDING_MODEL_ID = "embedding_model_id"
PROP_EMBEDDING_DIMENSION = "embedding_dimension"
PROP_TOKEN_COUNT = "token_count"
PROP_ORIGINAL_TEXT = "original_text"
PROP_EMBEDDING_TEXT = "embedding_text"
PROP_NLP_VERSION = "nlp_version"
PROP_LANGUAGE = "language"
PROP_SECTION_PATH = "section_path"
PROP_CHAR_START = "char_start"
PROP_CHAR_END = "char_end"
PROP_SOURCE_SEGMENT_LABEL = "source_segment_label"
PROP_SOURCE_SEGMENT_START = "source_segment_start"
PROP_SOURCE_SEGMENT_END = "source_segment_end"
PROP_DOCUMENT_STATUS = "document_status"

# Filtered on every query — must be indexed.
FILTERABLE_PROPERTIES = (
    PROP_CHUNK_ID,
    PROP_DOCUMENT_ID,
    PROP_COMPANY_ID,
    PROP_DEPARTMENT_ID,
    PROP_EMBEDDING_MODEL_ID,
    PROP_EMBEDDING_DIMENSION,
    PROP_CONTENT_HASH,
    PROP_DOCUMENT_STATUS,
)

TEXT_PROPERTIES = (
    PROP_CHUNK_ID,
    PROP_DOCUMENT_ID,
    PROP_COMPANY_ID,
    PROP_DEPARTMENT_ID,
    PROP_CONTENT,
    PROP_CONTENT_HASH,
    PROP_EMBEDDING_MODEL_ID,
    PROP_ORIGINAL_TEXT,
    PROP_EMBEDDING_TEXT,
    PROP_NLP_VERSION,
    PROP_LANGUAGE,
    PROP_SECTION_PATH,
    PROP_SOURCE_SEGMENT_LABEL,
    PROP_DOCUMENT_STATUS,
)

INT_PROPERTIES = (
    PROP_DOCUMENT_VERSION,
    PROP_CHUNK_INDEX,
    PROP_EMBEDDING_DIMENSION,
    PROP_TOKEN_COUNT,
    PROP_CHAR_START,
    PROP_CHAR_END,
    PROP_SOURCE_SEGMENT_START,
    PROP_SOURCE_SEGMENT_END,
)


def build_properties() -> list[Any]:
    """Collection properties covering every persisted `StoredChunk` field."""
    from weaviate.classes.config import DataType, Property

    properties: list[Any] = []
    for name in TEXT_PROPERTIES:
        properties.append(
            Property(
                name=name,
                data_type=DataType.TEXT,
                index_filterable=name in FILTERABLE_PROPERTIES,
                # Chunk bodies are retrieved, never BM25-searched by this adapter.
                index_searchable=name == PROP_CONTENT,
            )
        )
    for name in INT_PROPERTIES:
        properties.append(
            Property(
                name=name,
                data_type=DataType.INT,
                index_filterable=True,
            )
        )
    return properties


def ensure_collection(client: Any, name: str) -> Any:
    """
    Create the collection if absent and return it.

    Idempotent: safe to call on every startup.
    """
    import weaviate.classes as wvc
    from weaviate.classes.config import Configure

    if not client.collections.exists(name):
        client.collections.create(
            name=name,
            # Vectors are supplied by EmbeddingService, never computed server-side.
            vector_config=Configure.Vectors.self_provided(
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=wvc.config.VectorDistances.COSINE
                )
            ),
            multi_tenancy_config=Configure.multi_tenancy(
                enabled=True, auto_tenant_creation=True
            ),
            properties=build_properties(),
        )
    return client.collections.get(name)


def tenant_name(company_id: Any) -> str:
    """
    Tenant key for a company.

    Prefixed so a tenant name can never be confused with another identifier and
    is never a bare user-supplied string.
    """
    return f"company-{company_id}"
