# Deploying RedactAgent on 2x Intel Arc Pro B70 32GB

Tested on the organiser-provided Intel Cloud host: 2x Arc Pro B70 32 GB, 2x Xeon 6787P (344 vCPU, AMX),
251 GB RAM, Ubuntu 26.04, Docker, image `vllm/vllm-openai-xpu:v0.33.0` (development started on 0.26.0).

## One command

```bash
git clone https://github.com/bananabbgun/RedactAgent.git && cd RedactAgent
bash deploy/b70/up.sh
```

`up.sh` does four things:

1. starts **one vLLM XPU server per card** – `ZE_AFFINITY_MASK=0` text LLM on port 8000, `ZE_AFFINITY_MASK=1`
   vision-language model on port 8001 (both bound to 127.0.0.1);
2. waits until both answer `/v1/models` (prints the container log and stops if one exits);
3. creates `.venv` with `uv` on first run and installs `requirements.txt`;
4. starts the RedactAgent web UI (default `127.0.0.1:8080`; `/batch`, `/system`).

Reach the UI through an SSH tunnel or a reverse proxy with authentication – it is deliberately not exposed on all
interfaces. On the Intel Cloud JupyterLab, the recording script (`scripts/record_b70.py`) drives a headless
browser on the host itself.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `TEXT_MODEL` | `openai/gpt-oss-20b` | contextual PII + agentic re-identification check (card 0) |
| `TEXT_EXTRA` | – | extra vLLM args for the text server, e.g. `--quantization fp8` |
| `VISION_MODEL` | `Qwen/Qwen2.5-VL-7B-Instruct` | signatures, photos, seals (card 1) |
| `GPU_UTIL` | `0.85` | VRAM fraction vLLM may use per card |
| `RA_OCR_THREADS` | `8` | ONNX Runtime threads per OCR engine (one engine per worker thread) |
| `RA_WORKERS` | `8` | pages processed concurrently by the web app / batch mode |
| `RA_REASONING_EFFORT` | `low` for gpt-oss | only for always-reasoning models: `low` / `medium` / `high` |
| `RA_TEMPERATURE` | `0` | text-model decoding: `0` = greedy (accuracy mode), `1.0` = sampled (throughput mode) |
| `RA_STREAM_LOOP_GUARD` | `1` | stream reasoning-model calls and cancel a runaway repetition loop |
| `RA_LOOP_MIN_CHUNKS` | `2000` | cancel only a loop still running after this many streamed tokens |
| `RA_MAX_RETRIES` | `2` | sampled retries after a cancelled or truncated call |
| `HOST`, `PORT` | `127.0.0.1`, `8080` | web UI address |

The configurations measured in [`docs/STAGE2_LOG.md`](../../docs/STAGE2_LOG.md):

```bash
bash deploy/b70/up.sh                                                              # accuracy mode: gpt-oss-20b, greedy + loop guard (default)
RA_TEMPERATURE=1.0 bash deploy/b70/up.sh                                           # throughput mode: same model, sampled
TEXT_MODEL=Qwen/Qwen3-8B  TEXT_EXTRA="--quantization fp8" bash deploy/b70/up.sh
TEXT_MODEL=Qwen/Qwen3-14B TEXT_EXTRA="--quantization fp8" bash deploy/b70/up.sh
TEXT_MODEL=Qwen/Qwen3-30B-A3B-GPTQ-Int4 bash deploy/b70/up.sh
```

## Lessons from bring-up (vLLM XPU 0.26 → 0.33 on this host)

| Symptom | Cause / fix |
|---|---|
| `Failed to infer device type` | the oneAPI environment is not sourced; `up.sh` uses `bash -c "source /opt/intel/oneapi/setvars.sh; exec …"` as entrypoint |
| graph capture fails with `UR_RESULT_ERROR_OUT_OF_RESOURCES` (also at `GPU_UTIL=0.70`) | XPU graph mode not usable here; `--enforce-eager` |
| `--limit-mm-per-prompt` JSON quoting errors | use the dotted form `--limit-mm-per-prompt.image=1` |
| throughput flat beyond 4 pages in flight, GPUs idle | OCR threads oversubscribed 344 cores; cap with `RA_OCR_THREADS=8` (9x faster OCR) |
| `xpu-smi` hangs a server started from a terminal | it reads stdin; `redactagent/hwmon.py` starts it with stdin closed; GPU utilisation reads N/A on this platform, so board power is used as the activity signal |
| gpt-oss returns an empty answer | it reasons first and runs out of tokens; set `RA_REASONING_EFFORT=low` |
| some gpt-oss calls repeat their reasoning until the token cap | greedy decoding loops occasionally; the loop guard cancels a loop still running after 2,000 tokens and resamples, or use `RA_TEMPERATURE=1.0` (no loops) |
| bursts of `!!!!` output / many loops at once on 0.26 | not seen on vLLM XPU 0.33.0; upgrade the image |

## Health checks

- `GET /api/system` – host, both cards (power, VRAM, temperature), served models.
- `GET /api/system/diagnostics` – host, OS, CPU, memory, `xpu-smi discovery`, `docker ps` (fixed read-only commands).
- `python eval/evaluate.py --workers 8 --data data/synthetic_v3 --out /tmp/v3` – end-to-end accuracy check.
