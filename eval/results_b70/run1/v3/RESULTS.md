# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 93.9% | 0.0% |
| B. + contextual LLM | 94.9% | 96.1% | 40.0% |
| C. + VLM | 95.7% | 95.4% | 46.7% |
| D. + agentic re-identification check (RedactAgent) | 96.7% | 94.8% | 60.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 92% | 92% | 93% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 94% | 94% | 94% | 94% |
| Date (event) | 102 | 100% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 100% |
| Quasi-identifier | 24 | 0% | 88% | 88% | 92% |
| Signature | 12 | 0% | 75% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, gpt-oss-20b (reasoning low) + Qwen2.5-VL-7B)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.68 s | 0.83 s | 4.50 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 10.22 s | 7.17 s | 36.51 s |
| vlm | 2.85 s | 2.39 s | 6.65 s |
| total | 16.22 s | 13.69 s | 39.90 s |
