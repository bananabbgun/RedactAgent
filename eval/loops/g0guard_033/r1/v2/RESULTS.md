# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.3% | 0.0% |
| B. + contextual LLM | 94.2% | 95.1% | 56.7% |
| C. + VLM | 94.7% | 95.3% | 60.0% |
| D. + agentic re-identification check (RedactAgent) | 96.7% | 92.5% | 70.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 88% | 88% | 94% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 83% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b T=0 g0guard_033 r1)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.86 s | 0.95 s | 4.82 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 9.68 s | 7.14 s | 48.60 s |
| vlm | 1.98 s | 2.12 s | 3.11 s |
| total | 16.04 s | 14.06 s | 57.37 s |
