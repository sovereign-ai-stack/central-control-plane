"""
Persian NLP layer types.

`ProcessedText` deliberately keeps three representations side by side. The
original is never discarded, the normalized form is what humans and lexical
matching see, and `embedding_text` is the (possibly morphologically reduced)
form handed to the embedding model. Improving semantic retrieval must not mean
losing the source text.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Token:
    surface: str
    normalized: str
    lemma: str
    char_start: int
    char_end: int


@dataclass(frozen=True, slots=True)
class Sentence:
    text: str
    char_start: int
    char_end: int

    @property
    def length(self) -> int:
        return self.char_end - self.char_start


@dataclass(frozen=True, slots=True)
class ProcessedText:
    original: str
    normalized: str
    embedding_text: str
    tokens: tuple[Token, ...]
    sentences: tuple[Sentence, ...]
    nlp_version: str
    normalization_version: str
    morphology_applied: bool

    @property
    def token_count(self) -> int:
        return len(self.tokens)

    @property
    def sentence_count(self) -> int:
        return len(self.sentences)
