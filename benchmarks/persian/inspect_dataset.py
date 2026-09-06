"""Inspect query-document relevance in fa-retrieval-v1."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from benchmarks.persian.dataset import load_dataset, query_category

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    dataset_dir = Path(__file__).resolve().parent / "data" / "fa-retrieval-v1"
    dataset = load_dataset(dataset_dir)
    corpus = {doc.doc_id: doc.text for doc in dataset.corpus}
    meta: dict[str, dict] = {}
    for line in (dataset_dir / "corpus.jsonl").open(encoding="utf-8"):
        row = json.loads(line)
        meta[row["doc_id"]] = row.get("metadata", {})

    by_cat: dict[str, list] = defaultdict(list)
    for query in dataset.queries:
        if query.query_id not in dataset.validation_query_ids:
            continue
        by_cat[query_category(query)].append(query)

    for category in sorted(by_cat):
        print(f"=== {category} count={len(by_cat[category])} ===")
        for query in by_cat[category][:5]:
            doc_id = query.relevant_doc_ids[0]
            print(f"Q: {query.text}")
            print(f"D: {corpus[doc_id]}")
            print(f"title: {meta.get(doc_id, {}).get('title')}")
            print("---")


if __name__ == "__main__":
    main()
