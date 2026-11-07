# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.7% | 0.0% |
| B. + contextual LLM | 94.4% | 95.3% | 53.3% |
| C. + VLM | 94.9% | 95.6% | 53.3% |
| D. + agentic re-identification check (RedactAgent) | 96.7% | 94.0% | 66.7% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 90% | 90% | 93% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 99% | 99% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 100% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 88% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b observe r1)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.88 s | 0.90 s | 5.12 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 12.37 s | 9.41 s | 42.67 s |
| vlm | 1.87 s | 1.81 s | 3.00 s |
| total | 18.49 s | 16.25 s | 49.04 s |
