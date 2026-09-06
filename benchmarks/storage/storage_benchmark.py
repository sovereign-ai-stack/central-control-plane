"""
Storage backend benchmark: InMemory linear scan vs Weaviate.

Measures ingestion batch throughput and vector-search latency so the production
storage boundary has real numbers rather than assumptions. This is a
characterisation harness, not an optimisation exercise — the goal is to know
where the boundary stands.

Usage:

    docker compose -f docker-compose.weaviate.yml up -d
    RAG_WEAVIATE_TEST_URL=localhost:18080 \\
        python -m benchmarks.storage.storage_benchmark --chunks 2000
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from rag.ingestion.types import StoredChunk
from rag.storage.chunk_store import InMemoryChunkStore
from rag.storage.vector_search import VectorSearchScope

MODEL_ID = "bench-model"


@dataclass(frozen=True, slots=True)
class BackendResult:
    backend: str
    chunks: int
    documents: int
    ingest_seconds: float
    ingest_chunks_per_second: float
    search_p50_ms: float
    search_p95_ms: float
    search_mean_ms: float
    top_k: int
    queries: int


def _unit_vector(rng: np.random.Generator, dim: int) -> np.ndarray:
    vector = rng.normal(size=dim).astype(np.float32)
    return vector / np.linalg.norm(vector)


def build_corpus(
    *,
    chunks: int,
    documents: int,
    dim: int,
    company_id: uuid.UUID,
    department_id: uuid.UUID,
    seed: int = 42,
) -> tuple[list[tuple[uuid.UUID, list[StoredChunk]]], list[uuid.UUID]]:
    rng = np.random.default_rng(seed)
    per_document = max(chunks // documents, 1)
    corpus: list[tuple[uuid.UUID, list[StoredChunk]]] = []
    document_ids: list[uuid.UUID] = []

    for _ in range(documents):
        document_id = uuid.uuid4()
        document_ids.append(document_id)
        batch = [
            StoredChunk(
                chunk_id=uuid.uuid4(),
                document_id=document_id,
                company_id=company_id,
                department_id=department_id,
                document_version=1,
                chunk_index=index,
                content=f"chunk {index} of document {document_id}",
                content_hash=f"hash-{index}",
                embedding=_unit_vector(rng, dim),
                embedding_model_id=MODEL_ID,
                embedding_dimension=dim,
            )
            for index in range(per_document)
        ]
        corpus.append((document_id, batch))
    return corpus, document_ids


def measure_backend(
    store: Any,
    corpus: list[tuple[uuid.UUID, list[StoredChunk]]],
    document_ids: list[uuid.UUID],
    *,
    backend: str,
    dim: int,
    top_k: int,
    queries: int,
    company_id: uuid.UUID,
    department_id: uuid.UUID,
) -> BackendResult:
    total_chunks = sum(len(batch) for _doc, batch in corpus)

    started = time.perf_counter()
    for document_id, batch in corpus:
        store.replace_document_chunks(document_id, batch)
    ingest_seconds = time.perf_counter() - started

    scope = VectorSearchScope(
        company_id=company_id,
        allowed_department_ids=(department_id,),
        allowed_document_ids=frozenset(document_ids),
    )
    rng = np.random.default_rng(7)
    latencies: list[float] = []
    for _ in range(queries):
        query = _unit_vector(rng, dim)
        query_started = time.perf_counter()
        store.search(
            query,
            scope,
            top_k=top_k,
            query_model_id=MODEL_ID,
            query_dimension=dim,
        )
        latencies.append((time.perf_counter() - query_started) * 1000)

    latencies.sort()
    return BackendResult(
        backend=backend,
        chunks=total_chunks,
        documents=len(corpus),
        ingest_seconds=round(ingest_seconds, 4),
        ingest_chunks_per_second=round(total_chunks / ingest_seconds, 1),
        search_p50_ms=round(statistics.median(latencies), 3),
        search_p95_ms=round(latencies[int(len(latencies) * 0.95) - 1], 3),
        search_mean_ms=round(statistics.fmean(latencies), 3),
        top_k=top_k,
        queries=queries,
    )


def run(
    *,
    chunks: int,
    documents: int,
    dim: int,
    top_k: int,
    queries: int,
    output: Path | None,
) -> dict[str, Any]:
    company_id = uuid.uuid4()
    department_id = uuid.uuid4()
    corpus, document_ids = build_corpus(
        chunks=chunks,
        documents=documents,
        dim=dim,
        company_id=company_id,
        department_id=department_id,
    )

    results: list[BackendResult] = [
        measure_backend(
            InMemoryChunkStore(),
            corpus,
            document_ids,
            backend="in_memory",
            dim=dim,
            top_k=top_k,
            queries=queries,
            company_id=company_id,
            department_id=department_id,
        )
    ]

    from tests.storage_support import (
        unique_collection_name,
        weaviate_available_for_tests,
        weaviate_config,
    )

    if weaviate_available_for_tests():
        from rag.storage.weaviate.store import WeaviateChunkStore

        name = unique_collection_name("Bench")
        store = WeaviateChunkStore(weaviate_config(name))
        try:
            results.append(
                measure_backend(
                    store,
                    corpus,
                    document_ids,
                    backend="weaviate",
                    dim=dim,
                    top_k=top_k,
                    queries=queries,
                    company_id=company_id,
                    department_id=department_id,
                )
            )
        finally:
            store.client.collections.delete(name)
            store.close()
    else:
        print(
            "Weaviate not configured (set RAG_WEAVIATE_TEST_URL); "
            "reporting in-memory only",
            file=sys.stderr,
        )

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "parameters": {
            "chunks": chunks,
            "documents": documents,
            "dimension": dim,
            "top_k": top_k,
            "queries": queries,
        },
        "results": [asdict(item) for item in results],
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Storage backend benchmark")
    parser.add_argument("--chunks", type=int, default=2000)
    parser.add_argument("--documents", type=int, default=100)
    parser.add_argument("--dim", type=int, default=384)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--queries", type=int, default=50)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    report = run(
        chunks=args.chunks,
        documents=args.documents,
        dim=args.dim,
        top_k=args.top_k,
        queries=args.queries,
        output=args.output,
    )
    print(
        f"{'backend':12} {'chunks':>7} {'ingest/s':>10} "
        f"{'p50 ms':>9} {'p95 ms':>9} {'mean ms':>9}"
    )
    for row in report["results"]:
        print(
            f"{row['backend']:12} {row['chunks']:>7} "
            f"{row['ingest_chunks_per_second']:>10.1f} "
            f"{row['search_p50_ms']:>9.3f} {row['search_p95_ms']:>9.3f} "
            f"{row['search_mean_ms']:>9.3f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
