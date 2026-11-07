# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 92.3% | 0.0% |
| B. + contextual LLM | 91.9% | 94.4% | 43.3% |
| C. + VLM | 92.9% | 94.7% | 46.7% |
| D. + agentic re-identification check (RedactAgent) | 95.5% | 91.5% | 60.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 85% | 85% | 92% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 83% |
| Quasi-identifier | 24 | 0% | 75% | 75% | 75% |
| Signature | 12 | 0% | 67% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, vLLM 0.33, gpt-oss-20b throughput (T=1.0) + Qwen2.5-VL-7B)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.76 s | 0.92 s | 4.52 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 7.70 s | 6.22 s | 18.90 s |
| vlm | 2.49 s | 2.31 s | 4.90 s |
| total | 13.66 s | 12.42 s | 27.34 s |
