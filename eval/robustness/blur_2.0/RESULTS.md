# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 54.0% | 87.9% | 0.0% |
| B. + contextual LLM | 89.1% | 91.4% | 26.7% |
| C. + VLM | 90.7% | 91.2% | 33.3% |
| D. + agentic re-identification check (RedactAgent) | 91.9% | 89.0% | 40.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 26% | 84% | 84% | 85% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 89% | 89% | 89% | 89% |
| Date (event) | 102 | 98% | 99% | 99% | 99% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 75% | 79% | 79% | 88% |
| Bank / card / policy no. | 6 | 50% | 83% | 83% | 100% |
| Quasi-identifier | 24 | 0% | 79% | 79% | 79% |
| Signature | 12 | 0% | 58% | 100% | 100% |
| Seal / chop | 12 | 92% | 92% | 100% | 100% |

## Latency per page (v2 degraded: blur_2.0)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.62 s | 0.78 s | 4.41 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 8.84 s | 8.11 s | 24.12 s |
| vlm | 2.39 s | 2.45 s | 4.82 s |
| total | 15.46 s | 15.23 s | 26.80 s |
