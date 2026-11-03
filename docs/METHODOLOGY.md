# KPI definitions

| KPI | Definition | Target |
|-----|------------|--------|
| Accuracy | Share of annotations on **gold** tasks that equal the gold label | ≥ 90% |
| Throughput | Annotations per active hour (`count / Σ duration`) | track |
| Avg handle time | Mean seconds per annotation | track |
| Rework rate | Reviewed annotations that were sent back | ≤ 10% |
| Fleiss' κ | Chance-corrected agreement for ≥ 2 raters per task | ≥ 0.70 |
| Krippendorff's α | Nominal alpha, robust to missing ratings | ≥ 0.70 |
| Cohen's κ | Pairwise agreement between two annotators | ≥ 0.70 |
| Agreement rate | Share of an annotator's labels matching the majority of the other raters | ≥ 80% |

κ interpretation (Landis & Koch): < 0.4 poor/fair, 0.4–0.6 moderate, 0.6–0.8 substantial, > 0.8 almost perfect.

Data: each task is labelled by 3 distinct annotators; ~15% of tasks carry gold labels; ~25% of annotations are reviewed.
The dataset is **synthetic** (`src/aqkpi/generate_data.py`) — swap in real exports with the same three-table schema
(`sql/schema.sql`) to reuse the whole pipeline.
