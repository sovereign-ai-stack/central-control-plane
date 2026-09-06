"""
The Persian NLP pipeline.

One object, used identically by ingestion, query processing, and the benchmark.
Symmetry matters: if documents are morphologically reduced but queries are not,
the two land in different spaces and recall collapses. `process_document` and
`process_query` therefore share one code path.

The transform is **idempotent**, so a text that is processed at ingestion and
again at embedding time is unchanged by the second pass.
"""

from __future__ import annotations

from rag.nlp.backends.protocol import MorphologyBackend, create_backend
from rag.nlp.config import NlpConfig
from rag.nlp.normalizer import normalize_persian_v2
from rag.nlp.sentences import split_sentences
from rag.nlp.tokenizer import tokenize_with_spans
from rag.nlp.types import ProcessedText, Token


class PersianNlpPipeline:
    """Normalization, tokenization, sentence segmentation, optional morphology."""

    def __init__(
        self,
        config: NlpConfig | None = None,
        *,
        backend: MorphologyBackend | None = None,
    ) -> None:
        self._config = config or NlpConfig()
        self._backend = backend
        if self._backend is None and self._config.morphology.enabled:
            self._backend = create_backend(
                self._config.morphology.backend,
                rules=self._config.morphology.to_rules(),
            )

    @property
    def config(self) -> NlpConfig:
        return self._config

    @property
    def version(self) -> str:
        return self._config.pipeline_version

    @property
    def backend(self) -> MorphologyBackend | None:
        return self._backend

    def normalize(self, text: str) -> str:
        return normalize_persian_v2(text, fold_digits=self._config.fold_digits)

    def process(self, text: str) -> ProcessedText:
        normalized = self.normalize(text)
        spans = tokenize_with_spans(normalized)
        surfaces = [surface for surface, _start, _end in spans]

        if self._morphology_active():
            lemmas = self._backend.lemmatize(list(surfaces))
            if len(lemmas) != len(surfaces):
                lemmas = list(surfaces)
        else:
            lemmas = list(surfaces)

        tokens = tuple(
            Token(
                surface=surface,
                normalized=surface,
                lemma=lemma,
                char_start=start,
                char_end=end,
            )
            for (surface, start, end), lemma in zip(spans, lemmas, strict=True)
        )
        embedding_text = (
            self._rebuild(normalized, spans, lemmas)
            if self._morphology_active()
            else normalized
        )
        return ProcessedText(
            original=text,
            normalized=normalized,
            embedding_text=embedding_text,
            tokens=tokens,
            sentences=tuple(split_sentences(normalized)),
            nlp_version=self.version,
            normalization_version=self._config.normalization_version,
            morphology_applied=self._morphology_active(),
        )

    def process_document(self, text: str) -> ProcessedText:
        return self.process(text)

    def process_query(self, text: str) -> ProcessedText:
        """Identical transform to documents — asymmetry here would break recall."""
        return self.process(text)

    def embedding_text(self, text: str) -> str:
        """Shortcut for callers that only need the embedding representation."""
        return self.process(text).embedding_text

    def _morphology_active(self) -> bool:
        return self._config.morphology.enabled and self._backend is not None

    @staticmethod
    def _rebuild(
        normalized: str,
        spans: list[tuple[str, int, int]],
        lemmas: list[str],
    ) -> str:
        """Splice lemmas back into the text, preserving all inter-token characters."""
        if not spans:
            return normalized
        parts: list[str] = []
        cursor = 0
        for (_surface, start, end), lemma in zip(spans, lemmas, strict=True):
            parts.append(normalized[cursor:start])
            parts.append(lemma)
            cursor = end
        parts.append(normalized[cursor:])
        return "".join(parts)
