# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.3% | 0.0% |
| B. + contextual LLM | 93.9% | 95.0% | 53.3% |
| C. + VLM | 94.4% | 95.3% | 53.3% |
| D. + agentic re-identification check (RedactAgent) | 97.0% | 93.1% | 73.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 88% | 88% | 94% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 99% | 99% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 88% | 88% | 88% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b T=0 g0guard_033 r2)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.70 s | 0.94 s | 4.37 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 10.61 s | 7.70 s | 48.96 s |
| vlm | 1.95 s | 2.13 s | 3.31 s |
| total | 16.27 s | 12.63 s | 54.63 s |
