# Model information

RedactAgent uses only openly licensed, commercially usable models and libraries. No model is fine-tuned;
behaviour comes from prompts, deterministic rules and post-processing, all in this repository.

## Models in the pipeline

| Role | Model | Licence | Where it runs (B70 deployment) | Precision | Laptop prototype |
|---|---|---|---|---|---|
| OCR (text + per-character boxes) | PP-OCR det/cls/rec via RapidOCR 1.4 | Apache-2.0 | Xeon CPU, ONNX Runtime, 8 threads/engine | FP32 | same |
| Contextual PII detection + agentic re-identification check | **gpt-oss-20b** (MoE, 21B total / 3.6B active), reasoning effort *low* | Apache-2.0 | Arc Pro B70 #0, vLLM XPU 0.33 | MXFP4 MoE weights, native XPU MXFP4 kernel; greedy decoding + loop guard | Qwen3-8B Q4 (Ollama) |
| Throughput mode | same gpt-oss-20b, sampled at temperature 1.0 (`RA_TEMPERATURE=1.0`) | Apache-2.0 | Arc Pro B70 #0 | MXFP4 | — |
| Visual identifiers (signatures, ID photos, seals) | Qwen2.5-VL-7B-Instruct | Apache-2.0 | Arc Pro B70 #1, vLLM XPU 0.33 | BF16 | Qwen2.5-VL-7B Q4 (Ollama) |
| Seal impressions (cross-check) | OpenCV colour segmentation | Apache-2.0 | Xeon CPU | — | same |

Serving: one OpenAI-compatible vLLM server per card (`ZE_AFFINITY_MASK`), JSON-schema guided decoding for the
vision model, compact line output for the text model. Launch: `deploy/b70/up.sh`.

## Text-model selection (measured on the B70, see `docs/STAGE2_LOG.md`)

Second sweep, latest code, agentic check on, 8 pages in flight, eager mode. Recall / precision in %, ablation D.
Pages/min combines both corpora.

| Candidate | Licence | Weights on the B70 | Pages / min | v1 (dev) | v2 (held-out) | failed pages |
|---|---|---|---|---|---|---|
| **gpt-oss-20b, reasoning low** | Apache-2.0 | MXFP4 (native) | 19.6 | 98.5 / 98.2 | **95.5 / 94.2** | 0 |
| Qwen3-14B | Apache-2.0 | FP8 (online) | 27.7 | 96.9 / 98.7 | 94.7 / 91.3 | 0 |
| Qwen3-8B | Apache-2.0 | FP8 (online) | 28.1 | 98.3 / 97.8 | 92.9 / 91.4 | 0 |
| Qwen3-30B-A3B | Apache-2.0 | GPTQ INT4 | 17.5 | 98.5 / 97.4 | 94.7 / 89.6 | 0 |
| Qwen3-8B BF16 (first sweep) | Apache-2.0 | BF16 | 15.7–16.8 | 98.3 / 98.2 | 92.9 / 88.8 | 0 |
| Qwen3-8B BF16 + XPU graph | Apache-2.0 | BF16 | — | graph capture out of resources | — | — |

**Decision:** gpt-oss-20b is the default ("accuracy mode"): the best held-out recall *and* precision, best or
tied in both English and Chinese, and the fewest false positives. (The sweep ran on vLLM XPU 0.26; the final
configuration runs on 0.33, see below.)

**Decoding and the throughput mode (2026-11-08).** Greedy decoding occasionally makes gpt-oss repeat its reasoning
until the token cap. Accuracy mode keeps greedy decoding (most thorough on held-out documents) and adds a
streaming loop guard; throughput mode samples the same model at temperature 1.0, which removes the loops and
raises benchmark throughput by ~65 % (34.7 vs 21.0 pages/min at 8 in flight) for ~1 recall point on v2 (95.5 vs 96.7). This replaced Qwen3-8B FP8 as the throughput mode: on this
stack it is both faster and more accurate. Measurements: `docs/STAGE2_LOG.md`.

gpt-oss always reasons before answering. With RedactAgent's original 1,024-token budget the reasoning consumed
everything and the answer came back empty; `RA_REASONING_EFFORT=low` plus a reasoning-token allowance fixes it
(`deploy/b70/up.sh` sets this automatically for gpt-oss).

## Why no AGPL detectors

Popular object detectors such as Ultralytics YOLO are AGPL-3.0. The competition requires that winning entries can
be licensed to the organisers for commercial use, so every component here is Apache-2.0, MIT or BSD.

## Data

All documents used for development and evaluation are synthetic (`scripts/make_synthetic*.py`): names, ID numbers
(with valid checksums), addresses, accounts, signatures and portraits are generated. No real personal data was used.
