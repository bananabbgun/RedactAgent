"""FastAPI server: upload -> background detection -> human review -> export.

Runs entirely on the local machine (bind to 127.0.0.1 or the LAN of the B70 host);
no request ever leaves the premises.

    python -m redactagent.server            # http://127.0.0.1:8080
"""

from __future__ import annotations

import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, render
from .pipeline import ALL_LAYERS, Job, Pipeline
from .schema import CATEGORIES

WEB = config.ROOT / "web"
app = FastAPI(title="RedactAgent", version="0.1.0")
pipe = Pipeline()
jobs: dict[str, Job] = {}
executor = ThreadPoolExecutor(max_workers=1)  # one GPU, one document at a time; the queue keeps order
_lock = threading.Lock()

app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    return (WEB / "index.html").read_text(encoding="utf-8")


@app.get("/api/info")
def info():
    return {
        "backend": config.BACKEND,
        "text_model": pipe.text_client.model, "vision_model": pipe.vision_client.model,
        "text_model_online": pipe.text_client.ping(), "vision_model_online": pipe.vision_client.ping(),
        "categories": {k: {"name": v[0], "color": v[1]} for k, v in CATEGORIES.items()},
        "policies": [p.to_dict() for p in pipe.policies.values()],
        "layers": list(ALL_LAYERS),
    }


@app.get("/api/samples")
def samples():
    files = sorted(p.name for p in config.SAMPLES_DIR.glob("*") if p.suffix.lower() in (".png", ".jpg", ".pdf"))
    return {"samples": files}


@app.get("/api/samples/{name}")
def sample_file(name: str):
    p = (config.SAMPLES_DIR / name).resolve()
    if p.parent != config.SAMPLES_DIR.resolve() or not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


def _submit(filename: str, data: bytes, policy: str, layers: list[str]) -> Job:
    if policy not in pipe.policies:
        raise HTTPException(400, f"unknown policy {policy}")
    job = pipe.new_job(filename, policy, [l for l in layers if l in ALL_LAYERS])
    with _lock:
        jobs[job.id] = job
    executor.submit(pipe.run, job, data)
    return job


@app.post("/api/jobs")
async def create_job(file: UploadFile | None = File(None), sample: str | None = Form(None),
                     policy: str = Form("strict"), layers: str = Form(",".join(ALL_LAYERS))):
    if file is not None:
        data, name = await file.read(), file.filename or "upload"
    elif sample:
        p = (config.SAMPLES_DIR / sample).resolve()
        if p.parent != config.SAMPLES_DIR.resolve() or not p.exists():
            raise HTTPException(404, "sample not found")
        data, name = p.read_bytes(), p.name
    else:
        raise HTTPException(400, "file or sample required")
    job = _submit(name, data, policy, layers.split(","))
    return job.summary()


def _get(job_id: str) -> Job:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = _get(job_id)
    out = job.summary()
    if job.status == "done":
        out["findings"] = [f.to_dict() for f in job.findings]
        out["page_sizes"] = [list(p.image.size) for p in job.pages]
    return out


@app.get("/api/jobs/{job_id}/page/{n}.png")
def page_image(job_id: str, n: int, view: str = "original"):
    job = _get(job_id)
    if n < 0 or n >= len(job.pages):
        raise HTTPException(404)
    p = job.pages[n]
    img = render.redact_page(p.image, p.findings) if view == "redacted" else p.image
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


class Review(BaseModel):
    decisions: dict[str, bool] = {}
    policy: str | None = None
    reviewer: str = "reviewer"


@app.post("/api/jobs/{job_id}/review")
def review(job_id: str, body: Review):
    job = _get(job_id)
    changed = []
    by_id = {f.id: f for f in job.findings}
    for fid, acc in body.decisions.items():
        if fid in by_id and by_id[fid].accepted != acc:
            by_id[fid].accepted = acc
            changed.append({"id": fid, "accepted": acc, "category": by_id[fid].category})
    if body.policy and body.policy != job.policy_id:
        if body.policy not in pipe.policies:
            raise HTTPException(400, "unknown policy")
        pipe.apply_policy(job, body.policy)
        pipe.audit.append("policy_change", job.id, actor=body.reviewer, policy=body.policy)
    if changed:
        pipe.audit.append("review", job.id, actor=body.reviewer, changes=changed)
    return {"findings": [f.to_dict() for f in job.findings], "policy": job.policy_id}


@app.post("/api/jobs/{job_id}/export")
def export(job_id: str, reviewer: str = "reviewer"):
    job = _get(job_id)
    if job.status != "done":
        raise HTTPException(409, "job not finished")
    return pipe.export(job, actor=reviewer)


@app.get("/api/jobs/{job_id}/download/{name}")
def download(job_id: str, name: str):
    _get(job_id)
    if name not in ("redacted.pdf", "report.json", "deidentified.txt"):
        raise HTTPException(404)
    p = config.RUNS_DIR / job_id / name
    if not p.exists():
        raise HTTPException(404, "export first")
    return FileResponse(p, filename=f"{Path(jobs[job_id].filename).stem}_{name}")


@app.get("/api/audit")
def audit(job: str | None = None):
    return {"verify": pipe.audit.verify(), "entries": pipe.audit.entries(job)[-200:]}


def main():
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="warning")


if __name__ == "__main__":
    main()
