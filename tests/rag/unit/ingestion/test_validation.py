"""Validation unit tests."""

from __future__ import annotations

import pytest

from rag.ingestion.errors import IngestContentTooLargeError, IngestValidationError
from rag.ingestion.types import IngestDocumentRequest, IngestDocumentUpdateRequest
from rag.ingestion.validation import content_hash, validate_create_request, validate_update_request


class TestValidation:
    def test_empty_content_rejected(self, tenant_ids):
        request = IngestDocumentRequest(
            content="   ",
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            source="test",
        )
        with pytest.raises(IngestValidationError):
            validate_create_request(request)

    def test_content_hash_deterministic(self):
        text = "normalized content"
        assert content_hash(text) == content_hash(text)
        assert content_hash(text) != content_hash(text + "x")

    def test_oversized_content_rejected(self, tenant_ids):
        request = IngestDocumentRequest(
            content="x" * (1_048_577),
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
            source="test",
        )
        with pytest.raises(IngestContentTooLargeError):
            validate_create_request(request)

    def test_update_requires_content(self, tenant_ids):
        request = IngestDocumentUpdateRequest(
            content="",
            company_id=tenant_ids["companies"]["C1"],
            department_id=tenant_ids["departments"]["C1_D1"],
        )
        with pytest.raises(IngestValidationError):
            validate_update_request(request)
