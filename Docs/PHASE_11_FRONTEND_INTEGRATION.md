# Phase 11 Frontend Integration

This file is the current frontend integration memory for the user-facing loop.

Use it before editing dashboard or simulation portal work in later phases.

## Scope

Phase 11 is considered complete when these paths work together:

1. user lands on portal
2. login page creates or reuses a single portal session
3. behavioral events are flushed with the same `session_id`
4. login/transfer actions hit the Phase 9 API gateway
5. verdicts are fetched back with the same `session_id`
6. suspicious sessions activate sandbox mode
7. judge view shows the same live verdict and replay state
8. analyst dashboard surfaces the alerts/model status from the same backend

## Shared Session Model

The simulation portal uses one local browser session record:

- file: `simulation_portal/src/lib/portalSession.ts`
- storage key: `novatrust.portal.session`

Fields currently persisted:

- `sessionId`
- `userId`
- `email`
- `displayName`
- `authenticated`
- `verdict`
- `confidence`
- `account`
- `sandbox`

Do not reintroduce ad hoc session generation inside individual pages.

## Shared Portal API Layer

The simulation portal must call the shared API helpers in:

- `simulation_portal/src/lib/portalApi.ts`

Current helpers:

- `postBehavioral`
- `loginBank`
- `transferBank`
- `reportHoneypotHit`
- `reportWebAttack`
- `getCurrentVerdict`
- `getUserVerdict`
- `getSandboxReplay`

If a page needs a new backend call, add it there first instead of embedding raw `fetch()` calls everywhere.

## Page-by-Page Contract

### Landing

- file: `simulation_portal/src/pages/LandingPage.tsx`
- keeps hidden canary meta tag: `csrf-token`
- keeps hidden staff honeypot link: `/internal/staff-portal`

### Login

- file: `simulation_portal/src/pages/LoginPage.tsx`
- must use the shared tracker with the current `sessionId`
- flushes behavioral events before login
- honeypot field name is `username_confirm`
- calls:
  - `POST /api/behavioral`
  - `POST /api/bank/login`
  - `GET /api/verdicts/{user_id}`
- routes:
  - legitimate -> `/dashboard`
  - sandboxed/hacker -> `/security-alert`

### Dashboard

- file: `simulation_portal/src/pages/DashboardPage.tsx`
- must read the persisted portal session
- redirects to `/login` if `userId` is missing
- redirects to `/security-alert` if sandbox is active
- continues behavioral tracking under the same session
- writes the debug canary token to local storage

### Transfer

- file: `simulation_portal/src/pages/TransferPage.tsx`
- uses the same persisted `sessionId`
- continues behavioral tracking
- calls `POST /api/bank/transfer`
- handles:
  - accepted transfer
  - suspicious transfer
  - sandboxed transfer

### Security Alert

- file: `simulation_portal/src/pages/SecurityAlertPage.tsx`
- reads sandbox metadata from the persisted session
- calls `GET /api/sandbox/{session_id}/replay`
- shows current replay count and sandbox token

### Verdict Display

- file: `simulation_portal/src/pages/VerdictDisplayPage.tsx`
- polls `GET /api/verdicts/current`
- switches iframe:
  - `/login` when normal
  - `/security-alert` when sandboxed
- loads replay count from `GET /api/sandbox/{session_id}/replay`

## Dashboard App Contract

The analyst dashboard depends on:

- `GET /api/stats`
- `GET /api/model/version`
- `GET /api/alerts`
- `WS /ws/alerts`

Current normalization happens in:

- `dashboard/src/services/dashboardApi.js`

The dashboard assumes alert items already include:

- user metadata
- score
- message
- dimensions
- recent verdict history
- model version

Those are now produced by the backend alert formatter, not by mock-only code.

## What Is Real vs Placeholder

Real now:

- portal session flow
- behavioral event posting
- login flow
- transfer flow
- verdict fetch flow
- sandbox activation flow
- sandbox replay bridge
- analyst dashboard API consumption
- real localhost HTTP sandbox integration test

Still placeholder by design:

- trained model quality
- final model artifact swap behavior for future retraining
- real production geolocation guarantees
- production auth hardening

## Verification

Backend and integration:

- `python tests/verify_phase9_api.py`
- `python tests/verify_phase9_http_sandbox_flow.py`

Frontend builds:

- `cd simulation_portal && npm run build`
- `cd dashboard && npm run build`

## When You Ask Later

If you ask me to continue frontend integration later, tell me:

`refer Docs/PHASE_11_FRONTEND_INTEGRATION.md before editing portal or dashboard flow`
