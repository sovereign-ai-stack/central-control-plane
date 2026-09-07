# Production Embedding Model Selection

**Status**: **SELECTED**
**Model**: `BAAI/bge-m3`
**Revision**: `5617a9f61b028005a4858fdac845db406aefb181`
**Candidate ID**: `M2-bge-m3`
**Date**: 2026-09-01
**Dimension**: 1024 (measured from the loaded model, not from config)

---

## 1. Decision

`BAAI/bge-m3` is the production embedding model. It is applied via
`config/embedding.yaml` with `production: true` and a pinned revision.

The selection follows the procedure in
[benchmark-spec.md §7](../../../specs/003-embedding-service/benchmark-spec.md):
rank by Recall@5 → MRR → latency → memory, then eliminate candidates outside
15% relative Recall@5 of the best and those breaching the latency/memory budget.

**M2 ranks first on both primary keys, so no tiebreak was needed.**

## 2. Evidence

Validation split, `fa-retrieval-v1`, `fa-norm-v1`, seed 42, CPU.
Source: `benchmarks/persian/results/2026-08-29-phase4/`.

| Candidate | dim | R@1 | R@3 | **R@5** | R@10 | **MRR** | nDCG@5 | nDCG@10 |
|-----------|----:|----:|----:|--------:|-----:|--------:|-------:|--------:|
| **M2-bge-m3** | 1024 | **0.850** | **0.881** | **0.903** | **0.958** | **0.879** | **0.877** | **0.895** |
| M1-e5-large | 1024 | 0.839 | 0.865 | 0.897 | 0.943 | 0.865 | 0.866 | 0.881 |
| M3-persian-heydari | 1024 | 0.761 | 0.828 | 0.873 | 0.933 | 0.810 | 0.817 | 0.836 |
| M0-baseline | 384 | 0.732 | 0.814 | 0.844 | 0.914 | 0.788 | 0.792 | 0.815 |

**M2 wins every reported quality metric.**

### Performance (same hardware profile, CPU)

| Candidate | R@5 gap | query p50 | p95 | p99 | throughput | load |
|-----------|--------:|----------:|----:|----:|-----------:|-----:|
| M2-bge-m3 | 0.00% | 152.6 ms | 166.5 ms | 186.5 ms | 23.8 chunks/s | 26.6 s |
| M1-e5-large | 0.62% | 173.4 ms | 198.6 ms | 248.7 ms | 18.6 chunks/s | 14.9 s |
| M3-persian-heydari | 3.29% | 156.5 ms | 166.8 ms | 183.0 ms | 24.5 chunks/s | 15.2 s |
| M0-baseline | 6.47% | 18.4 ms | 24.1 ms | 27.8 ms | 149.2 chunks/s | 37.3 s |

Budget (CPU soft targets): query p95 < 200 ms, ingest > 30 chunks/min,
peak RSS < 16 GB. **All four candidates pass**, so nothing was eliminated on
budget. M2 peak RSS measured at **~1.38 GB**, comfortably inside budget.

M2 also dominates M1 outright: better on every quality metric *and* lower
latency at every percentile.

## 3. Why not the cheaper baseline

M0 is ~6× faster and 384-dimensional (smaller vectors, less storage), and its
6.47% Recall@5 gap keeps it inside the 15% elimination threshold. It was not
selected because the spec ranks **Recall@5 first**, with latency only the third
key. M2's p95 of 166 ms is inside the CPU budget, so the extra quality costs
nothing that the budget does not already allow.

If a future deployment is latency-bound rather than quality-bound, M0 is the
documented fallback — it is already benchmarked and within the gate.

## 4. Architectural fit

| Concern | Assessment |
|---------|------------|
| Local execution | Runs locally via `sentence-transformers`. No external inference API. |
| Query/document symmetry | **No prefixes required** (`query_prefix: null`, `document_prefix: null`). e5 requires `"query: "` / `"passage: "`, an extra way for the two paths to diverge. |
| Persian NLP | XLM-RoBERTa multilingual base; benchmarked through the existing `fa-norm-v1` path with no NLP changes. |
| EmbeddingService | Uses the existing `sentence-transformers` backend and `ModelRegistry`; no new abstraction. |
| Weaviate | 1024-d vectors, `vectorizer: none`, cosine HNSW. Dimension recorded per chunk and validated at query time. |
| Ingestion / retrieval | Unchanged. Batch size 32, `normalize_embeddings: true` so cosine equals dot product. |

## 5. Gate checklist

- [x] Validation benchmark completed for M0–M3
- [x] Recall@5 within 15% of best candidate (M2 **is** the best, gap 0.00%)
- [x] Latency/memory budget reviewed — all candidates pass; M2 peak RSS ~1.38 GB
- [ ] **Test split evaluated once** — *not possible with the current dataset; see §6*
- [x] Production config pinned with `model_id` + `revision`

## 6. Deviation: the held-out test split is unusable

Spec §7 step 7 asks for a single held-out test-split run for the final report.
It was executed and produced **Recall@K = 0.0000 for every K**.

That is a dataset defect, not a model result. The `fa-retrieval-v1` test split is
degenerate by construction: its queries are
`"محتوای سند {title} چیست؟"` where `{title}` is synthetic metadata such as
`hr-0` that never appears in the corpus text. Labelled query/document pairs
share **zero** distinctive tokens, so any model scores 0.

Corroborating evidence already in the repository:

- `tests/integration/embedding/test_dataset_grounding.py::test_ungrounded_title_query_would_fail_recall_at_5`
  asserts exactly this failure mode as a known regression guard.
- `validate_dataset.py` and the dataset integrity suite only ever check the
  **validation** split; the test split was never grounded or validated.

The diagnostic record is kept at
`benchmarks/persian/results/2026-09-01-final-test-split/`, explicitly marked
`quality_metrics_valid: false` so it cannot be misread as a model score.

**Impact on this decision: none.** All four candidates were ranked on the
validation split, which is grounded and integrity-tested, and the ranking is
unambiguous. Regenerating a grounded test split is tracked as a RECOMMENDED
follow-up, not a blocker.

## 7. Migration

Changing the production model from `stub-v1` (384-d) to `bge-m3` (1024-d)
invalidates every previously stored vector. A **full reindex is required**.
Stored chunks record their `embedding_model_id` and `embedding_dimension`, and
retrieval raises `RetrievalModelMismatchError` / `RetrievalDimensionMismatchError`
rather than silently returning degraded results.

`StubEmbeddingModel` remains available and is used by the test suite, which pins
its own embedding config and never reads this file.

## 8. Subsequent candidate evaluations

This decision has been re-tested against later candidates. None has displaced
`bge-m3`.

| Date | Candidate | Outcome |
|------|-----------|---------|
| 2026-09-07 | `M4-jina-v5-nano` — [evaluation](jina-v5-nano-evaluation.md) | Not promoted. Quality difference vs M2 within noise (Recall@5 +0.21% relative); CC-BY-NC-4.0 licence forbids commercial use. |
