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

_in progress — see `eval/tune/`_
