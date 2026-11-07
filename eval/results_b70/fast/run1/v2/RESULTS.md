# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.3% | 0.0% |
| B. + contextual LLM | 92.4% | 94.7% | 40.0% |
| C. + VLM | 93.4% | 95.0% | 46.7% |
| D. + agentic re-identification check (RedactAgent) | 94.2% | 94.6% | 46.7% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 87% | 87% | 88% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 100% |
| Quasi-identifier | 24 | 0% | 75% | 75% | 79% |
| Signature | 12 | 0% | 67% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, vLLM 0.33, gpt-oss-20b throughput (T=1.0) + Qwen2.5-VL-7B)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.79 s | 0.86 s | 5.01 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 7.96 s | 6.86 s | 20.42 s |
| vlm | 2.41 s | 2.84 s | 4.20 s |
| total | 13.23 s | 11.55 s | 29.86 s |
