# Reasoning-loop experiments (2026-11-07/08)

Raw outputs behind the "Reasoning loops at scale" section of [docs/STAGE2_LOG.md](../../docs/STAGE2_LOG.md).
Each directory holds per-page raw results and metrics for v1 (`synthetic`) and v2 (`synthetic_v2`); v3 was not used.

| Directory | Server | Text-model decoding | Loop guard |
|---|---|---|---|
| guard_nopc/ | vLLM 0.26, prefix caching off | greedy | cancel at first repetition |
| guard_pc/ | vLLM 0.26 | greedy | cancel at first repetition |
| observe/r1, r2 | vLLM 0.26 | greedy | observe only (never cancels) |
| abguard/ | vLLM 0.26 (degraded period) | greedy | off (`RA_STREAM_LOOP_GUARD=0`) |
| observe033/r1, r2 | vLLM 0.33 | greedy | observe only |
| t10_033/r1, r2 | vLLM 0.33 | sampled, T = 1.0 | observe only |
| t06_033/r1, r2 | vLLM 0.33 | sampled, T = 0.6 | observe only |
| g0guard_033/r1, r2 | vLLM 0.33 | greedy | cancel loops still running after 2,000 tokens (final) |

Detector calibration on the saved completions: `python scripts/loop_calibration.py '<dump dir>/*.txt'`
(completions are saved with `RA_LOOP_GUARD_OBSERVE=1 RA_LOOP_DUMP=<dir>`).
