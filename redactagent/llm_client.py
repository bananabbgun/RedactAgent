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
import logging
import time
from dataclasses import dataclass

import httpx
from PIL import Image

from . import config

log = logging.getLogger("redactagent.llm")


def is_looping(text: str, min_repeats: int = 3, min_span: int = 400, max_period: int = 400) -> bool:
    """True if the tail of `text` is (exactly) periodic: one chunk of p <= `max_period` characters repeated at least
    `min_repeats` times, covering at least `min_span` characters. Normal reasoning never repeats itself verbatim
    several times over; a degenerate decoding loop does (observed periods: 20-250 characters)."""
    for p in range(4, max_period + 1):
        n = max(min_repeats * p, min_span)
        if len(text) < n:
            break
        s = text[-n:]
        if s[p:] == s[:-p]:
            return True
    return False


@dataclass
class CallStats:
    seconds: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    attempts: int = 1  # >1 when a runaway reasoning loop was cancelled and retried


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
            stats = CallStats(time.perf_counter() - t0, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
                              data.get("attempts", 1))
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
                                                                    usage.get("completion_tokens", 0), data.get("attempts", 1))

    def _post_openai(self, body: dict) -> dict:
        """POST a chat completion. For reasoning models, decoding occasionally falls into a repetition loop in the
        reasoning ("Also line 25 date. Also line 25 date. ...") that would run to the token cap and return no answer.
        On vLLM XPU this happens at random (~5 % of calls, different pages in different runs), so it is handled at run
        time: the response is streamed, a loop is detected from the text itself and the request is cancelled within a
        few hundred tokens, then retried with sampling (RA_RETRY_TEMPERATURE, up to RA_MAX_RETRIES times). A
        repetition penalty is deliberately not sent by default: on vLLM XPU 0.26 requests carrying
        repetition_penalty were followed by many more looping requests (see docs/STAGE2_LOG.md)."""
        if not config.REASONING_EFFORT:
            r = self.http.post(f"{self.base_url}/v1/chat/completions", json=body)
            r.raise_for_status()
            return r.json()
        used = {"prompt_tokens": 0, "completion_tokens": 0}
        data: dict = {}
        for attempt in range(1 + config.MAX_RETRIES):
            req = body
            if attempt:
                req = dict(body, temperature=config.RETRY_TEMPERATURE, seed=attempt)
                if config.RETRY_REPETITION_PENALTY != 1.0:
                    req["repetition_penalty"] = config.RETRY_REPETITION_PENALTY
            data = self._stream_openai(req) if config.STREAM_LOOP_GUARD else self._plain_openai(req)
            for k in used:
                used[k] += data.get("usage", {}).get(k, 0)
            ch = data["choices"][0]
            if ch.get("finish_reason") not in ("length", "loop") and (ch["message"].get("content") or "").strip():
                break
        data["usage"] = used
        data["attempts"] = attempt + 1
        return data

    def _plain_openai(self, body: dict) -> dict:
        r = self.http.post(f"{self.base_url}/v1/chat/completions", json=body)
        r.raise_for_status()
        return r.json()

    def _stream_openai(self, body: dict) -> dict:
        """Stream one completion; cancel it as soon as the generated text becomes periodic (a runaway loop).
        Returns the same shape as a non-streamed response; finish_reason "loop" marks a cancelled request."""
        body = dict(body, stream=True, stream_options={"include_usage": True})
        reasoning, content, finish, usage, chunks, checked = [], [], None, {}, 0, 0
        with self.http.stream("POST", f"{self.base_url}/v1/chat/completions", json=body) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line.startswith("data: ") or line.strip() == "data: [DONE]":
                    continue
                d = json.loads(line[6:])
                if d.get("usage"):
                    usage = d["usage"]
                for c in d.get("choices", []):
                    delta = c.get("delta") or {}
                    reasoning.append(delta.get("reasoning_content") or delta.get("reasoning") or "")
                    content.append(delta.get("content") or "")
                    finish = c.get("finish_reason") or finish
                    chunks += 1
                if chunks - checked >= 32:
                    checked = chunks
                    if is_looping("".join(reasoning)) or is_looping("".join(content)):
                        finish = "loop"
                        log.warning("loop-guard: cancelled a looping completion after %d chunks (temperature %s)",
                                    chunks, body.get("temperature"))
                        if config.LOOP_DUMP_DIR:  # debugging aid: keep the cancelled text
                            d = config.LOOP_DUMP_DIR
                            d.mkdir(parents=True, exist_ok=True)
                            (d / f"loop_{time.time():.3f}.txt").write_text(
                                "".join(reasoning) + "\n=====CONTENT=====\n" + "".join(content), encoding="utf-8")
                        break  # leaving the context closes the connection; vLLM aborts the request
        if finish == "loop" and not usage:
            usage = {"prompt_tokens": 0, "completion_tokens": chunks}
        return {"choices": [{"message": {"content": "".join(content), "reasoning_content": "".join(reasoning)},
                             "finish_reason": finish}], "usage": usage}

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
