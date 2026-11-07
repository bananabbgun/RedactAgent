# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.4% | 0.0% |
| B. + contextual LLM | 94.8% | 98.4% | 52.8% |
| C. + VLM | 97.3% | 98.2% | 69.4% |
| D. + agentic re-identification check (RedactAgent) | 98.5% | 97.6% | 77.8% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 98% | 98% | 98% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 98% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 93% | 93% | 94% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 92% | 92% | 92% |
| Signature | 30 | 0% | 73% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b T=0.6 t06_033 r1)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.73 s | 0.97 s | 5.13 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 9.01 s | 7.34 s | 33.81 s |
| vlm | 2.69 s | 2.86 s | 5.12 s |
| total | 13.58 s | 11.77 s | 36.60 s |
