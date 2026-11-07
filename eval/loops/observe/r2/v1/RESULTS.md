# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 95.0% | 98.7% | 50.0% |
| C. + VLM | 97.3% | 98.2% | 69.4% |
| D. + agentic re-identification check (RedactAgent) | 99.0% | 97.6% | 86.1% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 98% | 98% | 99% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 98% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 93% | 93% | 98% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 92% | 92% | 92% |
| Signature | 30 | 0% | 77% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b observe r2)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.84 s | 0.92 s | 5.88 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 12.69 s | 8.75 s | 40.18 s |
| vlm | 2.73 s | 2.88 s | 4.10 s |
| total | 17.62 s | 13.49 s | 47.98 s |
