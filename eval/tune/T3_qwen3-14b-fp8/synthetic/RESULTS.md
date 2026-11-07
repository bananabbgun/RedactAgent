# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 96.9% | 98.8% | 55.6% |
| C. + VLM | 98.1% | 98.4% | 72.2% |
| D. + agentic re-identification check (RedactAgent) | 98.1% | 98.4% | 72.2% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 97% | 97% | 97% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 100% | 100% | 100% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 93% | 93% | 93% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 92% | 92% | 92% |
| Signature | 30 | 0% | 97% | 100% | 100% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T3_qwen3-14b-fp8)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.83 s | 0.92 s | 5.48 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 10.42 s | 10.00 s | 14.16 s |
| vlm | 2.56 s | 2.85 s | 4.05 s |
| total | 15.48 s | 12.91 s | 32.45 s |
