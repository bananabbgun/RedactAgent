# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 56.8% | 93.6% | 0.0% |
| B. + contextual LLM | 87.6% | 95.6% | 26.7% |
| C. + VLM | 89.4% | 95.8% | 36.7% |
| D. + agentic re-identification check (RedactAgent) | 90.9% | 95.4% | 43.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 29% | 81% | 81% | 85% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 89% | 94% | 94% | 94% |
| Date (event) | 102 | 98% | 98% | 98% | 98% |
| Phone number | 24 | 92% | 92% | 92% | 92% |
| Address | 24 | 0% | 96% | 96% | 96% |
| Medical record no. | 24 | 96% | 96% | 96% | 96% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 100% |
| Quasi-identifier | 24 | 0% | 75% | 75% | 75% |
| Signature | 12 | 0% | 33% | 92% | 92% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, vLLM 0.33, gpt-oss-20b throughput (T=1.0) + Qwen2.5-VL-7B)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.79 s | 0.83 s | 4.81 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 7.71 s | 6.73 s | 20.95 s |
| vlm | 2.57 s | 2.84 s | 4.81 s |
| total | 13.50 s | 12.15 s | 27.52 s |
