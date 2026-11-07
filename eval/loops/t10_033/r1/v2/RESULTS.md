# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.7% | 0.0% |
| B. + contextual LLM | 91.2% | 95.2% | 36.7% |
| C. + VLM | 92.4% | 95.5% | 43.3% |
| D. + agentic re-identification check (RedactAgent) | 95.2% | 93.9% | 56.7% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 83% | 83% | 91% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 99% | 99% | 99% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 83% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 83% |
| Signature | 12 | 0% | 58% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b T=1.0 t10_033 r1)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.75 s | 0.94 s | 4.79 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 7.08 s | 5.64 s | 18.95 s |
| vlm | 1.90 s | 1.90 s | 3.34 s |
| total | 13.09 s | 11.83 s | 28.67 s |
