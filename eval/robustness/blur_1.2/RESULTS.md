# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.8% | 93.1% | 0.0% |
| B. + contextual LLM | 88.6% | 94.8% | 30.0% |
| C. + VLM | 90.2% | 95.1% | 40.0% |
| D. + agentic re-identification check (RedactAgent) | 93.4% | 92.0% | 56.7% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 35% | 78% | 78% | 87% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 99% | 99% | 99% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 67% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 75% | 75% | 75% |
| Signature | 12 | 0% | 58% | 100% | 100% |
| Seal / chop | 12 | 92% | 92% | 100% | 100% |

## Latency per page (v2 degraded: blur_1.2)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.70 s | 0.83 s | 4.51 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 10.16 s | 6.87 s | 43.82 s |
| vlm | 2.30 s | 2.04 s | 4.08 s |
| total | 18.08 s | 16.24 s | 53.72 s |
