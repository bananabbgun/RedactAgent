# Evaluation results

Synthetic corpus: 36 scanned pages, 582 ground-truth PII items (6 templates, English + Traditional Chinese). Policy: strict.

| Configuration | Recall | Precision | Clean pages |
|---|---|---|---|
| A. Rules + colour (regex/DLP baseline) | 75.4% | 98.6% | 0.0% |
| B. + contextual LLM | 95.5% | 98.9% | 47.2% |
| C. + VLM | 97.3% | 98.5% | 63.9% |
| D. + agentic re-identification check (RedactAgent) | 98.5% | 98.4% | 80.6% |

## Recall by category

| Category | n | A | B | C | D |
|---|---|---|---|---|---|
| Person name | 126 | 60% | 98% | 98% | 98% |
| Government ID / passport | 48 | 90% | 100% | 100% | 100% |
| Date of birth | 36 | 100% | 100% | 100% | 100% |
| Date (event) | 96 | 97% | 98% | 98% | 98% |
| Phone number | 60 | 80% | 90% | 90% | 97% |
| E-mail | 24 | 100% | 100% | 100% | 100% |
| Address | 54 | 67% | 96% | 96% | 98% |
| Medical record no. | 12 | 100% | 100% | 100% | 100% |
| Health insurance no. | 6 | 100% | 100% | 100% | 100% |
| Bank / card / policy no. | 24 | 75% | 100% | 100% | 100% |
| Licence plate | 24 | 100% | 100% | 100% | 100% |
| Quasi-identifier | 12 | 0% | 83% | 83% | 92% |
| Signature | 30 | 0% | 83% | 97% | 97% |
| Face photo | 6 | 0% | 0% | 100% | 100% |
| Seal / chop | 24 | 100% | 100% | 100% | 100% |

## Latency per page (2x Arc Pro B70, vLLM 0.33, gpt-oss-20b accuracy (greedy + loop guard) + Qwen2.5-VL-7B)

| Stage | mean | p50 | max |
|---|---|---|---|
| ocr | 1.64 s | 0.88 s | 4.85 s |
| rules | 0.00 s | 0.00 s | 0.00 s |
| llm | 13.43 s | 9.35 s | 53.28 s |
| vlm | 3.43 s | 3.11 s | 7.22 s |
| total | 18.22 s | 13.86 s | 61.24 s |
