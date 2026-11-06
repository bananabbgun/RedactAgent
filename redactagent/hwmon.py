"""Live hardware telemetry for the UI: Intel GPUs via `xpu-smi`, host CPU/RAM, served models.

One background `xpu-smi dump` stream per card keeps the latest utilisation, power and
memory plus a two-minute history, so the review UI can show what each Arc Pro B70 is
doing while documents are processed. On machines without xpu-smi it reports
`available: false` and the UI hides the panel.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import threading
import time
from collections import deque

import httpx

from . import config

METRICS = "0,1,18"  # utilization.gpu %, power.draw W, memory.used MiB
# which card serves which model (matches deploy/b70 launch: ZE_AFFINITY_MASK=0 text, =1 vision)
ROLES = dict(x.split(":") for x in os.getenv("RA_GPU_ROLES", "0:text model,1:vision model").split(","))


class GpuMonitor:
    def __init__(self):
        self.available = shutil.which("xpu-smi") is not None
        self.devices: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._started = False

    def start(self):
        if not self.available or self._started:
            return
        self._started = True
        for dev in self._discover():
            self.devices[dev["id"]] = {**dev, "util": None, "power": None, "mem_used": None,
                                       "history": deque(maxlen=120)}
            threading.Thread(target=self._stream, args=(dev["id"],), daemon=True).start()

    def _discover(self) -> list[dict]:
        try:
            out = subprocess.run(["xpu-smi", "discovery"], capture_output=True, text=True, timeout=20,
                                 stdin=subprocess.DEVNULL).stdout
        except (OSError, subprocess.TimeoutExpired):
            return []
        devs, cur = [], None
        for line in out.splitlines():
            m = re.match(r"^\s*\|?\s*(\d+)\s*\|?\s*Device Name:\s*(.+?)\s*\|?\s*$", line)
            if m:
                cur = {"id": m.group(1), "name": m.group(2).replace("(R)", "").replace("(TM)", "").strip()}
                devs.append(cur)
        for d in devs:  # total memory per card
            try:
                det = subprocess.run(["xpu-smi", "discovery", "--device", d["id"]], capture_output=True, text=True,
                                     timeout=20, stdin=subprocess.DEVNULL).stdout
                m = re.search(r"Memory Physical Size:\s*([\d.]+)\s*MiB", det)
                d["mem_total"] = float(m.group(1)) if m else None
            except (OSError, subprocess.TimeoutExpired):
                d["mem_total"] = None
            d["role"] = ROLES.get(d["id"], "")
        return devs

    def _stream(self, dev: str):
        while True:
            try:
                p = subprocess.Popen(["xpu-smi", "dump", "--device", dev, "--metrics", METRICS, "--interval", "1"],
                                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     text=True, bufsize=1)  # no TTY: a background xpu-smi touching it gets stopped
                header = None
                for line in p.stdout:
                    cells = [c.strip() for c in line.split(",")]
                    if header is None:
                        header = [c.lower() for c in cells]
                        continue
                    rec = dict(zip(header, cells))

                    def num(kw):
                        for k, v in rec.items():
                            if kw in k:
                                try:
                                    return float(v)
                                except ValueError:
                                    return None
                        return None

                    with self._lock:
                        d = self.devices[dev]
                        d["util"], d["power"], d["mem_used"] = num("util"), num("power"), num("memory")
                        d["history"].append((round(time.time(), 1), d["util"], d["power"]))
            except OSError:
                pass
            time.sleep(5)  # restart the stream if xpu-smi exits

    def snapshot(self) -> dict:
        with self._lock:
            gpus = [{k: (list(v) if k == "history" else v) for k, v in d.items()} for d in self.devices.values()]
        return {"available": self.available and bool(gpus), "gpus": gpus}


def host_info() -> dict:
    mem_gb = None
    try:
        with open("/proc/meminfo") as fh:
            m = re.search(r"MemTotal:\s+(\d+)", fh.read())
            mem_gb = round(int(m.group(1)) / 1024 / 1024) if m else None
    except OSError:
        pass
    return {"hostname": socket.gethostname(), "cpus": os.cpu_count(), "ram_gb": mem_gb}


_model_cache: dict = {"t": 0, "data": []}


def served_models() -> list[dict]:
    """What each vLLM server is actually serving (cached 30 s)."""
    if time.time() - _model_cache["t"] < 30:
        return _model_cache["data"]
    out = []
    if config.BACKEND == "openai":
        for role, url in (("text", config.BASE_URL), ("vision", config.VISION_BASE_URL)):
            try:
                r = httpx.get(f"{url.rstrip('/')}/v1/models", timeout=3).json()
                for m in r.get("data", []):
                    out.append({"role": role, "served": m.get("id"), "model": m.get("root"),
                                "max_len": m.get("max_model_len"), "url": url})
            except (httpx.HTTPError, ValueError):
                out.append({"role": role, "served": None, "model": None, "url": url})
    _model_cache.update(t=time.time(), data=out)
    return out


monitor = GpuMonitor()


DIAG_COMMANDS = [  # fixed, read-only diagnostics shown on the /system page
    ("host", ["hostname"]),
    ("os", ["bash", "-c", "grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '\\\"'; uname -r"]),
    ("cpu", ["bash", "-c", "lscpu | grep -E 'Model name|^Socket|^CPU\\(s\\)' | sed 's/  */ /g'"]),
    ("memory", ["bash", "-c", "free -g | head -n 2"]),
    ("gpus", ["xpu-smi", "discovery"]),
    ("containers", ["docker", "ps", "--format", "{{.Names}}  {{.Image}}  {{.Status}}"]),
]


def diagnostics() -> dict:
    out = {}
    for key, cmd in DIAG_COMMANDS:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15, stdin=subprocess.DEVNULL)
            out[key] = (r.stdout or r.stderr).strip()
        except (OSError, subprocess.TimeoutExpired) as e:
            out[key] = f"unavailable ({type(e).__name__})"
    out["captured_at"] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    return out
