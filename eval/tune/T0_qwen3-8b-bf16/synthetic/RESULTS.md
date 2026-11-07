# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 95.9% | 98.8% | 44.4% |
| C. + VLM | 97.8% | 98.7% | 69.4% |
| D. + agentic re-identification check (RedactAgent) | 98.3% | 98.2% | 77.8% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 93% | 93% | 95% |
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
| Quasi-identifier | 12 | 0% | 83% | 83% | 83% |
| Signature | 30 | 0% | 83% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T0_qwen3-8b-bf16)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.60 s | 0.87 s | 4.68 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 9.43 s | 8.96 s | 12.94 s |
| vlm | 2.55 s | 2.70 s | 5.29 s |
| total | 26.11 s | 24.70 s | 43.71 s |
