# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 92.7% | 0.0% |
| B. + contextual LLM | 91.9% | 95.0% | 50.0% |
| C. + VLM | 92.4% | 95.3% | 53.3% |
| D. + agentic re-identification check (RedactAgent) | 94.4% | 94.6% | 56.7% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 81% | 81% | 87% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 88% | 88% | 88% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (gpt-oss-20b T=1.0 t10_033 r2)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.94 s | 0.93 s | 5.15 s |
| rules | 0.00 s | 0.00 s | 0.01 s |
| llm | 7.90 s | 7.25 s | 17.33 s |
| vlm | 2.09 s | 2.11 s | 3.93 s |
| total | 13.15 s | 12.44 s | 24.64 s |
