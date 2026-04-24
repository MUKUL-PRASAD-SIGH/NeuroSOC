# Sandbox Reminders

This file tracks what the sandbox already does today, what was intentionally left as a placeholder, and what later phases should integrate instead of rebuilding from scratch.

## What Is Complete Now

- `sandbox-service/main.py` provides a real Phase 10 decoy service.
- Sandbox sessions are created through `POST /sessions`.
- All sandbox routes require a valid sandbox token, except health and internal session management.
- The service mirrors the core attacker-facing bank flow:
  - `GET/POST /login`
  - `GET /dashboard`
  - `GET/POST /transfer`
  - `GET /security-alert`
  - `GET/POST/etc /api/*`
  - generic catch-all routes that never expose a real 404-style structure
- Requests are logged to `sandbox_actions`.
- Triggered traps are recorded to `honeypot_hits`.
- Session termination publishes to Kafka topic `feedback-trigger`.
- Session expiry is handled automatically in the background.
- Session replay is available internally through `GET /sessions/{sandbox_token}/replay`.

## Current Tables The Sandbox Owns

- `sandbox_sessions`
- `sandbox_actions`
- `honeypot_hits`

Do not rename these casually. Later phases should integrate with them.

## Current Trap Signals The Sandbox Records

- Honeypot endpoints:
  - `/api/admin`
  - `/api/debug`
  - `/.env`
  - `/wp-admin`
  - `/api/internal/user-export`
  - `/internal/staff-portal`
- Honeypot form fields:
  - `username_confirm`
  - `confirm_routing_number`
- Canary indicators:
  - `csrf-token`
  - `canary_token`
  - `debug_token`
- SQL injection patterns in posted content

## Phase 9 / API Integration Reminders

- The API gateway should create sandbox sessions via `POST /sessions` before redirecting a suspicious user.
- The API gateway should pass the returned token as `X-Sandbox-Token` and also set the `sandbox_token` cookie.
- The API gateway should expose replay data from `GET /sessions/{sandbox_token}/replay` rather than re-querying sandbox tables ad hoc.
- The API gateway should keep sandbox orchestration outside the ML inference engine. Inference should produce verdicts; API/orchestration should decide redirect flow.

## Phase 11 / Simulation Portal Reminders

- The bank portal should redirect HACKER verdicts to `/security-alert` while carrying the sandbox token forward.
- The portal honeypot fields must stay aligned with the sandbox trap logic:
  - login: `username_confirm`
  - transfer: `confirm_routing_number`
- The hidden honeypot and canary routes listed above should stay reachable in the portal experience so the sandbox can log them.
- The judge replay or admin replay UI should use the sandbox replay endpoint instead of inventing a second replay format.

## Feedback / Retraining Reminders

- Feedback already reads sandbox session actions from `sandbox_actions`.
- If retraining later starts using `honeypot_hits`, prefer enriching labels with those rows rather than duplicating trigger logic in multiple places.
- `feedback-trigger` exists for future event-driven integration, but current feedback polling still uses Postgres as the source of truth.

## Security / Infra Reminders

- Docker Compose now isolates sandbox traffic from the main app network by placing the sandbox on `sandbox-net` only.
- Kafka and Postgres are attached to `sandbox-net` so the sandbox can log actions and publish termination events.
- For Kubernetes later, mirror this with a dedicated NetworkPolicy that allows only:
  - sandbox -> postgres
  - sandbox -> kafka
  - ingress from the intended frontend/gateway
- The sandbox Dockerfile now runs as a non-root `sandbox_user`. Keep it that way.

## Deliberate Placeholders For Later Phases

- Rich browser-perfect HTML parity with the real NovaTrust frontend is still intentionally lightweight.
- Full analyst replay UX is not built yet; only the backend replay endpoint is ready.
- Automatic inference-to-sandbox redirect orchestration should be finished in the API/gateway phase, not by pushing more coupling into `inference-service`.
- Reset/demo scripts should later clear:
  - `sandbox_sessions`
  - `sandbox_actions`
  - `honeypot_hits`

## When You Ask Later

If you ask me to continue sandbox-related work in later phases, tell me to:

`refer Docs/SANDBOX_REMINDERS.md before editing sandbox integrations`

That is the file I should treat as the running sandbox integration memory.
