"""Tamper-evident audit trail (hash chain, JSON Lines).

Every entry stores the SHA-256 of the previous entry, so deleting or editing any
past record breaks verification. Documents themselves are never logged - only
their hashes, the detector counts and the reviewer's decisions.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path

GENESIS = "0" * 64


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class AuditLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _last_hash(self) -> str:
        if not self.path.exists():
            return GENESIS
        last = GENESIS
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    last = json.loads(line)["hash"]
        return last

    @staticmethod
    def _digest(entry: dict) -> str:
        body = {k: v for k, v in entry.items() if k != "hash"}
        return sha256_bytes(json.dumps(body, sort_keys=True, ensure_ascii=False).encode())

    def append(self, event: str, job_id: str, actor: str = "system", **data) -> dict:
        with self._lock:
            entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": event, "job": job_id, "actor": actor,
                     "data": data, "prev": self._last_hash()}
            entry["hash"] = self._digest(entry)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return entry

    def entries(self, job_id: str | None = None) -> list[dict]:
        if not self.path.exists():
            return []
        out = [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
        return [e for e in out if job_id is None or e["job"] == job_id]

    def verify(self) -> dict:
        prev = GENESIS
        entries = self.entries()
        for i, e in enumerate(entries):
            if e["prev"] != prev or self._digest(e) != e["hash"]:
                return {"ok": False, "entries": len(entries), "broken_at": i}
            prev = e["hash"]
        return {"ok": True, "entries": len(entries), "head": prev}
