| Concurrent pages | Pages / min | Latency p50 | Latency p95 | GPU power (both cards) | Pages / kWh |
|---|---|---|---|---|---|
| 1 | 5.8 | 9.8 s | 12.9 s | 301 W | 1,161 |
| 4 | 18.6 | 11.4 s | 21.1 s | 343 W | 3,263 |
| 8 | 21.3 | 21.3 s | 32.4 s | 307 W | 4,164 |
| 16 | 22.0 | 36.6 s | 59.1 s | 263 W | 5,026 |
| 32 | 15.7 | 120.9 s | 134.5 s | 218 W | 4,337 |

Baseline (2026-11-06): Qwen3-8B BF16 + Qwen2.5-VL-7B BF16, eager mode, OCR engines unrestricted (all 344 threads each).
Throughput plateaus at ~22 pages/min while GPU power falls: the bottleneck is CPU-side OCR contention, not the B70.
