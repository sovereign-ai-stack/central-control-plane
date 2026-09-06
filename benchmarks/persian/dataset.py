"""Dataset loading utilities for fa-retrieval-v1."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CorpusDocument:
    doc_id: str
    text: str
    domain: str
    language: str


@dataclass(frozen=True, slots=True)
class BenchmarkQuery:
    query_id: str
    text: str
    domain: str
    language: str
    relevant_doc_ids: tuple[str, ...]
    difficulty: str
    query_length: str
    normalization: str
    category: str | None = None


@dataclass(frozen=True, slots=True)
class BenchmarkDataset:
    dataset_version: str
    corpus: list[CorpusDocument]
    queries: list[BenchmarkQuery]
    validation_query_ids: set[str]
    test_query_ids: set[str]


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_dataset(dataset_dir: Path) -> BenchmarkDataset:
    corpus_rows = _read_jsonl(dataset_dir / "corpus.jsonl")
    query_rows = _read_jsonl(dataset_dir / "queries.jsonl")
    with (dataset_dir / "splits.json").open(encoding="utf-8") as handle:
        splits = json.load(handle)

    corpus = [
        CorpusDocument(
            doc_id=row["doc_id"],
            text=row["text"],
            domain=row.get("domain", "general"),
            language=row.get("language", "fa"),
        )
        for row in corpus_rows
    ]
    queries = [
        BenchmarkQuery(
            query_id=row["query_id"],
            text=row["text"],
            domain=row.get("domain", "general"),
            language=row.get("language", "fa"),
            relevant_doc_ids=tuple(row["relevant_doc_ids"]),
            difficulty=row.get("difficulty", "easy"),
            query_length=row.get("query_length", "medium"),
            normalization=row.get("normalization", "standard"),
            category=row.get("category"),
        )
        for row in query_rows
    ]
    return BenchmarkDataset(
        dataset_version=str(splits.get("dataset_version", "fa-retrieval-v1")),
        corpus=corpus,
        queries=queries,
        validation_query_ids=set(splits["validation_query_ids"]),
        test_query_ids=set(splits.get("test_query_ids", [])),
    )


def query_category(query: BenchmarkQuery) -> str:
    if query.category:
        return query.category
    if query.normalization == "zwnj":
        return "zwnj"
    if query.normalization == "arabic_chars":
        return "arabic_char_variants"
    if query.language == "mixed":
        return "mixed_language"
    if query.domain == "technical":
        return "technical"
    if query.query_length == "short":
        return "short_query"
    if query.query_length == "long":
        return "long_query"
    if query.difficulty == "medium":
        return "paraphrase"
    return "semantic"
