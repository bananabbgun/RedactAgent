# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 95.7% | 98.9% | 47.2% |
| C. + VLM | 97.3% | 98.4% | 63.9% |
| D. + agentic re-identification check (RedactAgent) | 98.8% | 97.4% | 80.6% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 98% | 98% | 99% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 97% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 94% | 94% | 98% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 92% | 92% | 100% |
| Signature | 30 | 0% | 87% | 97% | 97% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b T=0 g0guard_033 r1)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.69 s | 0.97 s | 4.85 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 14.79 s | 9.33 s | 66.91 s |
| vlm | 2.69 s | 2.82 s | 4.15 s |
| total | 19.98 s | 13.70 s | 73.81 s |
