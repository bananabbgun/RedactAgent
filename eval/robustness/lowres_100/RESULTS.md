# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.7% | 0.0% |
| B. + contextual LLM | 92.9% | 94.5% | 50.0% |
| C. + VLM | 93.4% | 94.8% | 50.0% |
| D. + agentic re-identification check (RedactAgent) | 93.7% | 93.5% | 53.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 84% | 84% | 85% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 88% | 88% | 88% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (v2 degraded: lowres_100)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.87 s | 0.83 s | 5.27 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 8.80 s | 8.19 s | 24.89 s |
| vlm | 2.23 s | 1.97 s | 4.78 s |
| total | 16.75 s | 15.18 s | 44.69 s |
