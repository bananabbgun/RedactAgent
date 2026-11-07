# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.7% | 0.0% |
| B. + contextual LLM | 89.9% | 95.1% | 46.7% |
| C. + VLM | 90.7% | 95.4% | 50.0% |
| D. + agentic re-identification check (RedactAgent) | 93.4% | 94.8% | 53.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 82% | 82% | 87% |
| Government ID / passport | 6 | 83% | 83% | 83% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 99% | 99% | 99% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 83% | 83% | 92% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 79% | 79% | 83% |
| Signature | 12 | 0% | 75% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b observe r2)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.72 s | 0.86 s | 4.61 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 32.30 s | 8.29 s | 174.80 s |
| vlm | 1.85 s | 1.84 s | 3.02 s |
| total | 61.57 s | 17.54 s | 316.35 s |
