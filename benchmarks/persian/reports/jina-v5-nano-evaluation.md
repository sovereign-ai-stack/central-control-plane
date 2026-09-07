# Candidate Evaluation — `jina-embeddings-v5-text-nano`

**Status**: **EVALUATED — NOT PROMOTED**
**Model**: `jinaai/jina-embeddings-v5-text-nano`
**Candidate ID**: `M4-jina-v5-nano`
**Benchmark run**: 2026-09-07 (`2026-09-07T09:11:18Z`)
**Dimension**: 768 (measured from the loaded model, not from config)
**Production model unchanged**: `M2-bge-m3` — see [selection-decision.md](selection-decision.md)

---

## 1. Purpose

Measure a fifth candidate against the four already benchmarked, under the
**existing** benchmark runner, dataset, ground truth and metrics, so the
comparison is decision-grade rather than indicative. No new benchmark, no new
dataset, no new metric.

The question this answers: does `jina-embeddings-v5-text-nano` beat `bge-m3`
by enough to justify replacing the production model and reindexing every stored
vector?

**Answer: no.** Its quality edge over M2 is within noise (Recall@5 +0.21%
relative, two queries out of 1078). Its real advantages are size and median
latency, and it carries a non-commercial licence.

## 2. Models compared

| ID | Model | dim | Notes |
|----|-------|----:|-------|
| M0-baseline | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | 384 | baseline |
| M1-e5-large | `intfloat/multilingual-e5-large` | 1024 | asymmetric: `"query: "` / `"passage: "` |
| **M2-bge-m3** | `BAAI/bge-m3` @ `5617a9f6…` | 1024 | **production**, symmetric |
| M3-persian-heydari | `heydariAI/persian-embeddings` | 1024 | Persian fine-tune |
| **M4-jina-v5-nano** | `jinaai/jina-embeddings-v5-text-nano` | 768 | **this evaluation**, asymmetric |

## 3. Model characteristics — `jina-embeddings-v5-text-nano`

Taken from the official model card and repository configuration, not inferred
from how earlier candidates behave.

| Property | Value |
|----------|-------|
| Base model | `EuroBERT/EuroBERT-210m` |
| Parameters | 239M |
| Embedding dimension | 768 (Matryoshka: 32/64/128/256/512/768 — **not** truncated here) |
| Max sequence length | 8192 |
| Pooling | last-token |
| Normalization | L2, applied inside the model's own forward |
| Similarity | cosine (`config_sentence_transformers.json`) |
| Tasks | `retrieval`, `text-matching`, `clustering`, `classification` (LoRA adapters) |
| Released | 2026-02-18 |
| Licence | **CC-BY-NC-4.0 — non-commercial** |
| Requires | `transformers>=4.57`, `peft>=0.15.2`, `trust_remote_code=True` |

### 3.1 Query / document encoding

This model is **asymmetric** and it is the only candidate that needs a task
selected before it will encode anything at all. Three model-specific details,
each verified against the repository configuration:

1. **Task adapter.** The checkpoint carries four LoRA adapters. The repo's
   `custom_st.Transformer.forward` raises if no task is set. The benchmark
   measures retrieval, so the adapter is pinned to `retrieval` at load time
   (`model_kwargs={"default_task": "retrieval"}`) and never varies per call.
   Using `text-matching` would have scored a different model.

2. **Prompts.** `config_sentence_transformers.json` defines
   `query: "Query: "` and `document: "Document: "`. These are configured as the
   candidate's `query_prefix` / `document_prefix`, so the **existing** prefix
   path in `SentenceTransformersBackend` applies them. Prepending a prompt
   string is exactly what `prompt_name=` does inside sentence-transformers, so
   this is the official encoding, not an approximation of it.

3. **The double-prompt trap.** The same file sets
   `default_prompt_name: "document"`, which makes sentence-transformers prepend
   `"Document: "` to *every* call — queries included — on top of the prefix the
   backend already applies. It is cleared at load time. Verified:

   ```
   is_query=True  -> 'Query: test<|end_of_text|>'      Query:=1  Document:=0
   is_query=False -> 'Document: test<|end_of_text|>'   Query:=0  Document:=1
   ```

   The effect is not cosmetic. On a three-document probe, correct prompting
   separates the relevant document far more sharply:

   ```
   official prompts : sims=[0.8743, 0.0894, 0.3459]
   no prompt        : sims=[0.6509, 0.0537, 0.4187]
   ```

## 4. Benchmark configuration

Identical for all five candidates; all five ran in **one process, one run**.

| Setting | Value |
|---------|-------|
| Dataset | `fa-retrieval-v1` — 220 documents, 1133 queries |
| Split | `val` — 1078 queries (the `test` split is degenerate; see [selection-decision.md §6](selection-decision.md)) |
| Ground truth | unchanged, `relevant_doc_ids` per query |
| Preprocessing | `fa-norm-v1`, NLP layer off (`--nlp off`) |
| Device | CPU |
| Batch size | 32 |
| Sequence length | each model's native default (not overridden) |
| Normalize embeddings | true — cosine equals dot product |
| Seed | 42 |
| Retrieval | full-corpus cosine ranking over all 220 documents |
| Warm-up | 20 queries before any timing |
| Timing | per-query `perf_counter` over the first 500 queries; p50/p95/p99 by index into the sorted sample |
| Throughput | one batch of 128 documents, wall clock |
| Load policy | `strict_load: true` — a failed load fails the candidate; `StubEmbeddingModel` fallback forbidden |

### 4.1 Hardware

| | |
|---|---|
| CPU | Intel64 Family 6 Model 158 Stepping 10 |
| GPU | none (CPU-only run) |
| OS | Windows-10-10.0.19045-SP0 |
| Python / torch | 3.14.7 / 2.13.0+cpu |

### 4.2 Metric definitions

As implemented in `benchmarks/persian/metrics.py`, unchanged by this evaluation:

- **Recall@k** — hit rate: 1.0 if any relevant document appears in the top k,
  else 0.0, averaged over queries. Not the fraction of relevant documents found.
- **MRR** — reciprocal of the rank of the first relevant document.
- **nDCG@k** — binary gain, `1/log2(rank+1)`, normalised by the ideal ordering.
- **Latency** — single-query embedding time, milliseconds.
- **Throughput** — documents embedded per second in a 128-document batch.

## 5. Results

Source of every number: `../results/2026-09-07-jina-v5-nano/summary.json`.
Nothing below is hand-entered.

| Model | dim | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR | nDCG@5 | nDCG@10 | Latency p50 | Throughput |
|-------|----:|---------:|---------:|---------:|----------:|----:|-------:|--------:|------------:|-----------:|
| M0-baseline | 384 | 0.7319 | 0.8145 | 0.8442 | 0.9137 | 0.7882 | 0.7923 | 0.8148 | **24.1 ms** | **134.43/s** |
| M1-e5-large | 1024 | 0.8386 | 0.8646 | 0.8970 | 0.9434 | 0.8650 | 0.8661 | 0.8807 | 208.0 ms | 13.24/s |
| M2-bge-m3 | 1024 | **0.8497** | **0.8813** | 0.9026 | 0.9583 | 0.8791 | 0.8770 | 0.8948 | 253.5 ms | 16.31/s |
| M3-persian-heydari | 1024 | 0.7607 | 0.8284 | 0.8729 | 0.9332 | 0.8097 | 0.8165 | 0.8360 | 203.7 ms | 16.94/s |
| **M4-jina-v5-nano** | 768 | **0.8497** | 0.8803 | **0.9045** | **0.9620** | **0.8793** | **0.8776** | **0.8958** | 145.0 ms | 16.46/s |

### 5.1 Full performance detail

| Model | p50 | p95 | p99 | Throughput | Peak RSS | Load |
|-------|----:|----:|----:|-----------:|---------:|-----:|
| M0-baseline | 24.1 ms | 64.2 ms | 91.2 ms | 134.43/s | 957 MB | 54.3 s |
| M1-e5-large | 208.0 ms | 361.5 ms | 526.6 ms | 13.24/s | 1547 MB | 12.4 s |
| M2-bge-m3 | 253.5 ms | 516.2 ms | 854.5 ms | 16.31/s | 1866 MB | 21.7 s |
| M3-persian-heydari | 203.7 ms | 318.0 ms | 494.4 ms | 16.94/s | 1866 MB | 25.5 s |
| M4-jina-v5-nano | 145.0 ms | 522.0 ms | **1539.9 ms** | 16.46/s | 1866 MB | 42.6 s |

### 5.2 Recall@5 by query category

| Category | M0 | M1 | M2 | M3 | **M4** |
|----------|---:|---:|---:|---:|-------:|
| semantic | 0.8864 | 0.9227 | **0.9273** | 0.9227 | 0.9227 |
| paraphrase | 0.8397 | 0.8846 | 0.8846 | 0.8654 | 0.8846 |
| mixed_language | 1.0000 | 1.0000 | 1.0000 | 0.9487 | 1.0000 |
| technical | 0.9744 | 1.0000 | 1.0000 | 0.9744 | 1.0000 |
| short_query | 0.8077 | 0.8590 | 0.8782 | 0.7500 | **0.8974** |
| long_query | 0.8590 | **0.8974** | **0.8974** | 0.8910 | 0.8910 |
| zwnj | 0.8526 | 0.8974 | 0.8974 | 0.8910 | 0.8974 |
| arabic_char_variants | 0.7308 | 0.8590 | 0.8718 | 0.8526 | **0.8782** |

## 6. M4 against each incumbent

Absolute and relative change, M4 minus the incumbent.

### 6.1 vs M2-bge-m3 (production) — the decisive comparison

| Metric | M2 | M4 | Absolute | Relative |
|--------|---:|---:|---------:|---------:|
| Recall@1 | 0.8497 | 0.8497 | ±0.0000 | 0.00% |
| Recall@3 | 0.8813 | 0.8803 | −0.0009 | −0.11% |
| Recall@5 | 0.9026 | 0.9045 | +0.0019 | +0.21% |
| Recall@10 | 0.9583 | 0.9620 | +0.0037 | +0.39% |
| MRR | 0.8791 | 0.8793 | +0.0002 | +0.02% |
| nDCG@5 | 0.8770 | 0.8776 | +0.0005 | +0.06% |
| nDCG@10 | 0.8948 | 0.8958 | +0.0011 | +0.12% |
| Latency p50 | 253.5 ms | 145.0 ms | −108.5 ms | **−42.8%** |
| Latency p95 | 516.2 ms | 522.0 ms | +5.7 ms | +1.1% |
| Latency p99 | 854.5 ms | 1539.9 ms | +685.5 ms | **+80.2%** |
| Throughput | 16.31/s | 16.46/s | +0.15/s | +0.9% |

Recall@1 is **exactly** equal (`0.849721706864564` for both). Every quality
delta is at the third or fourth decimal place — on 1078 queries, Recall@5
differs by two queries.

### 6.2 vs M1-e5-large

| Metric | Absolute | Relative |
|--------|---------:|---------:|
| Recall@1 | +0.0111 | +1.33% |
| Recall@3 | +0.0158 | +1.82% |
| Recall@5 | +0.0074 | +0.83% |
| Recall@10 | +0.0186 | +1.97% |
| MRR | +0.0143 | +1.65% |
| nDCG@5 | +0.0115 | +1.32% |
| nDCG@10 | +0.0151 | +1.72% |
| Latency p50 | −63.0 ms | −30.3% |
| Throughput | +3.22/s | +24.3% |

M4 dominates M1 outright: better on every quality metric, lower median latency,
higher throughput, and 25% smaller vectors.

### 6.3 vs M3-persian-heydari

| Metric | Absolute | Relative |
|--------|---------:|---------:|
| Recall@1 | +0.0891 | +11.71% |
| Recall@3 | +0.0519 | +6.27% |
| Recall@5 | +0.0315 | +3.61% |
| Recall@10 | +0.0288 | +3.08% |
| MRR | +0.0696 | +8.59% |
| nDCG@5 | +0.0610 | +7.47% |
| nDCG@10 | +0.0598 | +7.16% |
| Latency p50 | −58.7 ms | −28.8% |
| Throughput | −0.48/s | −2.8% |

A general multilingual model beats the Persian-specific fine-tune on this
Persian benchmark, on every quality metric.

### 6.4 vs M0-baseline

| Metric | Absolute | Relative |
|--------|---------:|---------:|
| Recall@1 | +0.1178 | +16.10% |
| Recall@5 | +0.0603 | +7.14% |
| MRR | +0.0911 | +11.55% |
| nDCG@10 | +0.0810 | +9.94% |
| Latency p50 | +120.9 ms | +502.2% |
| Throughput | −117.97/s | −87.8% |

Much better quality, roughly 6× the median latency and one eighth the
throughput. This is the quality/speed trade-off in its starkest form.

## 7. Analysis

### 7.1 Quality

Best per metric, from the run:

| Metric | Winner | Value |
|--------|--------|------:|
| Recall@1 | **M2 and M4 tied** | 0.8497 |
| Recall@3 | M2-bge-m3 | 0.8813 |
| Recall@5 | M4-jina-v5-nano | 0.9045 |
| Recall@10 | M4-jina-v5-nano | 0.9620 |
| MRR | M4-jina-v5-nano | 0.8793 |
| nDCG@5 | M4-jina-v5-nano | 0.8776 |
| nDCG@10 | M4-jina-v5-nano | 0.8958 |

M4 leads five of seven, ties one, and loses one — but every margin over M2 is
under half a percent relative. Against M1, M3 and M0 the margins are real
(1–16% relative); against M2 they are not distinguishable from noise on a
1078-query set.

By category, M4's gains over M2 are concentrated in `short_query` (+0.0192) and
`arabic_char_variants` (+0.0064); it loses slightly on `semantic` (−0.0045) and
`long_query` (−0.0064). Both models saturate `mixed_language` and `technical`
at 1.0000.

### 7.2 Performance

| Metric | Winner | Value |
|--------|--------|------:|
| Lowest latency (p50/p95/p99) | M0-baseline | 24.1 / 64.2 / 91.2 ms |
| Highest throughput | M0-baseline | 134.43/s |

Among the quality-competitive models, M4 has the best median latency
(145.0 ms, 42.8% below M2) but **the worst tail by a wide margin**: p99 of
1539.9 ms against M2's 854.5 ms. Its p95 (522.0 ms) is level with M2's
(516.2 ms), so the entire regression sits in the last few percent of requests.
The plausible cause is variable sequence length interacting with an 8192-token
window and last-token pooling, but this run does not isolate it.

None of the four large models met the project's CPU soft target of p95 < 200 ms
on this hardware — including the production model. That target was met on the
2026-08-29 hardware profile; this machine is slower. It is a property of the
run, not a new regression, and it does not affect the ranking, which is
internally consistent because all five models were measured back to back in one
process.

### 7.3 Trade-off

M4's case is **not** quality. It is:

- **25% smaller vectors** (768 vs 1024) — less index storage, less memory, less
  bandwidth per query.
- **58% fewer parameters** (239M vs 568M).
- **43% lower median latency**.

for statistically indistinguishable retrieval quality. That is a genuinely
attractive efficiency profile. It is offset by a worse p99 and by two
non-technical blockers (§8).

## 8. Recommendation

**Keep M4 in the candidate set. Do not promote it to production.**

1. **Is it better than the current models?** Better than M0, M1 and M3 on every
   quality metric, by margins that are real. Against M2 — the production model —
   the difference is noise.
2. **Where better / worse?** Better: Recall@5, Recall@10, MRR, nDCG@5, nDCG@10,
   median latency, vector size, model size. Worse: Recall@3, p99 latency,
   `semantic` and `long_query` categories.
3. **Is the quality worth the speed?** The question inverts here: the *speed and
   size* are the gain, and the quality is a wash. On that framing, yes — but not
   enough to justify a full reindex of every stored vector (§7 of
   [selection-decision.md](selection-decision.md)), which is what changing the
   production model costs.
4. **Suitable for this project's Persian RAG?** Technically yes. It is fully
   competitive on Persian, reaching 1.0000 Recall@5 on `mixed_language` and
   `technical` exactly like M2, and it leads on `arabic_char_variants` and
   `short_query`. Two non-technical obstacles are decisive for a production
   decision, though:
   - **Licence CC-BY-NC-4.0 forbids commercial use.**
   - **It requires `trust_remote_code=True`**, executing code from the model
     repository inside the serving process — a deliberate decision for a system
     positioned as sovereign.
5. **Admit to the candidate set?** **Yes, as a benchmarked candidate** — it is
   the strongest latency-per-quality option on record and the natural upgrade
   path from M0 if the deployment ever becomes latency-bound. **Not as the
   production model**, on the licence and reindex-cost grounds above.

Nothing here changes the standing selection of `BAAI/bge-m3`.

## 9. Limitations and caveats

- **Statistical power.** 1078 validation queries. A Recall@5 difference of
  0.0019 is two queries. No confidence intervals or significance test are
  computed by this benchmark, so the M2/M4 ordering should not be treated as
  established. Every margin between M2 and M4 is below the resolution of the
  measurement.
- **Peak RSS is process-wide.** The runner reports the process high-water mark,
  so M2, M3 and M4 all show 1866 MB — the maximum reached by the time each ran,
  not each model's own footprint. Only M0's figure (957 MB, first to run) is
  attributable to a single model. This is pre-existing runner behaviour, shared
  with the earlier runs.
- **Latency is not comparable across runs.** Absolute latency on this machine is
  higher than the 2026-08-29 run. Comparisons are valid *within* this run only.
- **Single run, no repetitions.** One measurement per model; no variance
  estimate.
- **Validation split only.** The `test` split of `fa-retrieval-v1` is degenerate
  by construction and unusable — see [selection-decision.md §6](selection-decision.md).
- **CPU only.** No GPU result. The model card recommends bfloat16 and
  flash-attention on GPU; neither applies here, and float32 was used for all
  candidates.
- **Matryoshka not exercised.** M4 was evaluated at its full 768 dimensions.
  Its 512/256/128 truncations may shift the size/quality trade-off and were not
  measured.
- **Revision not pinned.** M4 runs against `main` of the model repository
  (`revision: null`), unlike M2. Pinning would be mandatory before any
  production use.

## 10. Artifacts

Directory: [`../results/2026-09-07-jina-v5-nano/`](../results/2026-09-07-jina-v5-nano/)

| File | Contents |
|------|----------|
| `M0-baseline.json` | per-model metrics |
| `M1-e5-large.json` | per-model metrics |
| `M2-bge-m3.json` | per-model metrics |
| `M3-persian-heydari.json` | per-model metrics |
| **`M4-jina-v5-nano.json`** | **per-model metrics — this evaluation** |
| `summary.json` | all five models, dataset version, git commit, hardware profile, timestamp |
| `summary.md` | generated headline summary |

`M4-jina-v5-nano.json` uses the same schema as every earlier artifact —
verified key-by-key against `../results/2026-08-29-phase4/M2-bge-m3.json`. Its
`dimension_source` is `model.info.dimension`, meaning 768 was read from the
loaded model rather than from configuration.

### 10.1 Reproduction

```bash
python -m benchmarks.persian.generate_dataset --version fa-retrieval-v1
python -m benchmarks.persian.run_benchmark \
  --dataset benchmarks/persian/data/fa-retrieval-v1 \
  --candidates benchmarks/persian/config/candidates.yaml \
  --output benchmarks/persian/results/2026-09-07-jina-v5-nano \
  --device cpu --seed 42 --split val --nlp off
```

M4 additionally requires `transformers>=4.57` and `peft>=0.15.2`
(`benchmarks/persian/requirements-bench.txt`).

## 11. Validation performed

- All five candidates loaded as **real backends** — `StubEmbeddingModel` was
  forbidden for the run by `strict_load: true` and confirmed absent afterwards
  by reloading each candidate and asserting its backend class.
- Runtime dimension matches each artifact: 384 / 1024 / 1024 / 1024 / 768.
- Query and document embeddings verified for every candidate: correct shape, no
  NaN or Inf, unit L2 norm, and the relevant document outranking an irrelevant
  one.
- Artifact schema and `summary.json` validated; each summary entry is
  byte-identical to its standalone artifact file.
- **No regression in the incumbents.** M0–M3 reproduce their historical quality
  metrics from `../results/2026-08-29-phase4/`: M0 Recall@5 0.8442 vs 0.8442,
  M1 0.8970 vs 0.897, M2 0.9026 vs 0.903, M3 0.8729 vs 0.873.
