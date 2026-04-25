# Phase 9 API Reference

This document is the working contract for the FastAPI gateway layer in `inference-service/main.py`.

It exists to keep Phase 9 stable while model work, frontend integration, sandbox wiring, and later retraining continue independently.

## Scope

Phase 9 owns:

- analyst-facing API compatibility for the dashboard
- bank-facing API routes for the simulation portal
- behavioral event intake
- verdict lookup endpoints
- sandbox orchestration hooks
- placeholder behavior when the sandbox gateway is not reachable yet

Phase 9 does not own:

- retraining orchestration
- Kubernetes deployment
- red-team automation

## Auth Rules

API auth is controlled by `API_KEY`.

- If `API_KEY` is unset: auth is disabled for local/dev use
- If `API_KEY` is set: all HTTP routes require `X-API-Key: <value>`
- Exempt routes:
  - `/`
  - `/health`
  - `/docs`
  - `/redoc`
  - `/openapi.json`

Application login is separate from API auth.

- Bank login uses `POST /api/bank/login`
- It validates only the NovaTrust demo accounts
- Invalid credentials return a normal JSON denial payload instead of exposing account-existence details

## Demo Accounts

- `test@novatrust.com` / `password123` -> `alice`
- `normal2@novatrust.com` / `secure456` -> `bob`
- `admin@novatrust.com` / `Admin@2024!` -> `carol`

## Analyst Routes

### `GET /health`

Returns service liveness and runtime state.

```json
{
  "status": "ok",
  "timestamp": 1714000000.0,
  "kafka_consumer_connected": false,
  "kafka_producer_connected": false,
  "processed_messages": 12,
  "model_version": "0.0.3",
  "latest_verdict": null,
  "database_enabled": false
}
```

### `GET /api/stats`

Dashboard stats payload.

```json
{
  "totalTransactions": 12,
  "hackerDetections": 3,
  "avgRiskScore": 47.21,
  "liveAlerts": 3,
  "legitimateCount": 5,
  "uptimeSeconds": 184
}
```

### `GET /api/model/version`

Dashboard model-status payload.

```json
{
  "version": "0.0.3",
  "versions": [
    { "label": "Primary", "value": "0.0.3" },
    { "label": "SNN", "value": "models/snn_best.pt" },
    { "label": "LNN", "value": "models/lnn_best.pt" },
    { "label": "XGBoost", "value": "models/xgb_best.json" }
  ],
  "validationF1": [
    { "label": "SNN", "value": 0.91 },
    { "label": "LNN", "value": 0.89 },
    { "label": "XGBoost", "value": 0.94 }
  ],
  "lastRetrainedAt": "2026-04-25T00:00:00Z",
  "activeModels": ["SNN", "LNN", "XGBoost"]
}
```

### `GET /api/alerts`

Frontend-normalized alert feed.

Fields returned:

- `id`
- `severity`
- `verdict`
- `message`
- `timestamp`
- `sourceIp`
- `userId`
- `userName`
- `locationLabel`
- `score`
- `dimensions`
- `recentVerdicts`
- `modelVersion`

### `GET /verdicts/latest`

Raw latest-verdict buffer for low-level inspection.

### `GET /alerts/latest`

Raw latest-alert buffer for low-level inspection.

### `GET /profiles/{user_id}`

Returns stored behavioral profile payload for a user.

## Behavioral Routes

### `POST /behavioral/vectorize`

Request:

```json
{
  "events": [{ "type": "keydown", "timestamp": 1.0, "key": "a" }]
}
```

Response:

```json
{
  "vector": [0.1, 0.0, 0.4]
}
```

### `POST /api/behavioral`

Stores portal behavioral events against a live portal session.

Request:

```json
{
  "user_id": "test@novatrust.com",
  "session_id": "portal-123",
  "events": [{ "type": "mousemove", "timestamp": 1.0, "x": 10, "y": 20 }],
  "source_ip": "127.0.0.1",
  "page": "/login"
}
```

Response:

```json
{
  "status": "captured",
  "userId": "test@novatrust.com",
  "sessionId": "portal-123",
  "eventCount": 14,
  "vector": [0.12, 0.08, 0.44]
}
```

Note:

- Phase 9 stages behavioral telemetry first
- Final profile promotion still happens during verdict analysis
- This avoids mutating the trusted profile before a session has actually been evaluated

## Verdict Routes

### `GET /api/verdicts/current`

### `GET /api/verdicts/current-session`

Both routes return the latest portal-oriented verdict payload.

```json
{
  "sessionId": "portal-123",
  "verdict": "HACKER",
  "confidence": 0.97,
  "snnScore": 0.97,
  "lnnClass": "WEB_ATTACK",
  "xgbClass": "WEB_ATTACK",
  "behavioralDelta": 0.97,
  "modelVersion": "0.0.3"
}
```

### `GET /api/verdicts/{user_id}`

Returns the latest verdict plus recent history for a specific user.

## Bank Routes

### `POST /api/bank/login`

Request:

```json
{
  "email": "test@novatrust.com",
  "password": "password123",
  "session_id": "portal-123",
  "source_ip": "127.0.0.1"
}
```

Response:

```json
{
  "authenticated": true,
  "user_id": "alice",
  "displayName": "Alice Johnson",
  "sessionId": "portal-123",
  "verdict": "LEGITIMATE",
  "confidence": 0.24,
  "sandbox": null,
  "next": "/dashboard",
  "account": {
    "balance": 12450.0,
    "accountMasked": "****4521"
  }
}
```

If the session is escalated:

- `verdict` becomes `HACKER`
- `sandbox` is populated
- `sandbox_token` cookie is set
- `X-Sandbox-Token` response header is set
- `next` becomes `/security-alert`

### `POST /api/bank/transfer`

Accepts simulated transfer requests.

Security behaviors:

- hidden `confirm_routing_number` -> honeypot escalation
- SQLi-like memo -> web-attack escalation
- large transfer amount -> suspicious but not always sandboxed

### `POST /api/bank/honeypot-hit`

Immediate attacker signal capture route for hidden-field or trap-trigger events.

### `POST /api/bank/web-attack-detected`

Immediate escalation route for portal-detected web attack payloads.

## Sandbox Route

### `GET /api/sandbox/{session_id}/replay`

Returns sandbox replay data for the portal session.

Behavior:

- if a live sandbox gateway is reachable through `SANDBOX_BASE_URL`, replay is fetched from sandbox
- otherwise a local placeholder replay is returned from the Phase 9 session cache

## Placeholder Behavior

Phase 9 intentionally supports partial infrastructure.

If `SANDBOX_BASE_URL` is missing or unreachable:

- sandbox activation still returns `sandbox.active = true`
- a placeholder token is generated
- the `sandbox_token` cookie is still set
- replay falls back to locally cached API actions

This keeps frontend integration and demo flows moving before final sandbox network wiring is complete.

## Frontend Dependency Notes

### Simulation Portal dependencies

- `POST /api/behavioral`
- `POST /api/bank/login`
- `POST /api/bank/transfer`
- `POST /api/bank/honeypot-hit`
- `POST /api/bank/web-attack-detected`
- `GET /api/verdicts/current`
- `GET /api/verdicts/{user_id}`
- `GET /api/sandbox/{session_id}/replay`

### Dashboard dependencies

- `GET /api/stats`
- `GET /api/model/version`
- `GET /api/alerts`
- `GET /profiles/{user_id}`
- `WS /ws/alerts`

## Current Phase 9 Notes

- Phase 9 is implemented inside `inference-service/main.py` for now
- it is acting as both inference API and gateway/orchestration layer
- later refactoring can move these routes into `inference-service/api/` without changing the contract

## Verification

You can verify Phase 9 in two layers:

- contract verification only:
  - `python tests/verify_phase9_api.py`
- complete live HTTP gateway-to-sandbox flow without Docker:
  - `python tests/verify_phase9_http_sandbox_flow.py`

The second test boots the real `sandbox-service` app on localhost with an in-memory fake repository, points the inference gateway at that live HTTP server, and verifies:

- sandbox session creation through `POST /sessions`
- sandbox token propagation back through the API gateway
- replay retrieval through `GET /sessions/{sandbox_token}/replay`

This is the fastest way to validate the full Phase 9 + Phase 10 handoff on a machine where Docker is unavailable or blocked.
