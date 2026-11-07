# Client environment for scripts that talk to the two vLLM servers started by deploy/b70/up.sh.
#   source deploy/b70/env.sh && python eval/evaluate.py --workers 8 --data data/synthetic_v3 --out /tmp/v3
export RA_BACKEND=openai
export RA_BASE_URL=http://127.0.0.1:8000 RA_VISION_BASE_URL=http://127.0.0.1:8001
export RA_TEXT_MODEL=text RA_VISION_MODEL=vision
export RA_OCR_THREADS=${RA_OCR_THREADS:-8}
# the default text model (gpt-oss-20b) reasons first; keep it short (unset for Qwen3)
export RA_REASONING_EFFORT=${RA_REASONING_EFFORT-low}
[ -d .venv ] && source .venv/bin/activate
