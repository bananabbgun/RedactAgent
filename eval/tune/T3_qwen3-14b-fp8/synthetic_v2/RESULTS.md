# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.7% | 0.0% |
| B. + contextual LLM | 94.2% | 93.4% | 50.0% |
| C. + VLM | 94.2% | 93.8% | 50.0% |
| D. + agentic re-identification check (RedactAgent) | 96.2% | 90.6% | 66.7% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 88% | 88% | 93% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 79% | 79% | 79% |
| Signature | 12 | 0% | 100% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T3_qwen3-14b-fp8)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.72 s | 0.84 s | 4.69 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 7.31 s | 6.80 s | 14.59 s |
| vlm | 1.94 s | 2.00 s | 3.29 s |
| total | 19.51 s | 18.13 s | 42.27 s |
