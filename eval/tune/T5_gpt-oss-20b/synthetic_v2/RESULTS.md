# Evaluation results

Synthetic corpus: 0 scanned pages, 0 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 0.0% | 0.0% | 0.0% |
| B. + contextual LLM | 0.0% | 0.0% | 0.0% |
| C. + VLM | 0.0% | 0.0% | 0.0% |
| D. + agentic re-identification check (RedactAgent) | 0.0% | 0.0% | 0.0% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|

## Latency per page (2x Arc Pro B70, T5_gpt-oss-20b)

| Stage | mean | p50 | max |
|---|---|---|---|
