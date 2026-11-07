# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.7% | 0.0% |
| B. + contextual LLM | 94.7% | 95.4% | 60.0% |
| C. + VLM | 95.2% | 95.6% | 63.3% |
| D. + agentic re-identification check (RedactAgent) | 97.0% | 94.7% | 73.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 90% | 90% | 94% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 88% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b observe v0.33 r1)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.81 s | 0.98 s | 4.74 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 8.87 s | 7.78 s | 23.54 s |
| vlm | 1.90 s | 1.93 s | 3.03 s |
| total | 14.39 s | 13.36 s | 32.61 s |
