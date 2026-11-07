# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 95.0% | 98.8% | 50.0% |
| C. + VLM | 96.7% | 98.2% | 66.7% |
| D. + agentic re-identification check (RedactAgent) | 98.5% | 97.6% | 77.8% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 96% | 96% | 98% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 98% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 91% | 91% | 94% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 92% | 92% | 92% |
| Signature | 30 | 0% | 87% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b T=0.6 t06_033 r2)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.91 s | 1.00 s | 5.64 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 6.82 s | 6.67 s | 13.36 s |
| vlm | 2.76 s | 2.91 s | 4.02 s |
| total | 11.78 s | 10.97 s | 18.52 s |
