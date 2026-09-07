"""Jina Embeddings v5 backend — benchmark candidate only.

Everything model-specific below comes from the official model card for
`jinaai/jina-embeddings-v5-text-nano` (Jina AI, released 2026-02-18), not from
assumption:

* The checkpoint ships four LoRA task adapters — ``retrieval``,
  ``text-matching``, ``clustering``, ``classification``. One must be selected
  before any encode call; the repo's ``custom_st.Transformer`` raises otherwise.
  Retrieval is the task this benchmark measures, so the adapter is pinned to it
  at load time via ``default_task`` and never varies per call.
* Retrieval is asymmetric: queries carry the prompt ``"Query: "`` and documents
  ``"Document: "`` (`config_sentence_transformers.json`). Those two strings are
  configured as the candidate's ``query_prefix`` / ``document_prefix``, so the
  existing symmetric prefix path in ``SentenceTransformersBackend`` applies them
  — no new encode path.
* That same file sets ``default_prompt_name: "document"``, which would make
  sentence-transformers prepend ``"Document: "`` to *every* call, queries
  included, on top of the prefix this backend already applies. It is cleared at
  load time so each text receives exactly one, correct prompt.
* Pooling is last-token and the module L2-normalizes inside its own forward, so
  cosine similarity is the intended comparison — the same measure the benchmark
  already uses for every other candidate.
"""

from __future__ import annotations

from rag.embedding.backends.sentence_transformers import SentenceTransformersBackend
from rag.embedding.config import EmbeddingConfig
from rag.embedding.errors import EmbeddingModelLoadError

JINA_V5_MODEL_IDS = (
    "jinaai/jina-embeddings-v5-text-nano",
    "jinaai/jina-embeddings-v5-text-small",
)

# The benchmark measures retrieval, so the retrieval adapter is the only correct
# one here. Using text-matching would score a different model.
_TASK = "retrieval"


class JinaEmbeddingsV5Backend(SentenceTransformersBackend):
    """
    Local adapter for the Jina Embeddings v5 text family.

    Not production. Dimension is discovered from the loaded model at runtime;
    the repo's custom sentence-transformers module cannot report it, so the base
    class probes for it.
    """

    def __init__(self, config: EmbeddingConfig) -> None:
        if config.model_id not in JINA_V5_MODEL_IDS:
            raise EmbeddingModelLoadError(
                "JinaEmbeddingsV5Backend requires a configured jina-embeddings-v5 model id"
            )
        super().__init__(config)

    @classmethod
    def _sentence_transformer_kwargs(cls, config: EmbeddingConfig) -> dict:
        return {
            # The architecture (JinaEmbeddingsV5Model) and the ST module both
            # live in the model repo, so remote code is required to load it.
            "trust_remote_code": True,
            "model_kwargs": {"default_task": _TASK},
        }

    @classmethod
    def _post_load(cls, model, config: EmbeddingConfig) -> None:
        # Prompts are applied by the shared _apply_prefix path from the
        # candidate config. Leaving the repo default in place would prepend
        # "Document: " a second time, and to queries as well.
        model.default_prompt_name = None
