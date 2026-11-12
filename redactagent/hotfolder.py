"""Hot-folder integration: connect RedactAgent to an existing document system without writing code.

    python -m redactagent.hotfolder --inbox /srv/redact/inbox --outbox /srv/redact/outbox --policy research

A hospital system (records management, IRB portal, scanner) drops PDFs or images into the inbox. For each file
this client, which talks to a running RedactAgent server over its REST API:

1. submits it (POST /api/jobs) and moves the original to inbox/submitted/;
2. when detection is finished, writes outbox/pending_review/<name>.json: a review ticket with the link the
   reviewer opens (/?job=<id>), the triage priority and the reasons (re-identification risk, ink the OCR did not
   read, unconfirmed suggestions);
3. after the reviewer has approved and exported the document in the browser, copies the burned-in PDF and the
   JSON report to outbox/released/ and removes the ticket.

Nothing is released without a person: step 3 only follows an export recorded in the hash-chained audit log.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import httpx

SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def triage(summary: dict, findings: list[dict], risk_threshold: int) -> tuple[str, list[str]]:
    """Review priority for one document: 'full' review or 'standard' review, with the reasons shown to people."""
    reasons = []
    score = (summary.get("risk") or {}).get("score")
    if score is not None and score >= risk_threshold:
        reasons.append(f"re-identification risk {score}/100")
    if summary.get("warnings"):
        reasons.append(f"{len(summary['warnings'])} region(s) with ink the OCR did not read")
    pending = sum(1 for f in findings if not f.get("accepted"))
    if pending:
        reasons.append(f"{pending} unconfirmed suggestion(s)")
    if summary.get("error"):
        reasons.append("processing error: " + summary["error"])
    return ("full" if reasons else "standard"), reasons


def stable(p: Path, wait: float = 1.0) -> bool:
    """A file still being copied into the inbox changes size; only pick it up once it stops growing."""
    s = p.stat().st_size
    time.sleep(wait)
    return p.exists() and p.stat().st_size == s and s > 0


class HotFolder:
    def __init__(self, server: str, inbox: Path, outbox: Path, policy: str, risk_threshold: int):
        self.http = httpx.Client(base_url=server.rstrip("/"), timeout=120)
        self.server, self.inbox, self.outbox = server.rstrip("/"), inbox, outbox
        self.policy, self.risk_threshold = policy, risk_threshold
        self.submitted = inbox / "submitted"
        self.pending = outbox / "pending_review"
        self.released = outbox / "released"
        for d in (self.submitted, self.pending, self.released):
            d.mkdir(parents=True, exist_ok=True)
        self.state_file = outbox / ".hotfolder_state.json"
        self.state = json.loads(self.state_file.read_text()) if self.state_file.exists() else {}

    def save(self):
        self.state_file.write_text(json.dumps(self.state, indent=1))

    def submit_new(self):
        for p in sorted(self.inbox.iterdir()):
            if not p.is_file() or p.suffix.lower() not in SUFFIXES or p.name.startswith(".") or not stable(p):
                continue
            with p.open("rb") as fh:
                r = self.http.post("/api/jobs", files={"file": (p.name, fh)}, data={"policy": self.policy})
            r.raise_for_status()
            job = r.json()
            dst = self.submitted / f"{job['id']}_{p.name}"
            shutil.move(str(p), dst)
            self.state[job["id"]] = {"file": p.name, "stage": "processing", "source": str(dst)}
            print(f"submitted {p.name} -> job {job['id']}", flush=True)
            self.save()

    def advance(self):
        for jid, st in list(self.state.items()):
            if st["stage"] == "processing":
                s = self.http.get(f"/api/jobs/{jid}").json()
                if s["status"] not in ("done", "error"):
                    continue
                findings = s.get("findings", [])  # included once the job is done
                prio, reasons = triage(s, findings, self.risk_threshold)
                ticket = {"file": st["file"], "job": jid, "status": s["status"], "review_url": f"{self.server}/?job={jid}",
                          "priority": prio, "reasons": reasons, "policy": s["policy"], "pages": s["pages"],
                          "findings": s["n_findings"], "by_category": s["by_category"],
                          "risk": (s.get("risk") or {}).get("score"), "input_sha256": s["input_sha256"]}
                (self.pending / f"{Path(st['file']).stem}.json").write_text(json.dumps(ticket, ensure_ascii=False, indent=1))
                st["stage"] = "pending_review"
                print(f"ready for review ({prio}): {st['file']}  {ticket['review_url']}", flush=True)
                self.save()
            elif st["stage"] == "pending_review":
                entries = self.http.get("/api/audit", params={"job": jid}).json().get("entries", [])
                if not any(e.get("event") == "export" for e in entries):
                    continue
                stem = Path(st["file"]).stem
                for name in ("redacted.pdf", "report.json"):
                    r = self.http.get(f"/api/jobs/{jid}/download/{name}")
                    r.raise_for_status()
                    (self.released / f"{stem}_{name}").write_bytes(r.content)
                (self.pending / f"{stem}.json").unlink(missing_ok=True)
                st["stage"] = "released"
                print(f"released after review: {st['file']}", flush=True)
                self.save()

    def loop(self, interval: float):
        while True:
            try:
                self.submit_new()
                self.advance()
            except httpx.HTTPError as e:  # server restarting: keep the files, try again
                print("server not reachable:", e, flush=True)
            time.sleep(interval)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--server", default="http://127.0.0.1:8080")
    ap.add_argument("--inbox", required=True, type=Path)
    ap.add_argument("--outbox", required=True, type=Path)
    ap.add_argument("--policy", default="strict")
    ap.add_argument("--risk-threshold", type=int, default=70, help="risk score that triggers a full review (eval/triage.py)")
    ap.add_argument("--interval", type=float, default=5.0)
    a = ap.parse_args()
    a.inbox.mkdir(parents=True, exist_ok=True)
    HotFolder(a.server, a.inbox, a.outbox, a.policy, a.risk_threshold).loop(a.interval)


if __name__ == "__main__":
    main()
