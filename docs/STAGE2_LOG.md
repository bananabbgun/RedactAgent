# Stage II engineering log — RedactAgent on 2x Intel Arc Pro B70

Environment: Intel Cloud Services instance `asus-hackathon-07` — 2x Intel Arc Pro B70 32GB, 2x Intel Xeon 6787P
(344 vCPU, AMX), 251 GB RAM, Ubuntu 26.04, `vllm/vllm-openai-xpu:v0.26.0`. One model server per card
(`ZE_AFFINITY_MASK=0` text LLM, `=1` vision-language model), launched with `deploy/b70/up.sh`.

All numbers below are measured on that machine unless stated otherwise. Raw outputs live in `eval/results_b70/`
and `eval/tune/`.

## 2026-11-06 — Bring-up and baseline

- **Port.** The laptop code ran unchanged against vLLM (OpenAI-compatible API, JSON-schema decoding,
  image input). The only deployment detail that mattered: the container entry point must source oneAPI
  (`/opt/intel/oneapi/setvars.sh`) or vLLM cannot detect the XPU.
- **Accuracy parity.** Same models as the laptop (Qwen3-8B + Qwen2.5-VL-7B), v1 corpus (36 pages, 582 PII
  items): recall 97.8 %, precision 97.1 % — identical to the laptop.
- **Throughput.** 23.3 pages/min with 8 pages in flight vs ~2 pages/min on the laptop (~11x), before any tuning.
  The LLM and VLM layers of a page now run concurrently because each model owns a card.

## Concurrency sweep → OCR was the bottleneck

| Pages in flight | 1 | 4 | 8 | 16 | 32 |
|---|---|---|---|---|---|
| Pages / min | 5.8 | 18.6 | 21.3 | 22.0 | 15.7 |
| GPU power, both cards | 301 W | 343 W | 307 W | 263 W | 218 W |

Throughput plateaued while GPU power *fell*: the cards were waiting. Per-stage timing showed OCR at 10.5 s/page
under load vs 1.3 s alone. Cause: every ONNX Runtime OCR engine spawned a thread per vCPU (344), so eight
concurrent pages oversubscribed the CPUs.

**Fix:** `RA_OCR_THREADS=8` (8 threads per OCR engine). OCR alone: 29.7 → 274 pages/min (9x); 0.49 s/page.
OpenVINO on the Xeon's AMX reached 357 pages/min, but the available rapidocr_openvino build lacks the
per-character boxes RedactAgent needs for pixel-exact redaction — noted as future work.
Details: `eval/results_b70/OCR_BENCH.md`.

## XPU graph mode — not usable on this stack

`VLLM_XPU_ENABLE_XPU_GRAPH=1` without `--enforce-eager` failed during graph capture with
`UR_RESULT_ERROR_OUT_OF_RESOURCES`, at both 0.85 and 0.70 GPU memory utilisation. All configurations use eager mode.

## Held-out evaluation (v2) and agentic verifier

The v1 corpus was used while writing prompts and rules, so it flatters the system. v2 adds five document types
never used in development (lab report, prescription label, bank statement, court judgment, referral letter),
quasi-identifier phrasings that appear in no prompt, and phone-photo capture (perspective, uneven light, JPEG 60)
on half of the pages.

First v2 run (Qwen3-8B): recall **84.1 %**, precision **87.5 %** — a real generalisation gap.
Error analysis → generic fixes (no document-specific rules):

- dates followed by a time; accession / specimen numbers; more form-field labels; court-judgment party lines
- organisation phone numbers and addresses (letterheads, hotlines) are not personal data
- whitespace-insensitive propagation of names to repeated mentions (OCR drops spaces)
- quasi-identifiers must carry a uniqueness cue (only / sole / last / 唯一 / 現任 / captain ...)
- one ground-truth bug in the v2 generator (bank statement period-end date was unlabelled)

The **agentic re-identification check** (an adversarial LLM pass over the redacted text) recovers names and
quasi-identifiers the detectors miss. Its first version over-flagged (ages, durations, form labels, job histories);
plausibility checks and a uniqueness cue for auto-accepting quasi-identifiers fixed that.

| Qwen3-8B | v1 recall / precision | v2 recall / precision |
|---|---|---|
| detectors only (C), before fixes | 97.6 / 97.7 | 84.1 / 87.5 |
| + agentic check (D), before fixes | 98.3 / 94.7 | 90.5 / 85.4 |
| detectors only (C), after round-1 fixes | 97.8 / 98.7 | 88.9 / 91.3 |
| + agentic check (D), after round-1 fixes | 98.3 / 98.2 | 92.9 / 88.8 |

Because v2 has now been used for error analysis, the final numbers are reported on **v3**: the same five
document types with a fresh random seed (`data/synthetic_v3`), generated before any v3 result was seen.

## Model sweep (text model on card 0; vision model fixed: Qwen2.5-VL-7B)

All runs: round-1 fixes, agentic check on, `RA_OCR_THREADS=8`, 8 pages in flight, eager mode.
Throughput includes the agentic pass (a second LLM call per page).

| Config (card 0) | v1 pages/min | v1 recall / precision (D) | v2 pages/min | v2 recall / precision (D) |
|---|---|---|---|---|
| T0 Qwen3-8B BF16 | 15.7 | 98.3 / 98.2 | 16.8 | 92.9 / 88.8 |
| T1 Qwen3-8B BF16 + XPU graph | — | failed: UR_RESULT_ERROR_OUT_OF_RESOURCES | — | — |
| **T2 Qwen3-8B FP8 (online quant.)** | **27.5** | **98.5 / 98.3** | **27.4** | **94.4 / 90.2** |
| T3 Qwen3-14B FP8 | 29.1 | 98.1 / 98.4 | 21.5 | 96.2 / 90.6 |
| T4 Qwen3-30B-A3B GPTQ-Int4 | 16.6 | 98.8 / 97.3 | 20.5 | 96.0 / 89.0 |
| T5 gpt-oss-20b | 15.4 | invalid (34/36 pages failed) | 16.2 | invalid (30/30 pages failed) |

FP8 weights halve the bytes read per generated token (decoding is memory-bandwidth bound): +75 % throughput
with no measurable accuracy loss.

Without the agentic check (C) on v2: 8B FP8 88.9 / 92.7, 14B FP8 **94.2 / 93.8**, 30B-A3B 93.7 / 92.0 – the larger
models close most of the held-out gap on their own.

**An evaluation bug the sweep exposed.** gpt-oss-20b "scored" 100 % on v1 – because only 2 of 36 pages
succeeded and the harness silently excluded failed pages. gpt-oss always reasons before answering; with a
1024-token budget the reasoning consumed everything and the answer came back empty. Fixes: the harness now
counts a failed page as fully missed and reports `failed_docs` (throughput counts successes only), and the client
supports `RA_REASONING_EFFORT` with an extra reasoning-token allowance. All candidates are re-run on the latest
code (round-2 fixes) in a second sweep (`eval/tune3/`).

## Model sweep 2 — latest code, failure-aware scoring (`eval/tune3/`)

| Text model (card 0) | Pages / min (v1+v2) | v1 recall / precision (D) | v2 detectors only (C) | v2 + agentic check (D) | v2 EN / ZH recall |
|---|---|---|---|---|---|
| **gpt-oss-20b, reasoning low (MXFP4)** | 19.6 | 98.5 / 98.2 | 92.4 / 95.5 | **95.5 / 94.2** | 95.1 / 96.2 |
| Qwen3-14B FP8 | 27.7 | 96.9 / 98.7 | 93.4 / 94.4 | 94.7 / 91.3 | 93.9 / 96.2 |
| Qwen3-8B FP8 | 28.1 | 98.3 / 97.8 | 88.4 / 93.9 | 92.9 / 91.4 | 91.7 / 95.5 |
| Qwen3-30B-A3B GPTQ-Int4 | 17.5 | 98.5 / 97.4 | 92.9 / 93.1 | 94.7 / 89.6 | 94.3 / 95.5 |

No configuration had a failed page. vLLM runs gpt-oss with its native XPU MXFP4 MoE kernel.
**Final choice: gpt-oss-20b** (accuracy mode, default in `deploy/b70/up.sh`); Qwen3-8B FP8 is the
throughput mode. Single runs; differences of about one point are within run-to-run noise, so the decision rests
on gpt-oss leading on recall, precision and false positives at the same time.
