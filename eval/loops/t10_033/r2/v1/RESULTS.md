# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 94.2% | 98.7% | 41.7% |
| C. + VLM | 97.1% | 98.2% | 61.1% |
| D. + agentic re-identification check (RedactAgent) | 98.3% | 97.7% | 75.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 96% | 96% | 98% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 97% | 97% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 95% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 94% | 94% | 94% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 100% | 100% | 100% |
| Signature | 30 | 0% | 63% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b T=1.0 t10_033 r2)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.83 s | 0.99 s | 5.45 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 7.49 s | 5.68 s | 15.44 s |
| vlm | 2.86 s | 2.99 s | 4.07 s |
| total | 12.54 s | 11.69 s | 25.34 s |
