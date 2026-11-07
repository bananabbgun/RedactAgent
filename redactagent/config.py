"""Runtime configuration (environment variables override defaults).

Laptop prototype (default):   Ollama on Apple Silicon, Qwen3-8B + Qwen2.5-VL-7B
Intel Arc Pro B70 (Stage II):  RA_BACKEND=openai RA_BASE_URL=http://localhost:8000
                               RA_TEXT_MODEL=Qwen/Qwen3-30B-A3B ... (see deploy/b70/)
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BACKEND = os.getenv("RA_BACKEND", "ollama")  # "ollama" | "openai"
BASE_URL = os.getenv("RA_BASE_URL", "http://127.0.0.1:11434")
VISION_BASE_URL = os.getenv("RA_VISION_BASE_URL", BASE_URL)
TEXT_MODEL = os.getenv("RA_TEXT_MODEL", "qwen3:8b")
REASONING_EFFORT = os.getenv("RA_REASONING_EFFORT", "")  # only for always-reasoning models such as gpt-oss
REASONING_TOKENS = int(os.getenv("RA_REASONING_TOKENS", "2048"))
RETRY_TEMPERATURE = float(os.getenv("RA_RETRY_TEMPERATURE", "0.7"))  # one sampled retry after a runaway reasoning call
RETRY_REPETITION_PENALTY = float(os.getenv("RA_RETRY_REPETITION_PENALTY", "1.1"))  # vLLM sampling parameter
VISION_MODEL = os.getenv("RA_VISION_MODEL", "qwen2.5vl:7b")
TIMEOUT = float(os.getenv("RA_TIMEOUT", "300"))
# Run the LLM and VLM layers of a page at the same time. Default on for a vLLM backend (separate GPUs);
# off for the laptop/Ollama path, where only one model fits in memory at a time.
PARALLEL_LAYERS = os.getenv("RA_PARALLEL_LAYERS", "1" if BACKEND == "openai" else "0") == "1"
# Documents processed concurrently by the server (vLLM batches the requests on the GPU).
WORKERS = int(os.getenv("RA_WORKERS", "8" if BACKEND == "openai" else "1"))
BATCH_DIR = Path(os.getenv("RA_BATCH_DIR", ROOT / "data" / "synthetic" / "images"))

RENDER_DPI = int(os.getenv("RA_DPI", "150"))
RUNS_DIR = Path(os.getenv("RA_RUNS_DIR", ROOT / "runs"))
POLICY_DIR = Path(os.getenv("RA_POLICY_DIR", ROOT / "policies"))
SAMPLES_DIR = Path(os.getenv("RA_SAMPLES_DIR", ROOT / "data" / "samples"))
