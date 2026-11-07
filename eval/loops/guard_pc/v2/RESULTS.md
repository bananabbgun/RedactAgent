# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 92.7% | 0.0% |
| B. + contextual LLM | 93.9% | 95.3% | 50.0% |
| C. + VLM | 94.4% | 95.6% | 53.3% |
| D. + agentic re-identification check (RedactAgent) | 95.5% | 94.7% | 60.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 88% | 88% | 90% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 83% |
| Quasi-identifier | 24 | 0% | 88% | 88% | 88% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, gpt-oss-20b (reasoning low) + Qwen2.5-VL-7B, loop guard, --enable-prefix-caching)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.85 s | 0.96 s | 4.90 s |
| rules | 0.00 s | 0.00 s | 0.01 s |
| llm | 9.58 s | 8.38 s | 23.63 s |
| vlm | 1.95 s | 2.04 s | 3.34 s |
| total | 15.83 s | 16.29 s | 29.84 s |
