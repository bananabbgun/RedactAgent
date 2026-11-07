# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 96.2% | 98.8% | 55.6% |
| C. + VLM | 98.5% | 98.5% | 80.6% |
| D. + agentic re-identification check (RedactAgent) | 98.8% | 97.3% | 86.1% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 98% | 98% | 98% |
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
| Quasi-identifier | 12 | 0% | 67% | 67% | 75% |
| Signature | 30 | 0% | 77% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T4_qwen3-30b-a3b-gptq)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.73 s | 0.88 s | 5.22 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 9.81 s | 9.89 s | 13.49 s |
| vlm | 2.58 s | 2.75 s | 4.04 s |
| total | 22.98 s | 20.69 s | 38.15 s |
