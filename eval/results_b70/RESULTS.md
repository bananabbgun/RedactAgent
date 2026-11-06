# Evaluation results — 2x Intel Arc Pro B70 (baseline, 2026-11-06)

Synthetic corpus v1: 36 scanned pages, 582 ground-truth PII items. Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 76.5% | 97.4% | 0.0% |
| B. + contextual LLM | 96.0% | 97.7% | 47.2% |
| C. + VLM (RedactAgent) | 97.8% | 97.1% | 69.4% |

Same models as the laptop prototype (Qwen3-8B + Qwen2.5-VL-7B), now one model per Arc Pro B70 card via vLLM XPU 0.26:
accuracy is unchanged and throughput rises from ~2 pages/min (laptop) to 23.3 pages/min (8 pages in flight).

## Latency per page (8 pages in flight)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 10.51 s | 7.98 s | 24.49 s |
| rules | 0.00 s | 0.00 s | 0.01 s |
| llm | 8.98 s | 8.62 s | 12.32 s |
| vlm | 3.71 s | 3.78 s | 6.77 s |
| total | 19.56 s | 17.80 s | 34.57 s |
