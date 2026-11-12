# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 94.7% | 98.9% | 47.2% |
| C. + VLM | 97.4% | 98.2% | 66.7% |
| D. + agentic re-identification check (RedactAgent) | 99.5% | 97.4% | 91.7% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 98% | 98% | 99% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 100% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 94% | 94% | 100% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 96% | 96% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 100% | 100% | 100% |
| Signature | 30 | 0% | 67% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (triage signals, accuracy mode)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.93 s | 0.94 s | 6.03 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 17.19 s | 12.93 s | 62.52 s |
| vlm | 2.55 s | 2.73 s | 3.67 s |
| total | 23.52 s | 18.27 s | 69.23 s |
