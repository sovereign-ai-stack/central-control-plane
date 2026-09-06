"""Validate fa-retrieval-v1 dataset integrity."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from benchmarks.persian.dataset import load_dataset


def _extract_doc_number(doc_text: str) -> str | None:
    import re

    match = re.search(r"\d+", doc_text)
    return match.group(0) if match else None


def validate_dataset(dataset_dir: Path) -> list[str]:
    errors: list[str] = []
    required_files = ("corpus.jsonl", "queries.jsonl", "splits.json")
    for name in required_files:
        if not (dataset_dir / name).exists():
            errors.append(f"Missing required file: {name}")

    if errors:
        return errors

    dataset = load_dataset(dataset_dir)
    corpus_ids = {doc.doc_id for doc in dataset.corpus}
    query_ids = {query.query_id for query in dataset.queries}

    if len(dataset.corpus) < 200:
        errors.append(f"Corpus too small: {len(dataset.corpus)} < 200")
    if len(dataset.validation_query_ids) < 80:
        errors.append(
            f"Validation split too small: {len(dataset.validation_query_ids)} < 80"
        )

    texts = [query.text for query in dataset.queries if query.query_id in dataset.validation_query_ids]
    if len(texts) != len(set(texts)):
        errors.append("Duplicate query text in validation set")

    for query in dataset.queries:
        if query.query_id not in dataset.validation_query_ids:
            continue
        if not query.relevant_doc_ids:
            errors.append(f"Query {query.query_id} has no relevant docs")
        for doc_id in query.relevant_doc_ids:
            if doc_id not in corpus_ids:
                errors.append(f"Query {query.query_id} references missing doc {doc_id}")

    if not dataset.validation_query_ids.issubset(query_ids):
        errors.append("validation_query_ids contains unknown query ids")

    val_queries = [q for q in dataset.queries if q.query_id in dataset.validation_query_ids]
    corpus_text = {doc.doc_id: doc.text for doc in dataset.corpus}

    if any(not query.category for query in val_queries):
        errors.append("Validation queries must include explicit category field")

    allowed_categories = {
        "semantic",
        "paraphrase",
        "mixed_language",
        "technical",
        "short_query",
        "long_query",
        "zwnj",
        "arabic_char_variants",
        "morphology",
        "plural_forms",
        "verb_forms",
        "spelling_variants",
    }
    for query in val_queries:
        if query.category and query.category not in allowed_categories:
            errors.append(f"Query {query.query_id} has invalid category {query.category}")

    # Grounding check: template-generated queries must reference their document number.
    for query in val_queries:
        doc_id = query.relevant_doc_ids[0]
        doc_text = corpus_text[doc_id]
        doc_number = _extract_doc_number(doc_text)
        if doc_number is None:
            continue
        if query.category in {"arabic_char_variants", "zwnj", "spelling_variants"}:
            continue
        if doc_number not in query.text:
            errors.append(
                f"Query {query.query_id} ({query.category}) is not grounded in labeled document number"
            )

    domains = Counter(q.domain for q in val_queries)
    if sum(1 for count in domains.values() if count >= 15) < 3:
        errors.append("Need at least 3 domains with >=15 validation queries each")
    if sum(1 for q in val_queries if q.query_length == "short") < 10:
        errors.append("Need >=10 short validation queries")
    if sum(1 for q in val_queries if q.query_length == "long") < 10:
        errors.append("Need >=10 long validation queries")
    if sum(1 for q in val_queries if q.domain == "technical") < 15:
        errors.append("Need >=15 technical validation queries")
    if sum(1 for q in val_queries if q.language == "mixed") < 10:
        errors.append("Need >=10 mixed-language validation queries")

    schema_path = dataset_dir / "schema.json"
    if not schema_path.exists():
        errors.append("Missing schema.json")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Persian retrieval benchmark dataset")
    parser.add_argument("--dataset", type=Path, required=True)
    args = parser.parse_args(argv)

    errors = validate_dataset(args.dataset)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    dataset = load_dataset(args.dataset)
    summary = {
        "dataset_version": dataset.dataset_version,
        "corpus_size": len(dataset.corpus),
        "validation_queries": len(dataset.validation_query_ids),
        "test_queries": len(dataset.test_query_ids),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
