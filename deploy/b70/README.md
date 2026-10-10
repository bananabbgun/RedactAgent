# Deploying RedactAgent on ASUS UGen Intel Arc Pro B70 32GB

> Stage II plan. The Stage I prototype runs on a laptop through Ollama; the code already
> speaks the OpenAI-compatible API that vLLM exposes, so moving to the B70 is a configuration
> change (`RA_BACKEND=openai`), not a rewrite. Memory figures below are planning estimates and
> will be replaced by measurements on the organiser's SDV environment.

## Why this workload needs the B70

| Requirement | Laptop prototype | B70 32GB target |
|---|---|---|
| Contextual model | Qwen3-8B (Q4) | **Qwen3-30B-A3B** (MoE, INT4) - better recall on names / quasi-identifiers in long, messy OCR |
| Vision model | Qwen2.5-VL-7B (Q4) | Qwen2.5-VL-7B (FP8) resident **at the same time** - no model swapping between pages |
| Concurrency | 1 page at a time | vLLM continuous batching: many pages / users in parallel |
| Data residency | on-device | on-premises server in the hospital / firm / agency LAN |
| Reliability | consumer RAM | **ECC GDDR6** - long unattended batch jobs (legal discovery, archive digitisation) |

Planned VRAM budget (single card, 32 GB):

| Component | Precision | Weights | KV cache / runtime | Total |
|---|---|---|---|---|
| Qwen3-30B-A3B (text) | INT4 (AWQ) | ~16 GB | ~3 GB | ~19 GB |
| Qwen2.5-VL-7B (vision) | FP8 | ~8.5 GB | ~2.5 GB | ~11 GB |
| Headroom | | | | ~2 GB |

Fallback if the budget is tight: Qwen3-14B INT4 (~9 GB) for text. Scale-out: a second B70 gives
each model its own card (64 GB pool) and doubles batch throughput.

## Serving (vLLM XPU)

`compose.yaml` starts two vLLM servers on the same GPU plus the RedactAgent web app:

```bash
cp .env.example .env        # set the vLLM XPU image tag from Intel's LLM Scaler release
docker compose up -d
open http://<b70-host>:8080
```

RedactAgent environment:

```bash
RA_BACKEND=openai
RA_BASE_URL=http://vllm-text:8000         # Qwen3-30B-A3B
RA_VISION_BASE_URL=http://vllm-vision:8001  # Qwen2.5-VL-7B
RA_TEXT_MODEL=Qwen/Qwen3-30B-A3B
RA_VISION_MODEL=Qwen/Qwen2.5-VL-7B-Instruct
```

Structured output uses vLLM's `response_format: json_schema` (guided decoding), the same JSON
schemas the Ollama path uses, so detector code is unchanged.

## OCR on Intel

RapidOCR runs PP-OCR models through ONNX Runtime; on the B70 host it can switch to the
OpenVINO execution provider (`rapidocr_openvino`) to run on the Xeon/Core CPU or the Arc GPU.

## Stage II validation plan

1. Bring-up on the SDV virtual host: both models resident, `GET /api/info` shows both online.
2. Re-run `eval/evaluate.py` on the same synthetic corpus - compare recall / precision with the laptop.
3. Throughput test: 1, 4, 8, 16 concurrent pages; report pages/min and p95 latency.
4. Power and cost: tokens per watt from the B70 telemetry; cost per 1,000 pages vs. cloud APIs.
