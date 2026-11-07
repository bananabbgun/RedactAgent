# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.7% | 0.0% |
| B. + contextual LLM | 87.4% | 93.5% | 23.3% |
| C. + VLM | 88.4% | 93.9% | 23.3% |
| D. + agentic re-identification check (RedactAgent) | 92.9% | 91.4% | 40.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 73% | 73% | 85% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 99% | 99% | 99% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 75% | 75% | 75% |
| Signature | 12 | 0% | 67% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T2_qwen3-8b-fp8)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.70 s | 0.93 s | 4.28 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 4.14 s | 3.60 s | 6.46 s |
| vlm | 2.01 s | 2.20 s | 3.38 s |
| total | 14.88 s | 13.04 s | 24.99 s |
