# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 92.3% | 0.0% |
| B. + contextual LLM | 92.7% | 95.0% | 40.0% |
| C. + VLM | 93.4% | 95.3% | 43.3% |
| D. + agentic re-identification check (RedactAgent) | 94.7% | 93.9% | 50.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 86% | 86% | 89% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 99% | 99% | 99% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 100% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 83% |
| Signature | 12 | 0% | 75% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b T=0.6 t06_033 r1)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.87 s | 0.86 s | 5.14 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 7.09 s | 6.66 s | 15.46 s |
| vlm | 1.98 s | 1.95 s | 3.58 s |
| total | 12.97 s | 12.52 s | 24.75 s |
