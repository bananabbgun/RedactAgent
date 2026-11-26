# Evaluation results

Synthetic corpus: 22 scanned pages, 287 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 32.1% | 67.4% | 0.0% |
| B. + contextual LLM | 63.4% | 74.6% | 4.5% |
| C. + VLM | 65.5% | 74.3% | 4.5% |
| D. + agentic re-identification check (RedactAgent) | 73.9% | 70.9% | 18.2% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 72 | 4% | 69% | 71% | 85% |
| Government ID / passport | 18 | 78% | 78% | 78% | 78% |
| Date of birth | 22 | 77% | 82% | 82% | 82% |
| Date (event) | 80 | 35% | 42% | 42% | 51% |
| Phone number | 22 | 64% | 91% | 91% | 100% |
| E-mail | 4 | 100% | 100% | 100% | 100% |
| Address | 34 | 0% | 53% | 53% | 65% |
| Medical record no. | 4 | 0% | 25% | 25% | 50% |
| Health insurance no. | 4 | 0% | 50% | 50% | 50% |
| Quasi-identifier | 3 | 0% | 100% | 100% | 100% |
| Signature | 8 | 0% | 75% | 88% | 88% |
| Face photo | 4 | 0% | 0% | 100% | 100% |
| Seal / chop | 12 | 100% | 100% | 100% | 100% |

## Latency per page (2x Intel Arc Pro B70 (final configuration))

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 2.87 s | 2.94 s | 3.83 s |
| rules | 0.01 s | 0.00 s | 0.01 s |
| llm | 19.04 s | 18.25 s | 57.59 s |
| vlm | 2.53 s | 2.75 s | 5.02 s |
| total | 38.79 s | 29.95 s | 131.18 s |
