# OCR engine benchmark on the B70 host (2x Intel Xeon 6787P, 344 vCPU, AMX) — 2026-11-06

PP-OCR (RapidOCR) on 16 synthetic pages; "8 threads" = 8 pages OCR'd concurrently, one engine per thread.

| Engine / setting | Single page | 8 pages in parallel |
|---|---|---|
| ONNX Runtime, default threads (each engine grabs all 344 vCPU) | 1.60 s | 29.7 pages/min |
| **ONNX Runtime, 8 threads per engine (`RA_OCR_THREADS=8`)** | **0.49 s** | **274.0 pages/min** |
| ONNX Runtime, 4 threads per engine | 0.78 s | 251.6 pages/min |
| OpenVINO 2024.6 (rapidocr_openvino 1.3.25), CPU | 0.30 s | 357.5 pages/min |

Finding: the default ONNX Runtime thread pool oversubscribes a many-core Xeon when pages run in
parallel; capping it to 8 threads per engine gives a 9x OCR speed-up and removes OCR as the pipeline
bottleneck. OpenVINO is faster still (AMX), but this rapidocr_openvino release lacks per-character
boxes and call-time detection settings, which RedactAgent needs for pixel-exact redaction — kept as
a future option.
