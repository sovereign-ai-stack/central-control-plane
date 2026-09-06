"""
Unit tests for Weaviate mapping, schema, and configuration (Phase 6).

These need neither a running Weaviate nor the client library, so they run in the
default suite.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import numpy as np
import pytest

from rag.ingestion.types import StoredChunk
from rag.storage.chunk_validation import validate_chunk, validate_chunk_batch
from rag.storage.config import (
    BACKEND_MEMORY,
    BACKEND_WEAVIATE,
    VectorStoreConfig,
    WeaviateConfig,
    load_vector_store_config,
)
from rag.storage.errors import (
    StorageConfigurationError,
    StorageScopeTooLargeError,
    StorageWriteError,
)
from rag.storage.weaviate.mapping import (
    chunk_to_properties,
    chunk_to_vector,
    distance_to_similarity,
    properties_to_chunk,
    vector_from_object,
)
from rag.storage.weaviate.schema import (
    FILTERABLE_PROPERTIES,
    INT_PROPERTIES,
    PROP_COMPANY_ID,
    PROP_DEPARTMENT_ID,
    PROP_DOCUMENT_ID,
    TEXT_PROPERTIES,
    tenant_name,
)

COMPANY = UUID("11111111-1111-1111-1111-111111111101")
DEPARTMENT = UUID("22222222-2222-2222-2222-222222222201")


def _chunk(**overrides) -> StoredChunk:
    base = {
        "chunk_id": uuid4(),
        "document_id": uuid4(),
        "company_id": COMPANY,
        "department_id": DEPARTMENT,
        "document_version": 3,
        "chunk_index": 2,
        "content": "متن نمونه",
        "content_hash": "hash-abc",
        "embedding": np.ones(4, dtype=np.float32),
        "embedding_model_id": "stub-v1",
        "embedding_dimension": 4,
        "token_count": 2,
    }
    base.update(overrides)
    return StoredChunk(**base)


class TestPropertyMapping:
    def test_security_metadata_is_persisted(self):
        chunk = _chunk()
        properties = chunk_to_properties(chunk)
        assert properties[PROP_COMPANY_ID] == str(COMPANY)
        assert properties[PROP_DEPARTMENT_ID] == str(DEPARTMENT)
        assert properties[PROP_DOCUMENT_ID] == str(chunk.document_id)

    def test_embedding_metadata_is_persisted(self):
        properties = chunk_to_properties(_chunk())
        assert properties["embedding_model_id"] == "stub-v1"
        assert properties["embedding_dimension"] == 4

    def test_dedup_and_version_fields_persisted(self):
        properties = chunk_to_properties(_chunk())
        assert properties["content_hash"] == "hash-abc"
        assert properties["document_version"] == 3
        assert properties["chunk_index"] == 2

    def test_phase5_enrichment_persisted(self):
        chunk = _chunk(
            original_text="اصل",
            embedding_text="پردازش",
            nlp_version="fa-nlp-v1+fa-norm-v2+morph",
            language="fa",
            section_path="ماده ۵",
            char_start=10,
            char_end=42,
            source_segment_label="page",
            source_segment_start=3,
            source_segment_end=4,
        )
        properties = chunk_to_properties(chunk)
        assert properties["nlp_version"] == "fa-nlp-v1+fa-norm-v2+morph"
        assert properties["source_segment_label"] == "page"
        assert properties["source_segment_start"] == 3
        assert properties["char_end"] == 42

    def test_unset_optionals_are_omitted(self):
        properties = chunk_to_properties(_chunk())
        assert "original_text" not in properties
        assert "source_segment_label" not in properties

    def test_round_trip_preserves_every_field(self):
        chunk = _chunk(
            original_text="اصل",
            embedding_text="پردازش",
            nlp_version="v",
            language="fa",
            section_path="بخش",
            char_start=1,
            char_end=2,
            source_segment_label="page",
            source_segment_start=1,
            source_segment_end=1,
        )
        restored = properties_to_chunk(
            chunk_to_properties(chunk), embedding=chunk.embedding
        )
        for field in (
            "chunk_id",
            "document_id",
            "company_id",
            "department_id",
            "document_version",
            "chunk_index",
            "content",
            "content_hash",
            "embedding_model_id",
            "embedding_dimension",
            "token_count",
            "original_text",
            "embedding_text",
            "nlp_version",
            "language",
            "section_path",
            "char_start",
            "char_end",
            "source_segment_label",
            "source_segment_start",
            "source_segment_end",
        ):
            assert getattr(restored, field) == getattr(chunk, field), field

    def test_missing_required_property_is_rejected(self):
        with pytest.raises(StorageWriteError):
            properties_to_chunk({"chunk_id": str(uuid4())})


class TestVectorMapping:
    def test_vector_is_serialised_as_floats(self):
        vector = chunk_to_vector(_chunk())
        assert vector == [1.0, 1.0, 1.0, 1.0]
        assert all(isinstance(value, float) for value in vector)

    def test_missing_embedding_is_rejected(self):
        with pytest.raises(StorageWriteError):
            chunk_to_vector(_chunk(embedding=None))

    def test_vector_from_object_handles_named_vectors(self):
        assert vector_from_object({"default": [1.0, 2.0]}).tolist() == [1.0, 2.0]
        assert vector_from_object([1.0, 2.0]).tolist() == [1.0, 2.0]
        assert vector_from_object(None) is None

    def test_vector_from_object_is_float32(self):
        assert vector_from_object([1.0, 2.0]).dtype == np.float32


class TestScoreMapping:
    def test_distance_converts_to_cosine_similarity(self):
        # Verified against a live instance: similarity = 1 - distance.
        assert distance_to_similarity(0.0) == 1.0
        assert distance_to_similarity(1.0) == 0.0
        assert distance_to_similarity(2.0) == -1.0

    def test_missing_distance_is_zero(self):
        assert distance_to_similarity(None) == 0.0

    def test_matches_dot_product_of_normalised_vectors(self):
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        expected = float(np.dot(a, b))
        assert distance_to_similarity(1.0 - expected) == pytest.approx(expected)


class TestSchema:
    def test_tenant_is_derived_from_company(self):
        assert tenant_name(COMPANY) == f"company-{COMPANY}"

    def test_tenant_names_differ_per_company(self):
        assert tenant_name(COMPANY) != tenant_name(uuid4())

    def test_authorization_properties_are_filterable(self):
        for name in (PROP_COMPANY_ID, PROP_DEPARTMENT_ID, PROP_DOCUMENT_ID):
            assert name in FILTERABLE_PROPERTIES

    def test_model_compatibility_properties_are_filterable(self):
        assert "embedding_model_id" in FILTERABLE_PROPERTIES
        assert "embedding_dimension" in FILTERABLE_PROPERTIES

    def test_text_and_int_properties_do_not_overlap(self):
        assert not (set(TEXT_PROPERTIES) & set(INT_PROPERTIES))


class TestSharedValidation:
    def test_valid_chunk_accepted(self):
        validate_chunk(_chunk())

    @pytest.mark.parametrize(
        "overrides",
        [
            {"embedding": None},
            {"embedding_model_id": None},
            {"embedding_dimension": None},
            {"embedding": np.ones((2, 2), dtype=np.float32)},
            {"embedding": np.ones(8, dtype=np.float32)},
            {"embedding": np.ones(4, dtype=np.float64)},
        ],
    )
    def test_invalid_chunk_rejected(self, overrides):
        with pytest.raises(ValueError):
            validate_chunk(_chunk(**overrides))

    def test_batch_document_mismatch_rejected(self):
        with pytest.raises(ValueError, match="document_id mismatch"):
            validate_chunk_batch(uuid4(), [_chunk()])

    def test_batch_mixed_scope_rejected(self):
        document_id = uuid4()
        first = _chunk(document_id=document_id)
        second = _chunk(document_id=document_id, department_id=uuid4())
        with pytest.raises(ValueError, match="scope mismatch"):
            validate_chunk_batch(document_id, [first, second])

    def test_empty_batch_is_allowed(self):
        validate_chunk_batch(uuid4(), [])


class TestConfiguration:
    def test_default_backend_is_memory(self):
        assert VectorStoreConfig().backend == BACKEND_MEMORY

    def test_shipped_config_defaults_to_memory(self):
        assert load_vector_store_config().backend == BACKEND_MEMORY

    def test_unknown_backend_rejected(self):
        with pytest.raises(StorageConfigurationError):
            VectorStoreConfig(backend="pinecone").validate()

    def test_api_key_is_read_from_environment(self, monkeypatch):
        monkeypatch.setenv("TEST_WV_KEY", "s3cret")
        config = WeaviateConfig(api_key_env="TEST_WV_KEY")
        assert config.api_key() == "s3cret"

    def test_missing_env_var_is_an_error_not_a_silent_none(self, monkeypatch):
        monkeypatch.delenv("TEST_WV_MISSING", raising=False)
        with pytest.raises(StorageConfigurationError):
            WeaviateConfig(api_key_env="TEST_WV_MISSING").api_key()

    def test_no_api_key_env_means_anonymous(self):
        assert WeaviateConfig().api_key() is None

    def test_literal_api_key_in_config_is_refused(self, tmp_path):
        path = tmp_path / "vector_store.yaml"
        path.write_text(
            "vector_store:\n  backend: weaviate\n  weaviate:\n    api_key: hunter2\n",
            encoding="utf-8",
        )
        with pytest.raises(StorageConfigurationError, match="api_key_env"):
            load_vector_store_config(path)

    def test_config_never_stores_a_secret_value(self):
        # The dataclass has no field that could hold a key.
        assert "api_key" not in WeaviateConfig.__dataclass_fields__
        assert "api_key_env" in WeaviateConfig.__dataclass_fields__

    @pytest.mark.parametrize(
        "overrides",
        [
            {"host": ""},
            {"collection": ""},
            {"collection": "lowercase"},
            {"http_port": 0},
            {"grpc_port": -1},
            {"batch_size": 0},
            {"overfetch_factor": 0},
            {"consistency_level": "EVENTUAL"},
        ],
    )
    def test_invalid_weaviate_config_rejected(self, overrides):
        with pytest.raises(StorageConfigurationError):
            WeaviateConfig(**overrides).validate()

    def test_weaviate_config_loads_from_file(self, tmp_path):
        path = tmp_path / "vector_store.yaml"
        path.write_text(
            "vector_store:\n"
            "  backend: weaviate\n"
            "  weaviate:\n"
            "    host: vectors.internal\n"
            "    http_port: 9090\n"
            "    collection: ProdChunk\n"
            "    api_key_env: WEAVIATE_API_KEY\n"
            "    consistency_level: ALL\n",
            encoding="utf-8",
        )
        config = load_vector_store_config(path)
        assert config.backend == BACKEND_WEAVIATE
        assert config.weaviate.host == "vectors.internal"
        assert config.weaviate.collection == "ProdChunk"
        assert config.weaviate.api_key_env == "WEAVIATE_API_KEY"
        assert config.uses_weaviate is True

    def test_missing_file_falls_back_to_memory(self, tmp_path):
        assert load_vector_store_config(tmp_path / "absent.yaml").backend == (
            BACKEND_MEMORY
        )


class TestFactory:
    def test_memory_backend_selected_by_default(self):
        from rag.storage.chunk_store import InMemoryChunkStore
        from rag.storage.factory import create_chunk_store

        assert isinstance(create_chunk_store(VectorStoreConfig()), InMemoryChunkStore)

    def test_unknown_backend_rejected(self):
        from rag.storage.factory import create_chunk_store

        with pytest.raises(StorageConfigurationError):
            create_chunk_store(VectorStoreConfig(backend="qdrant"))

    def test_close_is_optional(self):
        from rag.storage.chunk_store import InMemoryChunkStore
        from rag.storage.factory import close_chunk_store

        close_chunk_store(InMemoryChunkStore())


class TestErrorTypes:
    def test_scope_too_large_is_a_storage_error(self):
        from rag.storage.errors import StorageError

        assert issubclass(StorageScopeTooLargeError, StorageError)
        assert issubclass(StorageWriteError, StorageError)
