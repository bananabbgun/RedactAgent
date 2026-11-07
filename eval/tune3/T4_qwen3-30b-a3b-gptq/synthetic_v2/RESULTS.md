# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 91.9% | 0.0% |
| B. + contextual LLM | 92.4% | 92.7% | 36.7% |
| C. + VLM | 92.9% | 93.1% | 36.7% |
| D. + agentic re-identification check (RedactAgent) | 94.7% | 89.6% | 53.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 89% | 89% | 92% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 50% | 50% | 62% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T4_qwen3-30b-a3b-gptq)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.84 s | 0.87 s | 5.00 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 8.12 s | 7.31 s | 16.08 s |
| vlm | 1.87 s | 1.94 s | 3.34 s |
| total | 22.11 s | 20.54 s | 42.29 s |
