# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 93.4% | 0.0% |
| B. + contextual LLM | 93.7% | 95.8% | 40.0% |
| C. + VLM | 94.9% | 96.1% | 46.7% |
| D. + agentic re-identification check (RedactAgent) | 97.0% | 95.2% | 63.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 90% | 90% | 94% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 94% | 94% | 94% | 100% |
| Date (event) | 102 | 100% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 100% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 88% |
| Signature | 12 | 0% | 58% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.69 s | 0.89 s | 4.41 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 9.38 s | 7.28 s | 49.22 s |
| vlm | 1.84 s | 1.70 s | 3.36 s |
| total | 15.49 s | 14.11 s | 53.96 s |
