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

## Final evaluation — gpt-oss-20b (MXFP4, reasoning low) + Qwen2.5-VL-7B, 2026-11-07

Run once with the final code (commit `72cc4b0`); v3 was used here for the first time. 8 pages in flight,
strict policy, failed pages would count as fully leaked (there were none).

| Corpus | Pages / items | A rules | B + LLM | C + VLM | **D + agentic check** | Clean pages (D) |
|---|---|---|---|---|---|---|
| v1 development | 36 / 582 | 75.4 / 98.6 | 94.0 / 98.9 | 96.0 / 98.5 | **98.5 / 97.8** | 83 % |
| v2 held-out, analysed | 30 / 396 | 59.6 / 92.3 | 94.7 / 95.1 | 95.2 / 95.4 | **96.0 / 93.8** | 63 % |
| **v3 untouched** | 30 / 396 | 59.3 / 93.9 | 94.9 / 96.1 | 95.7 / 95.4 | **96.7 / 94.8** | 60 % |

Recall / precision in %. Median page latency at 8 in flight (v3): OCR 0.8 s, LLM 7.2 s, VLM 2.4 s (in parallel
with the LLM), total 13.7 s.

**What v3 still misses** (13 of 396 items): 10 person names – account-holder names in capitals on bank statements
(4), patient / pharmacist names on Chinese prescription labels (3), parties in court judgments (2), one in a lab
report – plus two quasi-identifiers ("the youngest member of the national para-fencing squad", "the last
blacksmith still working in Lukang old street") and one date of birth. Most false positives (22 of 423 boxes) are
pharmacy addresses on prescription labels (organisation, not personal, data) and VLM signature boxes on a
judgment. These are reported, not fixed: v3 stays a one-shot test set, and any later fix will be validated on v2.

### Runaway reasoning → retry (found on v1 after the first final run)

The benchmark at one page in flight showed a p95 latency of 105 s against a median of 14 s. The raw results
explain it: on two v1 Chinese pages gpt-oss reasoned until the token cap (3,548 completion tokens) and returned no
answer, so the LLM layer contributed **zero** findings on those pages (the agentic check recovered part of it).
The reasoning had fallen into a repetition loop ("Also P1L25 date." hundreds of times).

A detour worth recording: probing that page with `repetition_penalty=1.1` gave normal answers, but a full run whose
retries carried the penalty then **degraded badly** – 12 of 36 v1 pages looped (5.9 pages/min, recall down), and a
sampling-only probe sent right after the penalty probes also looped 4/4. After a clean restart of the text server,
an A/B on v1 gave:

| Retry after a runaway call | Pages / min | C recall / precision | D recall / precision | Pages that looped | Pages with no LLM answer |
|---|---|---|---|---|---|
| sampling only (temperature 0.7) | 22.8 | 97.1 / 98.5 | 99.1 / 97.9 | 1 (rescued by the retry) | 0 |
| sampling + repetition penalty 1.1 | 21.4 | 97.3 / 98.5 | 99.1 / 97.9 | 0 (retry not needed) | 0 |

Requests carrying `repetition_penalty` appear to disturb later decoding on this vLLM XPU build, so the final
retry uses **sampling only** and never sends the penalty (`RA_RETRY_REPETITION_PENALTY=1.0`). The normal path is
unchanged (greedy). Loops are rare on a healthy server (0–2 of 36 pages per run).

The fix was motivated by v1 only. Because it changes the final configuration, all three corpora and the
benchmark were run again (final run 2, `eval/results_b70/`); the first final run is kept in
`eval/results_b70/run1/` and both v3 results are reported.

## Final run 2 — final code (`a53e39c`), clean text-server restart

| Corpus | A rules | B + LLM | C + VLM | **D + agentic check** | Clean pages (D) | Pages / min | Runaway calls (rescued) |
|---|---|---|---|---|---|---|---|
| v1 | 75.4 / 98.6 | 95.4 / 98.9 | 97.3 / 98.5 | **99.0 / 97.8** | 86 % | 20.6 | 2 (2) |
| v2 | 59.6 / 91.9 | 94.7 / 94.9 | 95.2 / 95.1 | **96.2 / 93.8** | 63 % | 17.9 | 0 |
| **v3** | 59.3 / 93.9 | 92.9 / 96.0 | 93.7 / 95.5 | **96.2 / 95.0** | 63 % | 11.3 | 2 (1) |

v3 across the two final runs: recall 96.7 → 96.2, precision 94.8 → 95.0. The difference comes from the random
occurrence of reasoning loops (none in run 1; two in run 2, one not rescued by the retry, which also explains the
lower v3 throughput). This is reported as run-to-run variation; v3 is not used again. Remaining mitigation for an
unrescued loop: the agentic check, the unread-ink check and mandatory human review.

### Throughput and energy — final configuration (`eval/results_b70/bench/`)

gpt-oss-20b + Qwen2.5-VL-7B, full pipeline including the agentic check, 36 pages per level, 2 warm-up pages.

| Pages in flight | Pages / min | Latency p50 | Latency p95 | GPU power (both cards) |
|---|---|---|---|---|
| 1 | 3.3 | 12.7 s | 46.9 s | 263 W |
| 4 | 12.7 | 13.3 s | 37.3 s | 355 W |
| **8** | **24.7** | **14.4 s** | **30.0 s** | **364 W** |
| 16 | 23.4 | 20.6 s | 50.2 s | 334 W |
| 32 | 8.8 | 38.9 s | 194.8 s | 270 W |

Eight pages in flight is the sweet spot (the web app and batch mode default to `RA_WORKERS=8`); beyond 16 the
host-side work and long reasoning tails make throughput collapse, so the queue deliberately caps concurrency.
The p95 at one page in flight fell from 105 s to 47 s with the runaway-reasoning retry.

## 2026-11-07/08 — Reasoning loops at scale: diagnosis, vLLM 0.33, decoding temperature

While recording the demo, the very first page took 114 s: both the greedy call and the sampled retry ran to the
token cap. That started a systematic look at gpt-oss's repetition loops.

**What a loop looks like.** The reasoning repeats a sentence cycle verbatim ("Also the role of the patient is
subject. Also the role of the physician signature is professional. ...", period 20–250 characters) until the
token cap. During some periods the server also returned pure garbage ("!!!!…", the signature of NaN logits).

**Instrumentation.** `RA_LOOP_GUARD_OBSERVE=1` streams every call and records where a periodicity detector
(`llm_client.is_looping`: the tail is one chunk repeated ≥ 3 times) would fire, without cancelling anything;
`RA_LOOP_DUMP` saves the completions. 380 streamed calls on v1+v2 (vLLM 0.26, greedy):

| | Calls |
|---|---|
| detector fired | 30 |
| … loop ended by itself with a complete answer | 23 (most before 1,800 chunks, two after ~3,000) |
| … ran to the token cap | 7 |
| ran to the cap without the detector firing | 0 |
| normal completions: length p50 / p99 / max | 122 / 1,280 / 2,028 chunks |

Cancelling at the first sign of repetition therefore throws away answers the model would have finished:
in two v1+v2 runs it cost 0.4–0.7 recall points. The guard now cancels only a loop that is still running after
2,000 chunks (`RA_LOOP_MIN_CHUNKS`), then retries with sampling (up to 2 retries).

**Degraded periods on vLLM 0.26.** Loops are not independent: in one round of v2, 27 of 111 calls ran to the
cap and 7 returned "!!!!" garbage within three minutes (5.2 pages/min, recall 93.4 %), and the next run on the
same server was still slow (8.7 pages/min). Prefix caching is not the cause (same loop rate with
`--no-enable-prefix-caching`).

**vLLM 0.33.0** (released 2026-11-02; the B70 instance had 0.26.0): same XPU MXFP4 MoE backend, no garbage
episodes and no degraded periods observed, v2 recall higher; greedy decoding still loops sometimes (7 of 402
calls ran to the cap, all on v1).

**Decoding temperature.** OpenAI recommends sampling gpt-oss at temperature 1.0; greedy decoding is what makes it
loop. Observe mode, vLLM 0.33, v1 / v2 recall and precision of the full system (D), two rounds each:

| Text-model decoding | v1 D | v2 D | Pages / min (v1, v2) | Calls that looped / ran to the cap |
|---|---|---|---|---|
| greedy (T = 0) | 98.8 / 98.1, 98.3 / 98.1 | 97.0 / 94.7, 97.2 / 93.0 | 15.0–19.9, 24.0–24.5 | 23 / 7 of 402 |
| T = 0.6 | 98.5 / 97.6, 98.5 / 97.6 | 94.7 / 93.9, 94.9 / 93.5 | 32.6–37.1, 28.3–31.2 | 2 / 0 of 264 |
| T = 1.0 | 98.6 / 97.2, 98.3 / 97.7 | 95.2 / 93.9, 94.4 / 94.6 | 33.1–35.2, 28.8–30.4 | 0 / 0 of 264 |

Sampling removes the loops and raises throughput by ~50 %, but greedy decoding is more thorough on the harder
held-out corpus (+2 recall points on v2).

Greedy decoding **with the loop guard** (new code `1313367`, vLLM 0.33, two rounds):

| | v1 D | v2 D | Pages / min (v1, v2) | Loops cancelled (all rescued) |
|---|---|---|---|---|
| greedy + loop guard | 98.8 / 97.4, 99.0 / 97.9 | 96.7 / 92.5, 97.0 / 93.1 | 22.9–24.6, 23.8–25.1 | 1–2 per corpus run |

**Decision (taken on v1/v2 only, before any further v3 run):**
- *Accuracy mode (default):* vLLM XPU **0.33.0** on both cards, gpt-oss-20b with greedy decoding and the loop
  guard (cancel a loop still running after 2,000 chunks, ≤ 2 sampled retries).
- *Throughput mode:* the same model sampled at temperature 1.0 (`RA_TEMPERATURE=1.0`): no loops, ~50 % more
  pages per minute, ~2 recall points lower on v2. It replaces Qwen3-8B FP8 as the throughput mode (better on
  both speed and accuracy on this stack).

Because this changes the final configuration, v1, v2, v3 and the benchmark are run again (final run 3); runs 1
and 2 stay in the repository and all v3 results are reported.

## Final run 3 — vLLM XPU 0.33.0 on both cards, accuracy mode (greedy + loop guard), 2026-11-07

Code `490c1c1`; both servers restarted on `vllm/vllm-openai-xpu:v0.33.0`; 8 pages in flight. Recall / precision
in %, clean pages = pages with zero leaked items. Final run 2 moved to `eval/results_b70/run2/`.

| Corpus | A rules | B + LLM | C + VLM | **D + agentic check** | Clean pages (D) | Pages / min | Latency p50 / p95 | Loops cancelled |
|---|---|---|---|---|---|---|---|---|
| v1 | 75.4 / 98.6 | 95.5 / 98.9 | 97.3 / 98.5 | **98.5 / 98.4** | 81 % | 22.8 | 14.3 / 49.5 s | 2 (both rescued) |
| v2 | 59.6 / 92.3 | 93.9 / 95.1 | 94.7 / 95.3 | **96.7 / 92.9** | 70 % | 25.8 | 13.7 / 43.6 s | 0 |
| **v3** | 59.3 / 93.4 | 94.4 / 95.9 | 95.5 / 96.1 | **96.7 / 96.0** | 63 % | 21.9 | 15.4 / 36.3 s | 0 |

All v3 results so far (each run once, never used for tuning): run 1 96.7 / 94.8, run 2 96.2 / 95.0 (11.3 pages/min,
one unrescued loop), **run 3 96.7 / 96.0 (21.9 pages/min)**.

### Throughput and energy on vLLM 0.33 (`eval/results_b70/bench/`, `eval/results_b70/fast/bench/`)

Full pipeline including the agentic check, 36 pages per level, board power of both cards from `xpu-smi`.

| Mode | Pages in flight | Pages / min | Latency p50 | Latency p95 | GPU power (both cards) |
|---|---|---|---|---|---|
| accuracy | 1 | 3.4 | 14.8 s | 38.1 s | 263 W |
| accuracy | 4 | 11.6 | 13.0 s | 41.0 s | 329 W |
| accuracy | **8** | **21.0** | **15.2 s** | **39.6 s** | **362 W** |
| accuracy | 16 | 25.5 | 23.4 s | 58.2 s | 347 W |
| accuracy | 32 | 25.9 | 36.0 s | 73.8 s | 337 W |
| throughput (T = 1.0) | 8 | 34.7 | 11.6 s | 21.2 s | 382 W |
| throughput (T = 1.0) | 16 | 42.2 | 18.4 s | 28.2 s | 365 W |

On vLLM 0.26, 32 pages in flight collapsed to 8.8 pages/min; on 0.33 throughput keeps rising to 16–32 in flight.
Interactive review keeps 8 in flight (lowest latency); archive batches can use 16.

### Throughput mode (gpt-oss-20b sampled at T = 1.0), vLLM 0.33 (`eval/results_b70/fast/`)

| Corpus | A rules | C + VLM | **D + agentic check** | Clean pages | Pages / min |
|---|---|---|---|---|---|
| v1 | 75.4 / 98.6 | 96.6 / 98.0 | **97.4 / 97.4** | 69 % | 39.4 |
| v2 | 59.3 / 92.3 | 92.9 / 94.7 | **95.5 / 91.5** | 60 % | 29.9 |
| v3 | 58.8 / 93.0 | 93.7 / 95.8 | **96.0 / 94.5** | 50 % | 32.2 |

The first throughput-mode run (`fast/run1/`) lost one v3 page: the vision model's JSON was cut off at 512 tokens
and the parse error failed the page (v3 D 90.9 / 95.4, the page counted as fully leaked). Until `1313367` the
reasoning allowance had silently been added to the vision calls too, which hid the short budget. Fix (`11caa66`):
1,024 tokens for the vision model and a lenient parser that keeps every complete element and never fails a page.
Accuracy-mode runs never reached the 512-token limit (a truncation would have failed a page), so they are
unaffected. Throughput mode was then run again on all three corpora (table above).

### Recording on the instance (final video)

`scripts/record_b70.py` (web app) and `scripts/record_terminal.py` (real JupyterLab terminal: hardware, both
served models, a **live v3 evaluation**, GPU power) on the final configuration. The terminal recording was taken
twice (the first take showed a JupyterLab notification toast); both live v3 runs are kept in
`eval/results_b70/video_v3_live/`: take 1 96.2 / 95.9, **take 2 (in the video) 96.5 / 94.8**. Together with final
runs 1–3 these are all v3 evaluations ever made; none was used to change the system.
