# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 93.9% | 0.0% |
| B. + contextual LLM | 94.2% | 96.1% | 40.0% |
| C. + VLM | 95.2% | 96.3% | 50.0% |
| D. + agentic re-identification check (RedactAgent) | 96.5% | 94.8% | 60.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 90% | 90% | 93% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 94% | 94% | 94% | 94% |
| Date (event) | 102 | 100% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 100% |
| Quasi-identifier | 24 | 0% | 88% | 88% | 88% |
| Signature | 12 | 0% | 67% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.81 s | 0.86 s | 5.00 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 9.46 s | 8.02 s | 26.66 s |
| vlm | 1.87 s | 1.78 s | 3.40 s |
| total | 15.25 s | 13.69 s | 29.07 s |
