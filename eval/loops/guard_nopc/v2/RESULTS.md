# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 92.7% | 0.0% |
| B. + contextual LLM | 94.2% | 95.4% | 53.3% |
| C. + VLM | 94.7% | 95.6% | 56.7% |
| D. + agentic re-identification check (RedactAgent) | 95.5% | 94.3% | 60.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 89% | 89% | 91% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 83% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 83% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, gpt-oss-20b (reasoning low) + Qwen2.5-VL-7B, loop guard, --no-enable-prefix-caching)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.81 s | 0.92 s | 4.75 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 13.64 s | 9.40 s | 38.45 s |
| vlm | 1.89 s | 1.84 s | 3.22 s |
| total | 20.61 s | 18.61 s | 49.93 s |
