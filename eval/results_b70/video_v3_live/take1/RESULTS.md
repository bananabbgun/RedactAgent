# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 93.9% | 0.0% |
| B. + contextual LLM | 94.7% | 96.1% | 46.7% |
| C. + VLM | 95.7% | 96.4% | 53.3% |
| D. + agentic re-identification check (RedactAgent) | 96.2% | 95.9% | 56.7% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 92% | 92% | 92% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 94% | 94% | 94% | 100% |
| Date (event) | 102 | 100% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 100% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 83% |
| Signature | 12 | 0% | 67% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.79 s | 0.89 s | 4.82 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 10.11 s | 6.87 s | 45.36 s |
| vlm | 1.99 s | 2.01 s | 3.39 s |
| total | 15.40 s | 14.27 s | 47.45 s |
