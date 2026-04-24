# Phase 7 — Behavioral Profiler & Decision Engine

> **Master Plan Reference:** Phase 7 (Behavioral Profiler + Decision Engine)

## What Was Built

### Behavioral Signals

- `inference-service/core/behavioral/signals.py`
  Extracts typing rhythm, dwell time, mouse velocity, mouse curvature, and the final 20-dimensional session vector from browser events.

### Behavioral Profiler

- `inference-service/core/behavioral/profiler.py`
  Maintains per-user behavioral baselines with EMA updates, cosine-distance delta scoring, verdict banding (`LEGITIMATE`, `FORGETFUL_USER`, `HACKER`), and persistence.
- Persistence works with PostgreSQL when `DATABASE_URL` is configured and falls back to local JSON profile storage for smoke tests and local development.

### Decision Engine

- `inference-service/core/engine.py`
  Loads Phase 4-6 artifacts when present, fuses `SNN + LNN + XGBoost + behavioral delta`, applies tree overrides, emits `ThreatVerdict`, and supports model-version hot-swap checks with rollback-on-regression behavior.
- Kafka publishing is callback-friendly so the orchestration layer can publish to `verdicts` and `alerts` without hardwiring the engine to a broker in tests.

### Live Inference Service

- `inference-service/main.py`
  Runs the Phase 7 orchestration as a live FastAPI service, consumes `extracted-features` from Kafka, publishes verdicts and alerts, exposes `/health`, `/analyze`, `/verdicts/latest`, `/alerts/latest`, and `/behavioral/vectorize`, and keeps the model hot-swap monitor running in the background.

### Verification

- `tests/verify_phase7_engine.py`
  Verifies signal extraction, behavioral profile persistence + drift scoring, decision fusion, Kafka-style publishing, and hot-swap rejection when validation F1 regresses.

## Important Logic Notes

- The current Phase 6 XGBoost runtime wrapper is trained on the existing 80-feature contract, so Phase 7 uses score-level fusion across SNN, LNN, XGBoost, and behavioral delta rather than retraining XGBoost on a new 509-dimensional fused vector.
- Fusion uses threat-oriented confidence (`1 - P(BENIGN)`) for the LNN and XGBoost branches so strong benign predictions do not accidentally raise the final attack confidence.
- If trained artifacts are missing, the engine still has a heuristic fallback path. That keeps Phase 7 runnable before the full trained checkpoints are available.
- `models/model_version.json` in this repo currently includes a UTF-8 BOM, so the engine reads model metadata with BOM-safe decoding.

## Checkpoints

### Checkpoint 7A — Local Phase 7 verification

```bash
python tests/verify_phase7_engine.py
```

Expected:

- behavioral signals extract cleanly
- user profiles persist and reload
- normal session returns `LEGITIMATE`
- attack session returns `HACKER`
- regressed model metadata is rejected during hot-swap

### Checkpoint 7B — Live service verification

```bash
python tests/verify_phase7_live_service.py
```

Expected:

- inference service routes respond successfully
- manual `/analyze` calls produce verdicts
- latest verdict endpoints update immediately
- Kafka-path feature messages can be processed by the live runtime

## Next

Phase 8 can now consume Phase 7 verdicts and behavioral updates for the feedback loop and retraining orchestrator.
