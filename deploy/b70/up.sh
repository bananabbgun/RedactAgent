#!/bin/bash
# One-command deployment of RedactAgent on a 2x Intel Arc Pro B70 host (tested on Intel Cloud, Ubuntu 26.04,
# vllm/vllm-openai-xpu:v0.26.0). Card 0 serves the contextual LLM, card 1 the vision-language model.
#
#   bash deploy/b70/up.sh                 # default models, web UI on 127.0.0.1:8080
#   TEXT_MODEL=Qwen/Qwen3-14B TEXT_EXTRA="--quantization fp8" bash deploy/b70/up.sh
#
# Environment knobs:
#   TEXT_MODEL / VISION_MODEL   Hugging Face model ids
#   TEXT_EXTRA / VISION_EXTRA   extra vLLM arguments (e.g. "--quantization fp8")
#   GPU_UTIL                    fraction of each card's VRAM vLLM may use (default 0.85)
#   HOST / PORT                 where the RedactAgent web UI listens (default 127.0.0.1:8080)
set -euo pipefail
cd "$(dirname "$0")/../.."

IMG=${IMG:-vllm/vllm-openai-xpu:v0.26.0}
TEXT_MODEL=${TEXT_MODEL:-Qwen/Qwen3-8B}
VISION_MODEL=${VISION_MODEL:-Qwen/Qwen2.5-VL-7B-Instruct}
GPU_UTIL=${GPU_UTIL:-0.85}
HF_CACHE=${HF_CACHE:-$HOME/hf-cache}
mkdir -p "$HF_CACHE"

launch() {  # container card port model served-name extra...
  local name=$1 card=$2 port=$3 model=$4 served=$5; shift 5
  docker rm -f "$name" >/dev/null 2>&1 || true
  local serve="python -m vllm.entrypoints.openai.api_server --model $model --served-model-name $served \
    --dtype bfloat16 --host 127.0.0.1 --port $port --gpu-memory-utilization $GPU_UTIL --max-model-len 8192 \
    --block-size 64 --enforce-eager $*"
  # ZE_AFFINITY_MASK pins the server to one Arc Pro B70; the oneAPI environment must be sourced first.
  docker run -d --name "$name" --net=host --ipc=host --shm-size=16g --privileged \
    --device /dev/dri:/dev/dri -v /dev/dri/by-path:/dev/dri/by-path -v "$HF_CACHE":/root/.cache/huggingface \
    -e ZE_AFFINITY_MASK="$card" -e VLLM_WORKER_MULTIPROC_METHOD=spawn \
    --entrypoint bash "$IMG" -c "source /opt/intel/oneapi/setvars.sh --force >/dev/null 2>&1 || true; exec $serve" >/dev/null
  echo "started $name on XPU $card: $model"
}

launch ra-text 0 8000 "$TEXT_MODEL" text ${TEXT_EXTRA:-}
launch ra-vision 1 8001 "$VISION_MODEL" vision --limit-mm-per-prompt.image=1 ${VISION_EXTRA:-}

echo -n "waiting for both model servers"
for _ in $(seq 1 240); do
  if curl -sf -m 2 127.0.0.1:8000/v1/models >/dev/null && curl -sf -m 2 127.0.0.1:8001/v1/models >/dev/null; then
    echo " ready"; break
  fi
  for c in ra-text ra-vision; do
    if [ "$(docker inspect -f '{{.State.Status}}' $c)" = exited ]; then echo; docker logs --tail 30 $c; exit 1; fi
  done
  echo -n "."; sleep 5
done

[ -d .venv ] || { command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh; \
  ~/.local/bin/uv venv --python 3.12 .venv && ~/.local/bin/uv pip install --python .venv/bin/python -r requirements.txt; }

export RA_BACKEND=openai RA_BASE_URL=http://127.0.0.1:8000 RA_VISION_BASE_URL=http://127.0.0.1:8001
export RA_TEXT_MODEL=text RA_VISION_MODEL=vision RA_OCR_THREADS=${RA_OCR_THREADS:-8}
echo "RedactAgent UI: http://${HOST:-127.0.0.1}:${PORT:-8080}  (batch mode: /batch)"
exec .venv/bin/python -c "import uvicorn; uvicorn.run('redactagent.server:app', host='${HOST:-127.0.0.1}', port=${PORT:-8080})"
