# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 92.7% | 0.0% |
| B. + contextual LLM | 88.1% | 92.3% | 20.0% |
| C. + VLM | 88.9% | 92.7% | 20.0% |
| D. + agentic re-identification check (RedactAgent) | 94.4% | 90.2% | 46.7% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 74% | 74% | 88% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 99% | 99% | 99% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 75% | 75% | 83% |
| Signature | 12 | 0% | 75% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T2_qwen3-8b-fp8)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.71 s | 0.84 s | 4.80 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 4.47 s | 4.42 s | 6.54 s |
| vlm | 1.88 s | 1.98 s | 3.05 s |
| total | 13.85 s | 12.17 s | 26.11 s |
