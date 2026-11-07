# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 95.5% | 98.9% | 41.7% |
| C. + VLM | 97.3% | 98.7% | 63.9% |
| D. + agentic re-identification check (RedactAgent) | 98.5% | 98.3% | 80.6% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 91% | 91% | 95% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 100% | 100% | 100% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 100% | 100% | 100% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 75% | 75% | 92% |
| Signature | 30 | 0% | 87% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T2_qwen3-8b-fp8)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.78 s | 0.86 s | 5.67 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 5.98 s | 5.63 s | 8.26 s |
| vlm | 2.63 s | 2.74 s | 5.61 s |
| total | 16.20 s | 14.45 s | 28.43 s |
