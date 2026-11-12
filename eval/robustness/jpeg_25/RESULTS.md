# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.1% | 91.1% | 0.0% |
| B. + contextual LLM | 91.9% | 93.7% | 33.3% |
| C. + VLM | 93.7% | 94.1% | 50.0% |
| D. + agentic re-identification check (RedactAgent) | 94.9% | 91.6% | 50.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 88% | 88% | 91% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 94% | 100% | 100% | 100% |
| Date (event) | 102 | 100% | 100% | 100% | 100% |
| Phone number | 24 | 96% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 71% | 71% | 71% |
| Signature | 12 | 0% | 58% | 100% | 100% |
| Seal / chop | 12 | 83% | 83% | 100% | 100% |

## Latency per page (v2 degraded: jpeg_25)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.71 s | 0.83 s | 4.69 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 11.84 s | 8.64 s | 32.13 s |
| vlm | 2.08 s | 1.76 s | 4.50 s |
| total | 18.63 s | 15.59 s | 37.88 s |
