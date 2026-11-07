# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 92.7% | 0.0% |
| B. + contextual LLM | 92.9% | 94.0% | 36.7% |
| C. + VLM | 93.4% | 94.4% | 40.0% |
| D. + agentic re-identification check (RedactAgent) | 94.7% | 91.3% | 50.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 87% | 87% | 89% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 100% |
| Quasi-identifier | 24 | 0% | 75% | 75% | 79% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T3_qwen3-14b-fp8)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.70 s | 0.86 s | 4.46 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 6.92 s | 6.94 s | 9.19 s |
| vlm | 2.02 s | 2.19 s | 3.50 s |
| total | 17.23 s | 16.95 s | 28.79 s |
