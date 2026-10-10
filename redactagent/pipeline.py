"""End-to-end pipeline: ingest -> OCR -> rules + LLM + VLM -> merge -> policy -> redact -> audit."""

from __future__ import annotations

import io
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image

from . import config, render
from .coverage import unread_regions
from . import policy as policy_mod
from .audit import AuditLog, sha256_bytes
from .detectors import llm as llm_det
from .detectors import rules as rule_det
from .detectors import vision as vis_det
from .llm_client import ModelClient
from .ocr import run_ocr
from .schema import Finding, OcrLine

ALL_LAYERS = ("rules", "llm", "vlm")


def load_pages(data: bytes, filename: str, dpi: int = config.RENDER_DPI) -> list[Image.Image]:
    if filename.lower().endswith(".pdf") or data[:4] == b"%PDF":
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(data)
        return [pdf[i].render(scale=dpi / 72).to_pil().convert("RGB") for i in range(len(pdf))]
    return [Image.open(io.BytesIO(data)).convert("RGB")]


@dataclass
class PageResult:
    index: int
    image: Image.Image
    lines: list[OcrLine]
    findings: list[Finding] = field(default_factory=list)


@dataclass
class Job:
    id: str
    filename: str
    policy_id: str
    layers: tuple[str, ...]
    status: str = "queued"
    stage: str = ""
    progress: float = 0.0
    error: str = ""
    doc_type: str = ""
    input_sha256: str = ""
    pages: list[PageResult] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
    tokens: dict[str, int] = field(default_factory=dict)
    warnings: list[dict] = field(default_factory=list)  # ink that OCR did not read -> reviewer must check
    created: float = field(default_factory=time.time)

    @property
    def findings(self) -> list[Finding]:
        return [f for p in self.pages for f in p.findings]

    def summary(self) -> dict:
        fs = self.findings
        by_cat: dict[str, int] = {}
        for f in fs:
            by_cat[f.category] = by_cat.get(f.category, 0) + 1
        return {
            "id": self.id, "filename": self.filename, "policy": self.policy_id, "layers": list(self.layers),
            "status": self.status, "stage": self.stage, "progress": round(self.progress, 3), "error": self.error,
            "doc_type": self.doc_type, "pages": len(self.pages), "n_findings": len(fs), "by_category": by_cat,
            "timings": {k: round(v, 3) for k, v in self.timings.items()}, "tokens": self.tokens,
            "input_sha256": self.input_sha256, "warnings": self.warnings,
        }


def _overlap_ratio(a: tuple[int, int], b: tuple[int, int]) -> float:
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    return inter / max(1, min(a[1] - a[0], b[1] - b[0]))


def merge_text_hits(page: int, lines: list[OcrLine], rhits: list[rule_det.RuleHit], lhits: list[llm_det.LlmHit],
                    next_id: Callable[[], str]) -> list[Finding]:
    by_id = {ln.id: ln for ln in lines}
    out: list[Finding] = []
    for h in rhits:
        ln = by_id[h.line_id]
        out.append(Finding(next_id(), page, h.category, ln.text[h.start:h.end], ln.span_bbox(h.start, h.end), ["rule"],
                           h.confidence, None, h.reason, h.line_id, (h.start, h.end)))
    for h in lhits:
        ln = by_id[h.line_id]
        twin = next((f for f in out if f.line_id == h.line_id and _overlap_ratio(f.span, (h.start, h.end)) > 0.5), None)
        if twin is not None:
            if "llm" not in twin.sources:
                twin.sources.append("llm")
            twin.role = twin.role or h.role
            twin.confidence = min(0.99, twin.confidence + 0.05)
            # the LLM sees the whole page: let it upgrade a generic date to a birth date
            if twin.category == "DATE" and h.category == "DATE_OF_BIRTH":
                twin.category = "DATE_OF_BIRTH"
            # grow the span if the LLM captured more of the entity (e.g. full address)
            s, e = min(twin.span[0], h.start), max(twin.span[1], h.end)
            if (s, e) != twin.span:
                twin.span, twin.text, twin.bbox = (s, e), ln.text[s:e], ln.span_bbox(s, e)
            continue
        out.append(Finding(next_id(), page, h.category, h.text, ln.span_bbox(h.start, h.end), ["llm"], 0.8, h.role,
                           h.reason or "contextual PII (LLM)", h.line_id, (h.start, h.end)))
    return out


class Pipeline:
    def __init__(self, text_client: ModelClient | None = None, vision_client: ModelClient | None = None,
                 audit: AuditLog | None = None):
        self.text_client = text_client or ModelClient(config.TEXT_MODEL, think=False)
        self.vision_client = vision_client or ModelClient(config.VISION_MODEL, base_url=config.VISION_BASE_URL, think=None)
        self.audit = audit or AuditLog(config.RUNS_DIR / "audit.jsonl")
        self.policies = policy_mod.load_policies()

    def new_job(self, filename: str, policy_id: str, layers=ALL_LAYERS) -> Job:
        return Job(uuid.uuid4().hex[:10], filename, policy_id, tuple(layers))

    def run(self, job: Job, data: bytes, progress: Callable[[Job], None] | None = None) -> Job:
        def stage(name: str, frac: float):
            job.stage, job.progress = name, frac
            if progress:
                progress(job)

        counter = iter(range(1, 10**6))

        def next_id() -> str:
            return f"f{next(counter)}"

        try:
            job.status = "running"
            job.input_sha256 = sha256_bytes(data)
            self.audit.append("ingest", job.id, filename=job.filename, sha256=job.input_sha256, policy=job.policy_id,
                              layers=list(job.layers))
            t = time.perf_counter()
            stage("Rendering pages", 0.02)
            images = load_pages(data, job.filename)
            job.timings["ingest"] = time.perf_counter() - t
            n = len(images)
            for i, img in enumerate(images):
                base = i / n
                span = 1 / n
                stage(f"Page {i + 1}/{n}: OCR (PP-OCR, ONNX)", base + span * 0.05)
                t = time.perf_counter()
                lines = run_ocr(np.asarray(img)[:, :, ::-1].copy(), page=i)
                job.timings["ocr"] = job.timings.get("ocr", 0) + time.perf_counter() - t
                page = PageResult(i, img, lines)
                job.pages.append(page)

                rhits: list[rule_det.RuleHit] = []
                if "rules" in job.layers:
                    stage(f"Page {i + 1}/{n}: rule engine (regex + checksums)", base + span * 0.15)
                    t = time.perf_counter()
                    rhits = rule_det.detect(lines)
                    job.timings["rules"] = job.timings.get("rules", 0) + time.perf_counter() - t
                lhits: list[llm_det.LlmHit] = []
                if "llm" in job.layers:
                    stage(f"Page {i + 1}/{n}: contextual LLM ({self.text_client.model})", base + span * 0.2)
                    # the LLM reads the full text (masking rule hits hurt its recall in tests)
                    lhits, doc_type, st = llm_det.detect(lines, self.text_client)
                    job.doc_type = job.doc_type or doc_type
                    job.timings["llm"] = job.timings.get("llm", 0) + st.seconds
                    job.tokens["llm_prompt"] = job.tokens.get("llm_prompt", 0) + st.prompt_tokens
                    job.tokens["llm_completion"] = job.tokens.get("llm_completion", 0) + st.completion_tokens
                page.findings = merge_text_hits(i, lines, rhits, lhits, next_id)

                stage(f"Page {i + 1}/{n}: visual identifiers ({self.vision_client.model if 'vlm' in job.layers else 'colour check'})",
                      base + span * 0.7)
                t = time.perf_counter()
                vhits, vst = vis_det.detect(img, self.vision_client if "vlm" in job.layers else None)
                job.timings["vlm"] = job.timings.get("vlm", 0) + (time.perf_counter() - t)
                job.tokens["vlm_prompt"] = job.tokens.get("vlm_prompt", 0) + vst.prompt_tokens
                for h in vhits:
                    srcs = h.source.split("+")
                    page.findings.append(Finding(next_id(), i, h.category, h.category.lower(), h.bbox, srcs, h.confidence,
                                                 "subject" if h.category == "FACE_PHOTO" else None, h.reason))
                covered = [ln.bbox for ln in lines] + [h.bbox for h in vhits]
                for bb in unread_regions(img, covered):
                    job.warnings.append({"page": i, "bbox": bb, "reason": "text-like ink not read by OCR - check manually"})
            self.apply_policy(job)
            job.timings["total"] = sum(v for k, v in job.timings.items() if k != "total")
            job.status, job.stage, job.progress = "done", "Ready for review", 1.0
            by_src: dict[str, int] = {}
            for f in job.findings:
                for s in f.sources:
                    by_src[s] = by_src.get(s, 0) + 1
            self.audit.append("detect", job.id, n_pages=len(job.pages), n_findings=len(job.findings), by_source=by_src,
                              unread_regions=len(job.warnings),
                              doc_type=job.doc_type, seconds=round(job.timings["total"], 2),
                              models={"text": self.text_client.model if "llm" in job.layers else None,
                                      "vision": self.vision_client.model if "vlm" in job.layers else None})
        except Exception as e:  # surface errors to the UI instead of crashing the worker
            job.status, job.error = "error", f"{type(e).__name__}: {e}"
            self.audit.append("error", job.id, error=job.error)
        if progress:
            progress(job)
        return job

    def apply_policy(self, job: Job, policy_id: str | None = None) -> None:
        if policy_id:
            job.policy_id = policy_id
        policy_mod.apply(self.policies[job.policy_id], job.findings)

    def export(self, job: Job, out_dir: Path | None = None, actor: str = "reviewer") -> dict:
        out_dir = out_dir or (config.RUNS_DIR / job.id)
        out_dir.mkdir(parents=True, exist_ok=True)
        pages = [render.redact_page(p.image, p.findings) for p in job.pages]
        pdf = render.to_pdf(pages)
        (out_dir / "redacted.pdf").write_bytes(pdf)
        for p, im in zip(job.pages, pages):
            im.save(out_dir / f"redacted_p{p.index + 1}.png")
        text = deidentified_text(job)
        (out_dir / "deidentified.txt").write_text(text, encoding="utf-8")
        report = {"job": job.summary(), "policy": self.policies[job.policy_id].to_dict(),
                  "findings": [f.to_dict() for f in job.findings]}
        (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        rejected = [f.id for f in job.findings if not f.accepted]
        kept = [f.id for f in job.findings if f.accepted and f.action == "keep"]
        entry = self.audit.append("export", job.id, actor=actor, policy=job.policy_id, output_sha256=sha256_bytes(pdf),
                                  redacted=sum(1 for f in job.findings if f.accepted and f.action != "keep"),
                                  kept_by_policy=len(kept), rejected_by_reviewer=rejected)
        return {"dir": str(out_dir), "pdf_sha256": entry["data"]["output_sha256"], "audit_hash": entry["hash"]}


def deidentified_text(job: Job) -> str:
    """OCR text with every accepted finding replaced by its label - ready for downstream NLP/research."""
    out = []
    for p in job.pages:
        spans: dict[str, list[Finding]] = {}
        for f in p.findings:
            if f.line_id and f.accepted and f.action != "keep":
                spans.setdefault(f.line_id, []).append(f)
        for ln in p.lines:
            s = ln.text
            for f in sorted(spans.get(ln.id, []), key=lambda f: -f.span[0]):
                rep = f.label or f"[{f.category}]"
                s = s[:f.span[0]] + rep + s[f.span[1]:]
            out.append(s)
        out.append("")
    return "\n".join(out)
