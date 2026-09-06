"""
Chunk-level retrieval harness (Phase 5H).

The document-level benchmark (`run_benchmark.py`) ranks whole corpus documents
by cosine similarity, so it cannot see chunking at all — a chunking change that
severs sentences scores identically there. This harness closes that gap: it
chunks each document with a configured strategy, embeds the chunks, retrieves at
**chunk** granularity, and attributes each hit back to its source document.

It measures two things the document-level harness cannot:

- retrieval quality when the index granularity is a chunk, not a document
- chunk shape statistics (count, token spread, boundary quality)

It deliberately does **not** use `SecureRetrievalEngine`: this is an offline
quality measurement over a public benchmark corpus with no tenants, and routing
it through the authorization path would prove nothing about chunking while
requiring fake identities. Security is covered by the security suite.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from benchmarks.persian.dataset import BenchmarkDataset, load_dataset, query_category
from benchmarks.persian.metrics import (
    QueryMetrics,
    aggregate_query_metrics,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.service import EmbeddingService
from rag.embedding.stub import StubEmbeddingModel
from rag.ingestion.chunking import ChunkingConfig, create_chunker
from rag.nlp.config import MorphologyConfig, NlpConfig
from rag.nlp.pipeline import PersianNlpPipeline
from rag.nlp.sentences import split_sentences
from rag.nlp.tokenizer import count_tokens

K_VALUES = [1, 3, 5, 10, 20]
NDCG_K_VALUES = [5, 10]


@dataclass(frozen=True, slots=True)
class ChunkShapeStats:
    """How the chunker carved the corpus, independent of retrieval quality."""

    total_chunks: int
    documents: int
    chunks_per_document: float
    mean_tokens: float
    min_tokens: int
    max_tokens: int
    empty_chunks: int
    sentence_boundary_rate: float

    @property
    def is_healthy(self) -> bool:
        return self.empty_chunks == 0 and self.sentence_boundary_rate >= 0.9


def _sentence_boundary_rate(chunks: list[str], sources: list[str]) -> float:
    """
    Fraction of chunks whose text is composed of whole source sentences.

    This is the metric that distinguishes good chunking from a character-budget
    split that severs "... طبق ماده ۵ ..." mid-clause.
    """
    if not chunks:
        return 0.0
    sentences: set[str] = set()
    for source in sources:
        sentences.update(s.text.strip() for s in split_sentences(source))
    if not sentences:
        return 0.0

    whole = 0
    for chunk in chunks:
        lines = [line.strip() for line in chunk.split("\n") if line.strip()]
        if lines and all(line in sentences for line in lines):
            whole += 1
    return whole / len(chunks)


def build_chunk_index(
    dataset: BenchmarkDataset,
    service: EmbeddingService,
    chunking: ChunkingConfig,
    nlp: PersianNlpPipeline | None,
) -> tuple[list[str], list[str], np.ndarray, ChunkShapeStats]:
    """Chunk and embed the corpus; return per-chunk doc ids, texts, vectors, stats."""
    chunker = create_chunker(chunking)
    chunk_doc_ids: list[str] = []
    chunk_texts: list[str] = []
    sources: list[str] = []

    for document in dataset.corpus:
        text = nlp.normalize(document.text) if nlp is not None else document.text
        sources.append(text)
        drafts = chunker.split(text)
        if not drafts:
            drafts = []
        for draft in drafts:
            chunk_doc_ids.append(document.doc_id)
            chunk_texts.append(draft.content)

    if not chunk_texts:
        raise RuntimeError("chunking produced no chunks for the corpus")

    token_counts = [count_tokens(text) for text in chunk_texts]
    stats = ChunkShapeStats(
        total_chunks=len(chunk_texts),
        documents=len(dataset.corpus),
        chunks_per_document=round(len(chunk_texts) / max(len(dataset.corpus), 1), 3),
        mean_tokens=round(sum(token_counts) / len(token_counts), 2),
        min_tokens=min(token_counts),
        max_tokens=max(token_counts),
        empty_chunks=sum(1 for text in chunk_texts if not text.strip()),
        sentence_boundary_rate=round(
            _sentence_boundary_rate(chunk_texts, sources), 4
        ),
    )

    result = service.embed_documents(chunk_texts)
    matrix = np.vstack(result.vectors)
    return chunk_doc_ids, chunk_texts, matrix, stats


def rank_documents_via_chunks(
    service: EmbeddingService,
    query_text: str,
    chunk_doc_ids: list[str],
    chunk_matrix: np.ndarray,
) -> list[str]:
    """
    Rank documents by their best-scoring chunk.

    Max-pooling over chunks is the standard attribution for chunk-level indexes
    and matches how the production pipeline surfaces a document: via its
    strongest chunk.
    """
    query_vector = service.embed_query(query_text).vector
    scores = chunk_matrix @ query_vector
    order = np.argsort(-scores)

    ranked: list[str] = []
    seen: set[str] = set()
    for index in order:
        doc_id = chunk_doc_ids[index]
        if doc_id in seen:
            continue
        seen.add(doc_id)
        ranked.append(doc_id)
    return ranked


def evaluate_chunking(
    dataset: BenchmarkDataset,
    *,
    chunking: ChunkingConfig,
    nlp_config: NlpConfig | None,
    split: str = "val",
) -> dict[str, Any]:
    pipeline = (
        PersianNlpPipeline(nlp_config)
        if nlp_config is not None and nlp_config.enabled
        else None
    )
    version = (
        pipeline.config.normalization_version if pipeline is not None else "fa-norm-v1"
    )
    service = EmbeddingService(
        StubEmbeddingModel(dimension=384, model_id="stub-v1"),
        EmbeddingPreprocessor(version, nlp=pipeline),
    )

    chunk_doc_ids, _texts, matrix, stats = build_chunk_index(
        dataset, service, chunking, pipeline
    )
    selected = (
        dataset.validation_query_ids if split == "val" else dataset.test_query_ids
    )

    per_query: list[QueryMetrics] = []
    for query in dataset.queries:
        if query.query_id not in selected:
            continue
        ranked = rank_documents_via_chunks(
            service, query.text, chunk_doc_ids, matrix
        )
        relevant = set(query.relevant_doc_ids)
        row = QueryMetrics(
            query_id=query.query_id,
            category=query_category(query),
            reciprocal_rank=reciprocal_rank(relevant, ranked),
        )
        for k in K_VALUES:
            row.recall_at_k[k] = recall_at_k(relevant, ranked, k)
        for k in NDCG_K_VALUES:
            row.ndcg_at_k[k] = ndcg_at_k(relevant, ranked, k)
        per_query.append(row)

    aggregate = aggregate_query_metrics(
        per_query, k_values=K_VALUES, ndcg_k_values=NDCG_K_VALUES
    )
    return {
        "strategy": chunking.strategy,
        "chunking": {
            "max_tokens": chunking.max_tokens,
            "overlap_tokens": chunking.overlap_tokens,
            "max_chars": chunking.max_chars,
            "respect_sentences": chunking.respect_sentences,
            "respect_structure": chunking.respect_structure,
        },
        "nlp_enabled": pipeline is not None,
        "chunk_shape": asdict(stats),
        "metrics": {
            "recall_at_5": round(aggregate.recall_at_k.get(5, 0.0), 4),
            "recall_at_10": round(aggregate.recall_at_k.get(10, 0.0), 4),
            "mrr": round(aggregate.mrr, 4),
            "ndcg_at_5": round(aggregate.ndcg_at_k.get(5, 0.0), 4),
            "ndcg_at_10": round(aggregate.ndcg_at_k.get(10, 0.0), 4),
        },
    }


def compare_strategies(
    dataset_dir: Path,
    output_dir: Path | None = None,
    *,
    split: str = "val",
) -> dict[str, Any]:
    """Fixed-char baseline vs semantic chunking, with and without the NLP layer."""
    dataset = load_dataset(dataset_dir)
    morphology = NlpConfig(enabled=True, morphology=MorphologyConfig(enabled=True))

    runs = {
        "fixed_char": (ChunkingConfig(strategy="fixed_char"), None),
        "semantic": (
            ChunkingConfig(strategy="semantic", max_tokens=120, overlap_tokens=20),
            None,
        ),
        "semantic+nlp": (
            ChunkingConfig(strategy="semantic", max_tokens=120, overlap_tokens=20),
            morphology,
        ),
    }
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": dataset.dataset_version,
        "split": split,
        "note": (
            "Chunk-level retrieval over a public benchmark corpus. Scores use the "
            "deterministic stub embedding model unless a real model is wired in; "
            "chunk_shape statistics are model-independent and always meaningful."
        ),
        "runs": {},
    }
    for name, (chunking, nlp_config) in runs.items():
        print(f"Evaluating chunking run: {name}...", file=sys.stderr)
        report["runs"][name] = evaluate_chunking(
            dataset, chunking=chunking, nlp_config=nlp_config, split=split
        )

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "chunk-benchmark.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chunk-level retrieval benchmark")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--split", choices=("val", "test"), default="val")
    args = parser.parse_args(argv)

    report = compare_strategies(args.dataset, args.output, split=args.split)
    for name, run in report["runs"].items():
        shape = run["chunk_shape"]
        metrics = run["metrics"]
        print(
            f"{name:16} chunks={shape['total_chunks']:5d} "
            f"mean_tokens={shape['mean_tokens']:6.2f} "
            f"boundary_rate={shape['sentence_boundary_rate']:.3f} "
            f"recall@5={metrics['recall_at_5']:.4f} mrr={metrics['mrr']:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
