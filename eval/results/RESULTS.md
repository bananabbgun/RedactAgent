# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 76.5% | 97.4% | 0.0% |
| B. + contextual LLM | 96.4% | 96.9% | 52.8% |
| C. + VLM (RedactAgent) | 97.8% | 97.1% | 72.2% |

## Recall by category

| Category | n | A | B | C |
|---|---|---|---|---|
| Person name | 126 | 60% | 94% | 94% |
| Government ID / passport | 48 | 90% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% |
| Phone number | 60 | 90% | 100% | 100% |
| E-mail | 24 | 100% | 100% | 100% |
| Address | 54 | 67% | 100% | 100% |
| Medical record no. | 12 | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 75% | 75% |
| Signature | 30 | 0% | 93% | 100% |
| Face photo | 6 | 0% | 0% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% |

## Latency per page (Apple M5 laptop, 24 GB, Ollama)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.28 s | 1.25 s | 1.63 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 18.57 s | 17.61 s | 25.11 s |
| vlm | 10.01 s | 10.24 s | 14.77 s |
| total | 29.87 s | 30.13 s | 35.60 s |
