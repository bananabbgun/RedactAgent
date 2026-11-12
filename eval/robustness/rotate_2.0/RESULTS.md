# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 58.8% | 92.6% | 0.0% |
| B. + contextual LLM | 94.2% | 94.5% | 56.7% |
| C. + VLM | 95.2% | 94.3% | 66.7% |
| D. + agentic re-identification check (RedactAgent) | 96.2% | 93.0% | 70.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 31% | 91% | 91% | 93% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 100% | 100% | 100% | 100% |
| Date (event) | 102 | 100% | 100% | 100% | 100% |
| Phone number | 24 | 92% | 96% | 96% | 96% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 83% | 83% | 100% |
| Quasi-identifier | 24 | 0% | 88% | 88% | 88% |
| Signature | 12 | 0% | 58% | 92% | 92% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (Apple M5 laptop, 24 GB, Ollama)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.65 s | 0.79 s | 4.51 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 9.96 s | 8.06 s | 31.73 s |
| vlm | 2.45 s | 1.96 s | 4.84 s |
| total | 16.26 s | 15.26 s | 37.63 s |
