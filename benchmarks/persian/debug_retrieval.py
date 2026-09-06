"""Debug retrieval ranking for benchmark diagnosis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from benchmarks.persian.dataset import load_dataset, query_category
from benchmarks.persian.evaluate import debug_query_report, encode_corpus
from rag.embedding.config import load_candidate_config
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.registry import ModelRegistry
from rag.embedding.service import EmbeddingService


def _select_query_ids(dataset, *, category: str | None, limit: int) -> list[str]:
    validation = [q for q in dataset.queries if q.query_id in dataset.validation_query_ids]
    if category:
        validation = [q for q in validation if query_category(q) == category]
    return [q.query_id for q in validation[:limit]]


def format_report(report) -> str:
    lines = [
        "Query:",
        report.query_text,
        f"Category: {report.category}",
        f"Expected document IDs: {', '.join(report.expected_doc_ids)}",
        "",
        "Top hits:",
    ]
    for index, hit in enumerate(report.top_hits, start=1):
        marker = " *" if hit.doc_id in report.expected_doc_ids else ""
        lines.extend(
            [
                f"{index}. {hit.doc_id}{marker}",
                f"   score={hit.score:.6f}",
                f"   text={hit.text}",
                "",
            ]
        )
    for doc_id in report.expected_doc_ids:
        rank = report.expected_ranks.get(doc_id)
        score = report.expected_scores.get(doc_id)
        lines.append(f"Expected {doc_id}: rank={rank}, score={score}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Debug Persian embedding retrieval ranking")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--candidate-id", default="M0-baseline")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--category")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--query-id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    dataset = load_dataset(args.dataset)
    config = load_candidate_config(args.candidate_id, args.candidates, device=args.device)
    service = EmbeddingService(
        ModelRegistry.create(config),
        EmbeddingPreprocessor(config.preprocessing.normalization_version),
    )
    doc_ids, doc_matrix, corpus_text = encode_corpus(service, dataset)

    if args.query_id:
        query_ids = [args.query_id]
    else:
        query_ids = _select_query_ids(dataset, category=args.category, limit=args.limit)

    reports = [
        debug_query_report(
            service,
            dataset,
            query_id,
            doc_ids=doc_ids,
            doc_matrix=doc_matrix,
            corpus_text=corpus_text,
        )
        for query_id in query_ids
    ]

    if args.json:
        payload = [
            {
                "query_id": report.query_id,
                "query_text": report.query_text,
                "category": report.category,
                "expected_doc_ids": list(report.expected_doc_ids),
                "top_hits": [
                    {"doc_id": hit.doc_id, "score": hit.score, "text": hit.text}
                    for hit in report.top_hits
                ],
                "expected_ranks": report.expected_ranks,
                "expected_scores": report.expected_scores,
            }
            for report in reports
        ]
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    sys.stdout.reconfigure(encoding="utf-8")
    for report in reports:
        sys.stdout.write(format_report(report))
        sys.stdout.write("\n" + ("-" * 60) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
