# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 91.9% | 0.0% |
| B. + contextual LLM | 90.4% | 94.1% | 43.3% |
| C. + VLM | 91.4% | 94.0% | 50.0% |
| D. + agentic re-identification check (RedactAgent) | 93.2% | 91.1% | 56.7% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 34% | 82% | 82% | 85% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 98% | 99% | 99% | 99% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 96% | 96% | 96% |
| Medical record no. | 24 | 96% | 96% | 96% | 96% |
| Bank / card / policy no. | 6 | 67% | 83% | 83% | 100% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 88% |
| Signature | 12 | 0% | 67% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (v2 degraded: lowres_75)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.80 s | 0.80 s | 4.92 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 13.63 s | 10.44 s | 41.15 s |
| vlm | 2.30 s | 2.44 s | 3.90 s |
| total | 20.68 s | 16.51 s | 52.01 s |
