# Model Placeholder Handoff

This file explains exactly which parts of the current loop are real, which parts are temporary placeholders, and how later Phase 3 model work plus Phase 8 retraining should plug in without breaking the user flow.

## Current Rule

Do not redesign the frontend/backend loop while working on models.

The loop is already fixed around:

- Phase 9 API gateway
- Phase 10 sandbox orchestration
- Phase 11 frontend flow

Future model and retraining work should plug into that loop, not replace it.

## What Is Already Stable

Stable integration points:

- `POST /api/behavioral`
- `POST /api/bank/login`
- `POST /api/bank/transfer`
- `POST /api/analyze`
- `GET /api/verdicts/current`
- `GET /api/verdicts/{user_id}`
- `GET /api/sandbox/{session_id}/replay`
- `GET /api/alerts`
- `GET /api/model/version`

Stable verdict shape:

- `session_id`
- `user_id`
- `source_ip`
- `snn_score`
- `lnn_class`
- `xgb_class`
- `behavioral_delta`
- `confidence`
- `verdict`
- `timestamp`
- `model_version`
- `features_dict`

Do not casually rename these fields.

## What Is Placeholder Right Now

These areas are intentionally temporary until Phase 3 model quality and Phase 8 retraining are done:

### Model confidence realism

Current outputs are valid structurally, but some decisions still rely on:

- heuristic feature construction for portal flows
- forced escalation for honeypot/web-attack patterns
- synthetic or fallback probabilities when trained artifacts are absent

### Portal-generated flow features

For portal-originated login/transfer activity, the gateway currently builds lightweight surrogate flow features before calling the engine.

That is acceptable for now.

Later, if you connect full feature extraction from ingestion/feature-service for browser-originated actions, keep the same verdict contract.

### Model version metadata

The frontend already consumes:

- `version`
- `versions`
- `validationF1`
- `lastRetrainedAt`

If retraining later changes the underlying version file, preserve this response shape.

## Phase 3 Integration Guidance

When improving the actual model layer:

1. keep `DecisionEngine.analyze_session()` as the single inference entry point
2. keep the `ThreatVerdict` shape unchanged
3. keep Phase 9 routes calling that engine instead of bypassing it
4. treat frontend pages as clients of verdict data only, not of model internals

This means model work should improve:

- `snn_score`
- `lnn_class`
- `xgb_class`
- `confidence`
- `behavioral_delta`

without changing how the portal or dashboard talk to the backend.

## Phase 8 Retraining Guidance

When the retraining orchestrator is built:

### Inputs it should consume

- feedback samples from `feedback-service`
- model version file
- existing trained artifact locations

### Outputs it must preserve

- updated model artifact paths
- updated `model_version.json`
- backward-compatible `/api/model/version` payload

### What retraining must not break

- live login flow
- live transfer flow
- verdict polling
- alert feed payloads
- sandbox replay flow

Retraining is allowed to improve decision quality.
It is not allowed to change the public API contract.

## Placeholder-to-Real Swap Checklist

When swapping placeholders for real model behavior later:

1. verify `python tests/verify_phase9_api.py`
2. verify `python tests/verify_phase9_http_sandbox_flow.py`
3. verify frontend builds:
   - `simulation_portal`
   - `dashboard`
4. check that `/api/model/version` still matches the dashboard expectation
5. confirm that a HACKER verdict still results in sandbox activation

## Recommended Rule For Future Work

If a future model or retraining change breaks frontend flow, treat that as a regression in the model integration, not as a reason to rewrite Phase 9 or Phase 11.

## When You Ask Later

If you ask me to continue model integration or retraining later, tell me:

`refer Docs/MODEL_PLACEHOLDER_HANDOFF.md before changing model or retraining wiring`
