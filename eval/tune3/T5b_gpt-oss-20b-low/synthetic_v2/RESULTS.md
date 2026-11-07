# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.7% | 0.0% |
| B. + contextual LLM | 91.9% | 95.2% | 50.0% |
| C. + VLM | 92.4% | 95.5% | 50.0% |
| D. + agentic re-identification check (RedactAgent) | 95.5% | 94.2% | 60.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 83% | 83% | 90% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 92% | 92% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 88% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T5b_gpt-oss-20b-low)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.85 s | 0.87 s | 5.04 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 11.45 s | 10.00 s | 59.35 s |
| vlm | 1.97 s | 1.96 s | 3.20 s |
| total | 17.65 s | 14.43 s | 67.03 s |
