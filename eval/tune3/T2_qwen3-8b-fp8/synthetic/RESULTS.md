# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 94.7% | 98.9% | 38.9% |
| C. + VLM | 96.6% | 98.8% | 61.1% |
| D. + agentic re-identification check (RedactAgent) | 98.3% | 97.8% | 77.8% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 93% | 93% | 97% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 95% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 100% | 100% | 100% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 75% | 75% | 92% |
| Signature | 30 | 0% | 83% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T2_qwen3-8b-fp8)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.74 s | 0.96 s | 5.01 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 5.93 s | 6.05 s | 7.72 s |
| vlm | 2.65 s | 2.79 s | 5.49 s |
| total | 16.18 s | 14.72 s | 28.56 s |
