# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 54.8% | 91.3% | 0.0% |
| B. + contextual LLM | 91.4% | 94.4% | 33.3% |
| C. + VLM | 95.2% | 93.7% | 60.0% |
| D. + agentic re-identification check (RedactAgent) | 96.7% | 92.5% | 70.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 35% | 94% | 94% | 97% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 83% | 100% | 100% | 100% |
| Date (event) | 102 | 95% | 96% | 96% | 97% |
| Phone number | 24 | 92% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 96% | 96% | 96% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 88% | 88% | 88% |
| Signature | 12 | 0% | 58% | 92% | 92% |
| Seal / chop | 12 | 0% | 0% | 92% | 92% |

## Latency per page (v2 degraded: fax_1)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.63 s | 0.84 s | 4.36 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 11.42 s | 8.42 s | 40.94 s |
| vlm | 2.31 s | 2.51 s | 5.12 s |
| total | 17.34 s | 14.97 s | 47.74 s |
