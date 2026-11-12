# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 56.6% | 92.4% | 0.0% |
| B. + contextual LLM | 92.9% | 94.8% | 40.0% |
| C. + VLM | 94.9% | 95.1% | 53.3% |
| D. + agentic re-identification check (RedactAgent) | 96.2% | 92.9% | 63.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 30% | 91% | 91% | 93% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 89% | 100% | 100% | 100% |
| Date (event) | 102 | 97% | 99% | 99% | 99% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 96% | 96% | 96% | 96% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 83% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 92% |
| Signature | 12 | 0% | 58% | 100% | 100% |
| Seal / chop | 12 | 75% | 75% | 100% | 100% |

## Latency per page (v2 degraded: jpeg_10)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.79 s | 0.90 s | 4.87 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 9.22 s | 7.20 s | 33.03 s |
| vlm | 2.30 s | 2.50 s | 3.73 s |
| total | 15.61 s | 14.06 s | 39.73 s |
