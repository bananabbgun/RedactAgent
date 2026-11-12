# Integrating RedactAgent into a hospital's systems

RedactAgent runs on one 2x Arc Pro B70 host inside the hospital network (`deploy/b70/up.sh`). It never calls out
to the internet. There are two ways to connect it to existing systems; both keep a person in the loop.

```
 records system / IRB portal / scanner
          │  drop file                      │  HTTP (REST)
          ▼                                 ▼
   inbox/ ──► hot folder ──────────► RedactAgent server (127.0.0.1:8080) ◄── reviewer's browser
                  │                        │  OCR · rules · LLM (B70 #0) · VLM (B70 #1) · agentic check
                  ▼                        ▼
   outbox/pending_review/<doc>.json   review ticket: link, priority, reasons
   outbox/released/<doc>_redacted.pdf released only after a recorded human export (audit log)
```

## 1. Hot folder (no code on the hospital side)

```bash
python -m redactagent.hotfolder --inbox /srv/redact/inbox --outbox /srv/redact/outbox --policy research
```

| Step | What happens |
|---|---|
| A PDF / image appears in `inbox/` | submitted once its size is stable; original moved to `inbox/submitted/` |
| Detection finished | `outbox/pending_review/<doc>.json`: review link (`/?job=<id>`), **priority** (`full` / `standard`) and the reasons: re-identification risk ≥ threshold, ink the OCR did not read, unconfirmed suggestions |
| Reviewer approves and exports in the browser | burned-in `…_redacted.pdf` and `…_report.json` copied to `outbox/released/`, ticket removed |

The release step is triggered only by an `export` event in the hash-chained audit log, so nothing leaves without a
reviewer. State survives restarts (`outbox/.hotfolder_state.json`).

## 2. REST API

Interactive documentation of every endpoint: `http://<host>:8080/docs` (FastAPI / OpenAPI).

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/jobs` (`file`, `policy`) | submit one document → job id |
| GET | `/api/jobs/{id}` | status, findings with source and confidence, risk score, warnings |
| POST | `/api/jobs/{id}/review` | accept / reject findings, switch policy (recorded with the reviewer's name) |
| POST | `/api/jobs/{id}/export` | burn in, write PDF + de-identified text + JSON report, append to the audit log |
| GET | `/api/jobs/{id}/download/{redacted.pdf\|report.json\|deidentified.txt}` | results |
| POST | `/api/batches` | many documents at once (8–16 in flight on the B70 host) |
| GET | `/api/audit?job={id}` | audit entries and chain verification |
| GET | `/api/system` | GPU power / VRAM, served models (monitoring) |

```bash
JOB=$(curl -s -F file=@chart.pdf -F policy=research http://127.0.0.1:8080/api/jobs | jq -r .id)
curl -s http://127.0.0.1:8080/api/jobs/$JOB | jq '{status, n_findings, risk: .risk.score}'
curl -s -X POST "http://127.0.0.1:8080/api/jobs/$JOB/export?reviewer=records-office"
curl -s -o chart_redacted.pdf http://127.0.0.1:8080/api/jobs/$JOB/download/redacted.pdf
```

## 3. Policies

Purpose policies are YAML files in `policies/` (research / IRB, court filing, public release, strict). A hospital's
privacy officer can copy one and change actions per category and role (redact, pseudonymise consistently, keep
the year only, keep) without touching code.

## 4. Security notes

- The web UI and both model servers bind to `127.0.0.1`. Expose the UI through the hospital's reverse proxy with
  its single sign-on; reviewer names in the audit log then come from the proxy.
- The audit log (`runs/audit.jsonl`) chains SHA-256 hashes of every submission, review decision and export
  (input hash → output hash), so any later edit is detectable (`GET /api/audit` verifies the chain).
- Uploaded documents and results stay under `runs/` on the host; retention is the hospital's policy.
