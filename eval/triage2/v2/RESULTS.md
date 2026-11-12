# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.3% | 92.7% | 0.0% |
| B. + contextual LLM | 92.7% | 95.3% | 43.3% |
| C. + VLM | 93.2% | 95.5% | 46.7% |
| D. + agentic re-identification check (RedactAgent) | 96.5% | 92.2% | 66.7% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 85% | 85% | 94% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 79% | 79% | 79% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (two agentic rounds)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.58 s | 0.85 s | 4.13 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 12.43 s | 7.57 s | 48.79 s |
| vlm | 2.21 s | 1.81 s | 4.76 s |
| total | 22.57 s | 16.74 s | 53.53 s |
