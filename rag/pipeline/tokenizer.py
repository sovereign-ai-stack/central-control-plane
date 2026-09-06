"""
Token counting for context budgeting (spec 005-rag-pipeline/context-builder.md §6).

v1 uses a deterministic character-based estimate rather than a model tokenizer:
no production LLM is selected yet, and a tokenizer download would contradict the
"no model dependency before benchmark" constraint. The estimate is documented as
biased: for Persian text a 4-chars-per-token divisor tends to *under*-count real
subword tokens, so budgets should be set conservatively.
"""

from __future__ import annotations

import math
from typing import Protocol

from rag.pipeline.errors import PipelineValidationError


class TokenCounter(Protocol):
    def count(self, text: str) -> int:
        ...


class CharEstimateTokenCounter:
    """Deterministic ceil(len(text) / chars_per_token) estimator."""

    def __init__(self, chars_per_token: int = 4) -> None:
        if chars_per_token <= 0:
            raise PipelineValidationError("chars_per_token must be positive")
        self._chars_per_token = chars_per_token

    @property
    def chars_per_token(self) -> int:
        return self._chars_per_token

    def count(self, text: str) -> int:
        if not text:
            return 0
        return math.ceil(len(text) / self._chars_per_token)
