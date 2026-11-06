# Model information

RedactAgent uses only openly licensed, commercially usable models and libraries. No model is fine-tuned;
behaviour comes from prompts, deterministic rules and post-processing, all in this repository.

## Models in the pipeline

| Role | Model | Licence | Where it runs (B70 deployment) | Precision | Laptop prototype |
|---|---|---|---|---|---|
| OCR (text + per-character boxes) | PP-OCR det/cls/rec via RapidOCR 1.4 | Apache-2.0 | Xeon CPU, ONNX Runtime, 8 threads/engine | FP32 | same |
| Contextual PII detection + agentic re-identification check | Qwen3 family (final: see below) | Apache-2.0 | Arc Pro B70 #0, vLLM XPU 0.26 | FP8 (online) | Qwen3-8B Q4 (Ollama) |
| Visual identifiers (signatures, ID photos, seals) | Qwen2.5-VL-7B-Instruct | Apache-2.0 | Arc Pro B70 #1, vLLM XPU 0.26 | BF16 | Qwen2.5-VL-7B Q4 (Ollama) |
| Seal impressions (cross-check) | OpenCV colour segmentation | Apache-2.0 | Xeon CPU | — | same |

Serving: one OpenAI-compatible vLLM server per card (`ZE_AFFINITY_MASK`), JSON-schema guided decoding for the
vision model, compact line output for the text model. Launch: `deploy/b70/up.sh`.

## Text-model selection (measured on the B70, see `docs/STAGE2_LOG.md`)

| Candidate | Licence | Result |
|---|---|---|
| Qwen3-8B BF16 | Apache-2.0 | baseline |
| Qwen3-8B BF16 + XPU graph | Apache-2.0 | failed at graph capture (out of resources) |
| Qwen3-8B FP8 | Apache-2.0 | +75 % throughput, same accuracy |
| Qwen3-14B FP8 | Apache-2.0 | _pending_ |
| Qwen3-30B-A3B GPTQ-Int4 | Apache-2.0 | _pending_ |
| gpt-oss-20b | Apache-2.0 | _pending_ |

## Why no AGPL detectors

Popular object detectors such as Ultralytics YOLO are AGPL-3.0. The competition requires that winning entries can
be licensed to the organisers for commercial use, so every component here is Apache-2.0, MIT or BSD.

## Data

All documents used for development and evaluation are synthetic (`scripts/make_synthetic*.py`): names, ID numbers
(with valid checksums), addresses, accounts, signatures and portraits are generated. No real personal data was used.
