"""
RagResult structure and contract tests
(spec 005 PP-050..PP-055, contracts/rag-result.yaml).

The serialized payload is validated against the committed OpenAPI schema so the
implementation cannot drift from the published contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest
import yaml
from tests.rag.conftest import make_retrieved_chunk

from rag.authorization.context import AuthorizationContext
from rag.pipeline.pipeline import PostRetrievalPipeline, query_hash
from rag.pipeline.serialization import rag_result_to_dict
from rag.pipeline.types import AppliedFilter, PipelineOptions, RetrievalMetadata

CONTRACT_PATH = (
    Path(__file__).resolve().parents[4]
    / "specs"
    / "005-rag-pipeline"
    / "contracts"
    / "rag-result.yaml"
)

COMPANY = UUID("11111111-1111-1111-1111-111111111101")
DEPARTMENT = UUID("22222222-2222-2222-2222-222222222201")
USER = UUID("33333333-3333-3333-3333-333333333301")
REQUEST = UUID("55555555-5555-5555-5555-555555555501")

_TYPE_CHECKS = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


@pytest.fixture(scope="module")
def contract() -> dict:
    with CONTRACT_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _resolve(contract: dict, schema: dict) -> dict:
    ref = schema.get("$ref")
    if ref is None:
        return schema
    name = ref.rsplit("/", 1)[-1]
    return contract["components"]["schemas"][name]


def assert_matches_schema(contract: dict, schema: dict, payload, path: str = "$") -> None:
    """Minimal structural OpenAPI check: required keys, types, enums, nullability."""
    schema = _resolve(contract, schema)
    expected = schema.get("type")

    if expected == "object":
        assert isinstance(payload, dict), f"{path} must be an object"
        for key in schema.get("required", []):
            assert key in payload, f"{path}.{key} is required by the contract"
        properties = schema.get("properties", {})
        for key, value in payload.items():
            if key in properties:
                assert_matches_schema(contract, properties[key], value, f"{path}.{key}")
        return

    if expected == "array":
        assert isinstance(payload, list), f"{path} must be an array"
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(payload):
                assert_matches_schema(contract, item_schema, item, f"{path}[{index}]")
        return

    if payload is None:
        assert schema.get("nullable", False), f"{path} must not be null"
        return

    if expected in _TYPE_CHECKS:
        assert isinstance(payload, _TYPE_CHECKS[expected]), (
            f"{path} must be {expected}, got {type(payload).__name__}"
        )
    if "enum" in schema:
        assert payload in schema["enum"], f"{path} must be one of {schema['enum']}"


@pytest.fixture
def authorization_context() -> AuthorizationContext:
    return AuthorizationContext(
        user_id=USER,
        company_id=COMPANY,
        allowed_department_ids=(DEPARTMENT,),
        request_id=REQUEST,
    )


def _candidates(count: int = 3):
    return [
        make_retrieved_chunk(
            f"سند شماره {index} درباره مرخصی سالانه",
            score=0.9 - index * 0.05,
            company_id=COMPANY,
            department_id=DEPARTMENT,
            chunk_index=index,
        )
        for index in range(count)
    ]


def _retrieval_metadata(count: int) -> RetrievalMetadata:
    return RetrievalMetadata(
        chunk_count=count,
        latency_ms=12,
        filter_applied=AppliedFilter(company_id=COMPANY, department_count=1),
    )


def _process(authz, candidates, **option_overrides):
    options = PipelineOptions(**{"top_k": 10, **option_overrides})
    return PostRetrievalPipeline().process(
        "مرخصی سالانه",
        authz,
        candidates,
        _retrieval_metadata(len(candidates)),
        options,
    )


class TestRagResultStructure:
    def test_pp_050_all_required_sections_present(self, authorization_context):
        result = _process(authorization_context, _candidates())
        payload = rag_result_to_dict(result)
        for section in (
            "request_id",
            "query_hash",
            "identity",
            "sources",
            "chunks",
            "provenance",
            "relevance",
            "context",
            "retrieval",
            "pipeline",
        ):
            assert section in payload

    def test_pp_051_no_answer_or_prompt_fields(self, authorization_context):
        result = _process(authorization_context, _candidates())
        payload = rag_result_to_dict(result)
        for prohibited in (
            "answer",
            "system_prompt",
            "system_instructions",
            "authorization_instructions",
            "messages",
        ):
            assert prohibited not in payload

    def test_pp_sec_031_no_chat_message_array_anywhere(self, authorization_context):
        result = _process(authorization_context, _candidates())
        serialized = json.dumps(rag_result_to_dict(result), ensure_ascii=False)
        assert '"messages"' not in serialized
        assert '"role"' not in serialized

    def test_pp_052_sources_aggregate_by_document(self, authorization_context):
        document_id = UUID("dddddddd-0000-0000-0000-000000000001")
        candidates = [
            make_retrieved_chunk(
                f"بخش {index}",
                score=0.9 - index * 0.01,
                company_id=COMPANY,
                department_id=DEPARTMENT,
                document_id=document_id,
                chunk_index=index,
            )
            for index in range(3)
        ]
        result = _process(authorization_context, candidates)
        assert len(result.sources) == 1
        source = result.sources[0]
        assert source.document_id == document_id
        assert source.chunk_count == 3
        assert source.max_score == pytest.approx(0.9)

    def test_pp_053_provenance_carries_citation_metadata(self, authorization_context):
        result = _process(authorization_context, _candidates())
        assert len(result.provenance) == len(result.chunks)
        for position, record in enumerate(result.provenance):
            assert record.citation_id == f"src-{position + 1}"
            assert record.position_in_context == position
            assert record.document_id is not None
            assert record.chunk_id is not None
            assert isinstance(record.retrieval_score, float)

    def test_pp_sec_042_citation_ids_are_unique(self, authorization_context):
        result = _process(authorization_context, _candidates(5))
        citations = [record.citation_id for record in result.provenance]
        assert len(citations) == len(set(citations))

    def test_pp_sec_040_every_context_block_has_a_provenance_record(
        self, authorization_context
    ):
        result = _process(authorization_context, _candidates())
        assert result.context.block_count == len(result.provenance)
        for record in result.provenance:
            assert f'id="{record.citation_id}"' in result.context.text
            assert f'chunk_id="{record.chunk_id}"' in result.context.text

    def test_pp_054_query_hash_not_raw_query(self, authorization_context):
        result = _process(authorization_context, _candidates())
        payload = json.dumps(rag_result_to_dict(result), ensure_ascii=False)
        assert result.query_hash == query_hash("مرخصی سالانه")
        assert len(result.query_hash) == 64
        assert '"query"' not in payload

    def test_pp_sec_032_context_format_is_always_delimited_v1(
        self, authorization_context
    ):
        result = _process(authorization_context, _candidates())
        assert result.context.format == "delimited_v1"

    def test_no_vectors_in_serialized_payload(self, authorization_context):
        result = _process(authorization_context, _candidates())
        payload = json.dumps(rag_result_to_dict(result), ensure_ascii=False).lower()
        for banned in ("embedding", "vector", "dimension"):
            assert banned not in payload

    def test_relevance_summary_counts(self, authorization_context):
        candidates = _candidates(3)
        result = _process(authorization_context, candidates, top_k=2)
        assert result.relevance.candidate_count == 3
        assert result.relevance.selected_count == 2
        assert result.relevance.top_retrieval_score == pytest.approx(0.9)
        assert result.relevance.mean_retrieval_score is not None


class TestOpenApiContract:
    def test_pp_055_payload_validates_against_rag_result_yaml(
        self, contract, authorization_context
    ):
        result = _process(authorization_context, _candidates())
        payload = rag_result_to_dict(result)
        assert_matches_schema(
            contract, contract["components"]["schemas"]["RagResult"], payload
        )

    def test_pp_055_empty_result_validates(self, contract, authorization_context):
        result = _process(authorization_context, [])
        payload = rag_result_to_dict(result)
        assert_matches_schema(
            contract, contract["components"]["schemas"]["RagResult"], payload
        )
        assert payload["context"]["text"] == ""
        assert payload["chunks"] == []

    def test_contract_defines_no_answer_property(self, contract):
        properties = contract["components"]["schemas"]["RagResult"]["properties"]
        assert "answer" not in properties
        assert "system_prompt" not in properties
