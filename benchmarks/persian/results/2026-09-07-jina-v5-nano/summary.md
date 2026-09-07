# Persian Embedding Benchmark Summary

- Dataset: `fa-retrieval-v1`
- Split: `val`
- Models evaluated: 5

## Results

- **M0-baseline**: dim=384, Recall@5=0.8442, MRR=0.7882, load=54.253s
- **M1-e5-large**: dim=1024, Recall@5=0.8970, MRR=0.8650, load=12.436s
- **M2-bge-m3**: dim=1024, Recall@5=0.9026, MRR=0.8791, load=21.726s
- **M3-persian-heydari**: dim=1024, Recall@5=0.8729, MRR=0.8097, load=25.534s
- **M4-jina-v5-nano**: dim=768, Recall@5=0.9045, MRR=0.8793, load=42.599s

**Production model NOT selected** — awaiting human sign-off.