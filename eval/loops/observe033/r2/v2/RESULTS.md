# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.7% | 0.0% |
| B. + contextual LLM | 94.4% | 95.1% | 60.0% |
| C. + VLM | 94.9% | 95.4% | 63.3% |
| D. + agentic re-identification check (RedactAgent) | 97.2% | 93.0% | 73.3% |

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
| Quasi-identifier | 24 | 0% | 88% | 88% | 88% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b observe v0.33 r2)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.70 s | 0.94 s | 4.41 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 9.27 s | 8.21 s | 26.07 s |
| vlm | 1.90 s | 1.94 s | 3.32 s |
| total | 15.52 s | 14.25 s | 34.29 s |
