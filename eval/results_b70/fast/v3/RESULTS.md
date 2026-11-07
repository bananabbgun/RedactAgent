# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 58.8% | 93.0% | 0.0% |
| B. + contextual LLM | 92.4% | 95.5% | 43.3% |
| C. + VLM | 93.7% | 95.8% | 43.3% |
| D. + agentic re-identification check (RedactAgent) | 96.0% | 94.5% | 50.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 31% | 87% | 87% | 92% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 94% | 94% | 94% | 100% |
| Date (event) | 102 | 100% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 79% | 79% | 83% |
| Signature | 12 | 0% | 58% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, vLLM 0.33, gpt-oss-20b throughput (T=1.0) + Qwen2.5-VL-7B)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.70 s | 0.87 s | 4.70 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 7.09 s | 7.10 s | 17.82 s |
| vlm | 2.55 s | 2.57 s | 4.54 s |
| total | 13.43 s | 12.58 s | 25.89 s |
