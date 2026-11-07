# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 95.2% | 98.9% | 47.2% |
| C. + VLM | 97.3% | 98.5% | 66.7% |
| D. + agentic re-identification check (RedactAgent) | 99.1% | 97.8% | 86.1% |

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
| Quasi-identifier | 12 | 0% | 92% | 92% | 100% |
| Signature | 30 | 0% | 80% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b observe r1)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 2.04 s | 0.99 s | 6.33 s |
| rules | 0.00 s | 0.00 s | 0.01 s |
| llm | 15.94 s | 10.42 s | 55.54 s |
| vlm | 2.68 s | 2.79 s | 4.12 s |
| total | 21.42 s | 17.42 s | 61.93 s |
