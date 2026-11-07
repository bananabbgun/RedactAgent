# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.7% | 0.0% |
| B. + contextual LLM | 88.1% | 90.7% | 16.7% |
| C. + VLM | 88.9% | 91.3% | 16.7% |
| D. + agentic re-identification check (RedactAgent) | 92.9% | 88.8% | 43.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 74% | 74% | 85% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 99% | 99% | 99% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 75% | 75% | 79% |
| Signature | 12 | 0% | 75% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T0_qwen3-8b-bf16)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.79 s | 0.77 s | 5.03 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 6.90 s | 7.22 s | 10.18 s |
| vlm | 1.92 s | 1.97 s | 3.02 s |
| total | 23.12 s | 19.81 s | 38.99 s |
