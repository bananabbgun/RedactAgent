# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 94.0% | 98.9% | 47.2% |
| C. + VLM | 96.7% | 98.3% | 66.7% |
| D. + agentic re-identification check (RedactAgent) | 98.3% | 98.1% | 77.8% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 96% | 96% | 98% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 98% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 91% | 91% | 93% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 92% | 92% | 92% |
| Signature | 30 | 0% | 67% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, gpt-oss-20b (reasoning low) + Qwen2.5-VL-7B, loop guard, --no-enable-prefix-caching)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.85 s | 0.96 s | 5.61 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 14.38 s | 10.63 s | 42.61 s |
| vlm | 2.73 s | 2.92 s | 4.03 s |
| total | 20.10 s | 16.67 s | 50.01 s |
