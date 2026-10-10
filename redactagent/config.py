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
VISION_MODEL = os.getenv("RA_VISION_MODEL", "qwen2.5vl:7b")
TIMEOUT = float(os.getenv("RA_TIMEOUT", "300"))

RENDER_DPI = int(os.getenv("RA_DPI", "150"))
RUNS_DIR = Path(os.getenv("RA_RUNS_DIR", ROOT / "runs"))
POLICY_DIR = Path(os.getenv("RA_POLICY_DIR", ROOT / "policies"))
SAMPLES_DIR = Path(os.getenv("RA_SAMPLES_DIR", ROOT / "data" / "samples"))
