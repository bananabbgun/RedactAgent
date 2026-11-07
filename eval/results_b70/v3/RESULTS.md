# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 93.4% | 0.0% |
| B. + contextual LLM | 94.4% | 95.9% | 46.7% |
| C. + VLM | 95.5% | 96.1% | 56.7% |
| D. + agentic re-identification check (RedactAgent) | 96.7% | 96.0% | 63.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 90% | 90% | 92% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 94% | 94% | 94% | 100% |
| Date (event) | 102 | 100% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 100% |
| Quasi-identifier | 24 | 0% | 96% | 96% | 96% |
| Signature | 12 | 0% | 67% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, vLLM 0.33, gpt-oss-20b accuracy (greedy + loop guard) + Qwen2.5-VL-7B)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.83 s | 0.84 s | 5.02 s |
| rules | 0.00 s | 0.00 s | 0.01 s |
| llm | 10.55 s | 8.32 s | 34.15 s |
| vlm | 2.48 s | 2.28 s | 4.88 s |
| total | 16.07 s | 14.90 s | 36.41 s |
