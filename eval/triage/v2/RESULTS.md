# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 59.6% | 92.7% | 0.0% |
| B. + contextual LLM | 92.9% | 95.3% | 50.0% |
| C. + VLM | 93.4% | 95.5% | 50.0% |
| D. + agentic re-identification check (RedactAgent) | 96.5% | 93.0% | 66.7% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 33% | 85% | 85% | 93% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 99% | 99% | 99% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 83% | 83% | 83% |
| Signature | 12 | 0% | 83% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (triage signals, accuracy mode)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.81 s | 0.90 s | 4.86 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 10.12 s | 7.66 s | 42.37 s |
| vlm | 2.32 s | 2.67 s | 3.84 s |
| total | 16.34 s | 12.31 s | 52.94 s |
