# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 95.4% | 98.8% | 50.0% |
| C. + VLM | 96.7% | 98.7% | 66.7% |
| D. + agentic re-identification check (RedactAgent) | 96.9% | 98.7% | 66.7% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 97% | 97% | 97% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 92% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 89% | 89% | 89% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 92% | 92% | 92% |
| Signature | 30 | 0% | 93% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T3_qwen3-14b-fp8)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.72 s | 0.88 s | 5.00 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 9.79 s | 9.27 s | 14.20 s |
| vlm | 2.65 s | 2.80 s | 5.44 s |
| total | 14.96 s | 11.83 s | 33.32 s |
