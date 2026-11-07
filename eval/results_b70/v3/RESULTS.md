# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 93.9% | 0.0% |
| B. + contextual LLM | 92.9% | 96.0% | 50.0% |
| C. + VLM | 93.7% | 95.5% | 56.7% |
| D. + agentic re-identification check (RedactAgent) | 96.2% | 95.0% | 63.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 88% | 88% | 91% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 94% | 94% | 94% | 100% |
| Date (event) | 102 | 100% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 92% | 92% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 92% |
| Signature | 12 | 0% | 75% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, gpt-oss-20b (reasoning low) + Qwen2.5-VL-7B)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.65 s | 0.79 s | 4.53 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 16.41 s | 7.34 s | 117.19 s |
| vlm | 1.95 s | 1.76 s | 4.49 s |
| total | 22.75 s | 15.00 s | 125.07 s |
