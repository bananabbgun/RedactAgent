# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.3% | 0.0% |
| B. + contextual LLM | 94.7% | 95.1% | 56.7% |
| C. + VLM | 95.2% | 95.4% | 56.7% |
| D. + agentic re-identification check (RedactAgent) | 96.0% | 93.8% | 63.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 91% | 91% | 92% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 99% | 99% | 99% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 83% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 88% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, gpt-oss-20b (reasoning low) + Qwen2.5-VL-7B)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.91 s | 0.84 s | 5.32 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 10.34 s | 8.55 s | 32.90 s |
| vlm | 2.53 s | 2.37 s | 4.49 s |
| total | 16.89 s | 15.65 s | 37.04 s |
