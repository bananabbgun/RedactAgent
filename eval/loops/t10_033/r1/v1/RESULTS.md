# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 94.0% | 98.7% | 47.2% |
| C. + VLM | 96.9% | 98.3% | 63.9% |
| D. + agentic re-identification check (RedactAgent) | 98.6% | 97.2% | 80.6% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 97% | 97% | 98% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 97% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 93% | 93% | 100% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 92% | 92% | 92% |
| Signature | 30 | 0% | 60% | 97% | 97% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b T=1.0 t10_033 r1)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.88 s | 1.06 s | 5.58 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 7.75 s | 6.36 s | 14.16 s |
| vlm | 2.74 s | 3.00 s | 4.06 s |
| total | 12.42 s | 12.02 s | 20.89 s |
