# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 91.9% | 0.0% |
| B. + contextual LLM | 94.7% | 94.9% | 53.3% |
| C. + VLM | 95.2% | 95.1% | 56.7% |
| D. + agentic re-identification check (RedactAgent) | 96.2% | 93.8% | 63.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 90% | 90% | 92% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 100% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 88% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, gpt-oss-20b (reasoning low) + Qwen2.5-VL-7B)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.60 s | 0.85 s | 4.28 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 13.67 s | 9.16 s | 41.91 s |
| vlm | 1.89 s | 1.86 s | 3.19 s |
| total | 20.10 s | 15.74 s | 46.98 s |
