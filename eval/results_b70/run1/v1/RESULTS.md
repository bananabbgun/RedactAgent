# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 94.0% | 98.9% | 47.2% |
| C. + VLM | 96.0% | 98.5% | 61.1% |
| D. + agentic re-identification check (RedactAgent) | 98.5% | 97.8% | 83.3% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 96% | 96% | 98% |
| Government ID / passport | 48 | 90% | 98% | 98% | 98% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 98% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 91% | 91% | 98% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 96% | 96% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 75% | 75% | 83% |
| Signature | 30 | 0% | 80% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, gpt-oss-20b (reasoning low) + Qwen2.5-VL-7B)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.77 s | 0.91 s | 5.26 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 15.57 s | 9.50 s | 65.03 s |
| vlm | 3.47 s | 3.26 s | 6.22 s |
| total | 21.14 s | 14.51 s | 73.13 s |
