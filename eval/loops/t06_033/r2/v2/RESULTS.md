# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.3% | 0.0% |
| B. + contextual LLM | 93.4% | 95.0% | 43.3% |
| C. + VLM | 93.9% | 95.3% | 43.3% |
| D. + agentic re-identification check (RedactAgent) | 94.9% | 93.5% | 53.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 88% | 88% | 90% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 99% | 99% | 99% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 83% |
| Quasi-identifier | 24 | 0% | 79% | 79% | 83% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b T=0.6 t06_033 r2)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.93 s | 0.95 s | 5.13 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 8.23 s | 6.93 s | 27.83 s |
| vlm | 1.91 s | 1.80 s | 3.33 s |
| total | 14.12 s | 13.16 s | 31.04 s |
