"""Model client for local inference servers.

Two interchangeable backends so the same code runs on a laptop and on the B70:
  * "ollama" - Ollama native API (Apple Silicon / CPU / Intel GPU via IPEX-LLM Ollama)
  * "openai" - any OpenAI-compatible server, e.g. vLLM XPU on Intel Arc Pro B70
Both return parsed JSON constrained by a JSON schema (structured decoding), so the
detectors never have to parse free text.
"""

from __future__ import annotations

import base64
import io
import json
import time
from dataclasses import dataclass

import httpx
from PIL import Image

from . import config


@dataclass
class CallStats:
    seconds: float
    prompt_tokens: int = 0
    completion_tokens: int = 0


def _b64_png(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class ModelClient:
    def __init__(self, model: str, backend: str | None = None, base_url: str | None = None, think: bool | None = False):
        self.model = model
        self.backend = backend or config.BACKEND
        self.base_url = (base_url or config.BASE_URL).rstrip("/")
        self.think = think
        self.http = httpx.Client(timeout=config.TIMEOUT)

    def chat_json(self, system: str, user: str, schema: dict, images: list[Image.Image] | None = None,
                  max_tokens: int = 2048, num_ctx: int = 8192) -> tuple[dict, CallStats]:
        t0 = time.perf_counter()
        if self.backend == "ollama":
            msg = {"role": "user", "content": user}
            if images:
                msg["images"] = [_b64_png(i) for i in images]
            body = {
                "model": self.model,
                "messages": [{"role": "system", "content": system}, msg],
                "format": schema,
                "stream": False,
                "keep_alive": "60m",
                "options": {"temperature": 0, "num_ctx": num_ctx, "num_predict": max_tokens},
            }
            if self.think is not None:
                body["think"] = self.think
            r = self.http.post(f"{self.base_url}/api/chat", json=body)
            r.raise_for_status()
            data = r.json()
            content = data["message"]["content"]
            stats = CallStats(time.perf_counter() - t0, data.get("prompt_eval_count", 0), data.get("eval_count", 0))
        else:
            parts: list[dict] = [{"type": "text", "text": user}]
            for im in images or []:
                parts.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + _b64_png(im)}})
            body = {
                "model": self.model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": parts}],
                "temperature": 0,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_schema", "json_schema": {"name": "result", "schema": schema}},
                "chat_template_kwargs": {"enable_thinking": bool(self.think)},
            }
            self._reasoning(body)
            data = self._post_openai(body)
            content = data["choices"][0]["message"]["content"] or "{}"
            usage = data.get("usage", {})
            stats = CallStats(time.perf_counter() - t0, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        try:
            return json.loads(content), stats
        except json.JSONDecodeError:
            # structured decoding should prevent this; recover the largest JSON object if it happens
            s, e = content.find("{"), content.rfind("}")
            return (json.loads(content[s:e + 1]) if s >= 0 and e > s else {}), stats

    def chat_text(self, system: str, user: str, max_tokens: int = 1024, num_ctx: int = 8192) -> tuple[str, CallStats]:
        """Unconstrained text completion (used with compact line formats, ~3x fewer tokens than JSON)."""
        t0 = time.perf_counter()
        if self.backend == "ollama":
            body = {"model": self.model, "stream": False, "keep_alive": "60m",
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "options": {"temperature": 0, "num_ctx": num_ctx, "num_predict": max_tokens}}
            if self.think is not None:
                body["think"] = self.think
            r = self.http.post(f"{self.base_url}/api/chat", json=body)
            r.raise_for_status()
            data = r.json()
            return data["message"]["content"], CallStats(time.perf_counter() - t0, data.get("prompt_eval_count", 0),
                                                          data.get("eval_count", 0))
        body = {"model": self.model, "temperature": 0, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "chat_template_kwargs": {"enable_thinking": bool(self.think)}}
        self._reasoning(body)
        data = self._post_openai(body)
        usage = data.get("usage", {})
        return data["choices"][0]["message"]["content"] or "", CallStats(time.perf_counter() - t0, usage.get("prompt_tokens", 0),
                                                                    usage.get("completion_tokens", 0))

    def _post_openai(self, body: dict) -> dict:
        """POST a chat completion. For reasoning models, greedy decoding occasionally loops in the reasoning until the
        token cap and returns no answer; retry such a call once with sampling (RA_RETRY_TEMPERATURE)."""
        r = self.http.post(f"{self.base_url}/v1/chat/completions", json=body)
        r.raise_for_status()
        data = r.json()
        ch = data["choices"][0]
        if config.REASONING_EFFORT and (ch.get("finish_reason") == "length" or not (ch["message"].get("content") or "").strip()):
            retry = dict(body, temperature=config.RETRY_TEMPERATURE)
            r2 = self.http.post(f"{self.base_url}/v1/chat/completions", json=retry)
            r2.raise_for_status()
            data2 = r2.json()
            if (data2["choices"][0]["message"].get("content") or "").strip():
                u1, u2 = data.get("usage", {}), data2.get("usage", {})
                data2["usage"] = {k: u1.get(k, 0) + u2.get(k, 0) for k in ("prompt_tokens", "completion_tokens")}
                data2["retried"] = True
                return data2
        return data

    def _reasoning(self, body: dict) -> None:
        """Always-reasoning models (e.g. gpt-oss) spend tokens before the answer: lower the effort and add
        a reasoning allowance so the answer is not cut off (RA_REASONING_EFFORT=low|medium|high)."""
        if config.REASONING_EFFORT:
            body["reasoning_effort"] = config.REASONING_EFFORT
            body["max_tokens"] = body["max_tokens"] + config.REASONING_TOKENS

    def ping(self) -> bool:
        try:
            if self.backend == "ollama":
                r = self.http.get(f"{self.base_url}/api/tags", timeout=3)
                return r.status_code == 200 and any(m["name"].startswith(self.model.split(":")[0]) for m in r.json().get("models", []))
            r = self.http.get(f"{self.base_url}/v1/models", timeout=3)
            return r.status_code == 200
        except httpx.HTTPError:
            return False
