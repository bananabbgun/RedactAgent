# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 54.0% | 91.5% | 0.0% |
| B. + contextual LLM | 91.7% | 93.9% | 26.7% |
| C. + VLM | 95.5% | 93.9% | 63.3% |
| D. + agentic re-identification check (RedactAgent) | 96.7% | 92.6% | 70.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 93% | 93% | 95% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 89% | 100% | 100% | 100% |
| Date (event) | 102 | 95% | 95% | 95% | 97% |
| Phone number | 24 | 88% | 96% | 96% | 96% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 96% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 96% | 96% | 96% |
| Signature | 12 | 0% | 67% | 100% | 100% |
| Seal / chop | 12 | 0% | 0% | 92% | 92% |

## Latency per page (v2 degraded: fax_2)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.65 s | 0.76 s | 4.59 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 9.75 s | 7.53 s | 31.65 s |
| vlm | 2.34 s | 2.51 s | 4.50 s |
| total | 15.74 s | 13.77 s | 38.87 s |
