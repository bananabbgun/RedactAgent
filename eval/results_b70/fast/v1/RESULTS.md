# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 93.8% | 98.4% | 41.7% |
| C. + VLM | 96.6% | 98.0% | 61.1% |
| D. + agentic re-identification check (RedactAgent) | 97.4% | 97.4% | 69.4% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 98% | 98% | 98% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 97% | 97% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 93% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 91% | 91% | 91% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 83% | 83% | 92% |
| Signature | 30 | 0% | 63% | 97% | 97% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, vLLM 0.33, gpt-oss-20b throughput (T=1.0) + Qwen2.5-VL-7B)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.72 s | 0.96 s | 4.90 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 6.78 s | 6.41 s | 12.85 s |
| vlm | 2.57 s | 2.86 s | 3.78 s |
| total | 11.07 s | 10.28 s | 19.96 s |
