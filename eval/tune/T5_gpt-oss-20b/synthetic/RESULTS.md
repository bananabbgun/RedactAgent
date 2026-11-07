# Evaluation results

Synthetic corpus: 2 scanned pages, 22 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 72.7% | 100.0% | 0.0% |
| B. + contextual LLM | 100.0% | 100.0% | 100.0% |
| C. + VLM | 100.0% | 100.0% | 100.0% |
| D. + agentic re-identification check (RedactAgent) | 100.0% | 100.0% | 100.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 2 | 0% | 100% | 100% | 100% |
| Government ID / passport | 2 | 100% | 100% | 100% | 100% |
| Date of birth | 2 | 100% | 100% | 100% | 100% |
| Date (event) | 4 | 100% | 100% | 100% | 100% |
| Phone number | 2 | 100% | 100% | 100% | 100% |
| E-mail | 2 | 100% | 100% | 100% | 100% |
| Address | 2 | 0% | 100% | 100% | 100% |
| Bank / card / policy no. | 4 | 100% | 100% | 100% | 100% |
| Signature | 2 | 0% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, T5_gpt-oss-20b)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.07 s | 1.07 s | 1.41 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 20.81 s | 20.81 s | 24.32 s |
| vlm | 2.68 s | 2.68 s | 3.63 s |
| total | 34.98 s | 34.98 s | 38.51 s |
