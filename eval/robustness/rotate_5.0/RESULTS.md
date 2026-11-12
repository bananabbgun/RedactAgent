# Evaluation results

Synthetic corpus: 30 scanned pages, 396 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 58.8% | 89.8% | 0.0% |
| B. + contextual LLM | 95.5% | 92.1% | 46.7% |
| C. + VLM | 96.2% | 92.5% | 56.7% |
| D. + agentic re-identification check (RedactAgent) | 97.0% | 91.7% | 66.7% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 144 | 32% | 93% | 93% | 95% |
| Government ID / passport | 6 | 83% | 100% | 100% | 100% |
| Date of birth | 18 | 89% | 94% | 94% | 94% |
| Date (event) | 102 | 100% | 100% | 100% | 100% |
| Phone number | 24 | 100% | 100% | 100% | 100% |
| Address | 24 | 0% | 100% | 100% | 100% |
| Medical record no. | 24 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 6 | 83% | 100% | 100% | 100% |
| Quasi-identifier | 24 | 0% | 88% | 88% | 88% |
| Signature | 12 | 0% | 75% | 92% | 92% |
| Seal / chop | 12 | 92% | 92% | 100% | 100% |

## Latency per page (Apple M5 laptop, 24 GB, Ollama)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.63 s | 0.85 s | 4.41 s |
| rules | 0.00 s | 0.00 s | 0.01 s |
| llm | 13.63 s | 11.14 s | 27.30 s |
| vlm | 2.11 s | 1.80 s | 4.03 s |
| total | 19.31 s | 16.88 s | 35.69 s |
