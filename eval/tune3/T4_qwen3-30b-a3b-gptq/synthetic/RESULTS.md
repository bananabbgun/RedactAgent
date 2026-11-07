# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 95.2% | 98.9% | 47.2% |
| C. + VLM | 97.8% | 98.7% | 66.7% |
| D. + agentic re-identification check (RedactAgent) | 98.5% | 97.4% | 77.8% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 98% | 98% | 98% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 93% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 100% | 100% | 100% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 83% | 83% | 92% |
| Signature | 30 | 0% | 70% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T4_qwen3-30b-a3b-gptq)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.85 s | 0.88 s | 5.67 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 10.07 s | 10.04 s | 13.98 s |
| vlm | 2.65 s | 2.83 s | 5.11 s |
| total | 24.99 s | 22.92 s | 47.62 s |
