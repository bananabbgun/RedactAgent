# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 91.5% | 0.0% |
| B. + contextual LLM | 93.7% | 91.5% | 40.0% |
| C. + VLM | 93.7% | 92.0% | 40.0% |
| D. + agentic re-identification check (RedactAgent) | 96.0% | 89.0% | 60.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 90% | 90% | 95% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 54% | 54% | 62% |
| Signature | 12 | 0% | 100% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T4_qwen3-30b-a3b-gptq)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.62 s | 0.81 s | 4.38 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 7.84 s | 7.41 s | 11.96 s |
| vlm | 1.99 s | 2.05 s | 3.36 s |
| total | 21.06 s | 20.58 s | 38.85 s |
