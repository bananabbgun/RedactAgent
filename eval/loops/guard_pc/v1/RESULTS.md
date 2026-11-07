# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 94.3% | 98.9% | 47.2% |
| C. + VLM | 96.6% | 98.5% | 63.9% |
| D. + agentic re-identification check (RedactAgent) | 98.6% | 97.9% | 83.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 96% | 96% | 98% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 100% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 93% | 93% | 96% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 96% | 96% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 83% | 83% | 83% |
| Signature | 30 | 0% | 77% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, gpt-oss-20b (reasoning low) + Qwen2.5-VL-7B, loop guard, --enable-prefix-caching)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.78 s | 1.06 s | 5.06 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 15.00 s | 9.81 s | 137.68 s |
| vlm | 2.73 s | 2.81 s | 4.04 s |
| total | 19.91 s | 15.36 s | 144.91 s |
