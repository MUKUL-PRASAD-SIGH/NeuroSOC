# SIMULATION BANK PORTAL SPECIFICATION — NovaTrust Bank

> **Purpose:** A fully functional simulated banking application that allows judges, evaluators, and red-teamers to attempt realistic attacks against the NeuroShield system. Every interaction is monitored in real-time by the AI engine.

---

## Portal Overview

**Name:** NovaTrust Bank  
**URL (demo):** http://localhost:3001  
**Tech:** React 18 + TypeScript + TailwindCSS + FastAPI backend routes  
**Design:** Realistic 2024 banking portal aesthetic (NOT obviously a demo)

---

## User Personas & Pre-Seeded Accounts

### Persona 1 — Normal User (Alice)
- **Email:** test@novatrust.com
- **Password:** password123
- **Behavioral Profile:** Slow typist, 80–120ms inter-key interval, deliberate mouse movements
- **Pre-seeded sessions:** 10 baseline sessions
- **Account Balance:** $12,450.00
- **Demo Use:** Judges log in normally → NeuroShield shows LEGITIMATE

### Persona 2 — Fast Normal User (Bob)
- **Email:** normal2@novatrust.com
- **Password:** secure456
- **Behavioral Profile:** Fast typist, 30–50ms inter-key interval, uses keyboard shortcuts
- **Pre-seeded sessions:** 10 baseline sessions
- **Account Balance:** $89,320.00
- **Demo Use:** Establishes that NeuroShield handles different typing styles

### Persona 3 — Admin (Carol)
- **Email:** admin@novatrust.com
- **Password:** Admin@2024!
- **Behavioral Profile:** Mixed speed, frequent Tab key usage, long dwell on passwords
- **Pre-seeded sessions:** 15 baseline sessions
- **Account Balance:** N/A (admin view only)
- **Demo Use:** Attempting to access Carol's account as outsider → HACKER verdict

---

## Page Specifications

### Page 1: `/` — Landing Page
**Design elements:**
- NovaTrust Bank logo (custom SVG, navy and gold)
- Hero tagline: "Banking you can trust. Technology you can't see."
- Login CTA button
- Links: Personal Banking | Business | Wealth Management | About (all fake, lead to /login)
- Footer with fake address, FDIC logo, legal text

**Hidden security elements:**
- Canary token embedded in page metadata `<meta name="csrf-token" content="CANARY_TOKEN">`
- Honeypot link in footer: `<a href="/internal/staff-portal" style="display:none">Staff Portal</a>`

---

### Page 2: `/login` — Login Portal

**Visible UI:**
```
┌─────────────────────────────────────────────┐
│        🏦 NovaTrust Bank                    │
│                                             │
│  Welcome Back                               │
│  ─────────────────                          │
│  Email Address: [___________________________]│
│  Password:      [___________________________]│
│                                             │
│  [□] Remember this device                  │
│                 [Sign In]                   │
│                                             │
│  Forgot password? | Create Account          │
│  🔒 256-bit SSL Encrypted                  │
└─────────────────────────────────────────────┘
```

**Hidden security elements:**
- Invisible honeypot field: `<input name="username_confirm" style="opacity:0;position:absolute;top:-9999px">`
- If honeypot field is filled → instant CRITICAL alert (bot detection)

**Behavioral tracking (invisible to user):**
```typescript
// Fires on every keydown
{ type: 'keydown', key: 'a', timestamp: 1720000001.234, element: 'password' }
// Fires on every keyup
{ type: 'keyup', key: 'a', timestamp: 1720000001.289, element: 'password' }
// Mouse moves sampled at 10Hz
{ type: 'mousemove', x: 450, y: 320, timestamp: 1720000001.100 }
```

**On Submit Flow:**
1. Send behavioral events to NeuroShield: `POST /api/behavioral`
2. Wait for behavioral verdict
3. Send credentials to `POST /api/bank/login`
4. If login success AND NeuroShield verdict ≠ HACKER → go to /dashboard
5. If NeuroShield verdict = HACKER → redirect to /security-alert (but actually to sandbox)
6. If login fails → show error, do NOT reveal if email exists (security best practice)

**Attack vectors judges can try here:**
- Rapid successive wrong passwords (brute force → behavioral anomaly)
- Typing random characters fast then slowly (rhythm anomaly)
- Pasting password (no typing rhythm at all → anomaly)
- Using automation/Selenium (no human mouse movement → anomaly)

---

### Page 3: `/dashboard` — Account Dashboard

**Visible UI:**
```
┌──────────────────────────────────────────────────────────────┐
│  NovaTrust Bank   Alice Johnson  ▼   [Logout]   [⚙ Settings]│
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Available Balance                                           │
│  ──────────────────                                          │
│  $12,450.00 USD                                              │
│  Account: ****4521                                           │
│                                                              │
│  [Pay Bills]  [Transfer]  [Statements]  [Cards]             │
│                                                              │
│  Recent Transactions                                         │
│  ──────────────────────────────────────────────────────────  │
│  Apr 20  Amazon.com            -$89.99                       │
│  Apr 19  Netflix               -$15.99                       │
│  Apr 19  Paycheck ACH Deposit  +$3,200.00                    │
│  Apr 18  Whole Foods Market    -$67.43                       │
│  (... 6 more)                                                │
└──────────────────────────────────────────────────────────────┘
```

**Hidden security elements:**
- HTML comment: `<!-- Session token: [UNIQUE_CANARY_TOKEN] DO NOT SHARE -->`
- Hidden API endpoint referenced in JS: `fetch('/api/internal/user-export')` (honeypot API)
- Canary token also injected into `localStorage['debug_token']` — any exfiltration triggers alert

**Behavioral tracking continues:**
- Navigation patterns tracked (which buttons clicked, in what order)
- Dwell time on balance section
- Scroll behavior

---

### Page 4: `/transfer` — Money Transfer

**Visible UI:**
```
┌────────────────────────────────────────────┐
│  Transfer Funds                            │
│  ────────────────                          │
│  From Account:  [Checking ****4521   ▼]   │
│  To Account:    [_____________________]    │
│  Amount:        [$ ___________________]    │
│  Memo:          [_____________________]    │
│                                            │
│  [HIDDEN FIELD: confirm_routing_number]    │
│  (invisible to human, visible to bots)     │
│                                            │
│  [Cancel]          [Transfer Funds]        │
└────────────────────────────────────────────┘
```

**Security logic:**
- `confirm_routing_number` field: if filled → bot detected → CRITICAL alert + HACKER verdict
- Transfer amount > $10,000 → triggers suspicious activity flag (AML simulation)
- SQL injection in memo field: detect `' OR 1=1 --` patterns → WEB_ATTACK verdict

**Attack vectors:**
- Fill hidden field (automated form submission)
- SQL inject the memo field
- Transfer $999,999 (suspicious amount)

---

### Page 5: `/security-alert` — Attacker Sees This (Sandbox)

**What attacker sees (sandbox environment):**
```
┌────────────────────────────────────────────────────────┐
│  ⚠️  NovaTrust Security Alert                         │
│                                                        │
│  We've detected unusual activity on your account.     │
│  Your session has been temporarily suspended while    │
│  our security team reviews this activity.             │
│                                                        │
│  Reference Number: NS-[RANDOM]                        │
│  Estimated Review Time: 24 hours                      │
│                                                        │
│  If you believe this is an error, please call:        │
│  1-800-NOVATRUST                                      │
│                                                        │
│  [Return to Login]                                    │
└────────────────────────────────────────────────────────┘
```

**What's actually happening:**
- Attacker is in isolated sandbox — `sandbox-service` runs with `network_mode: none` (no external network access per Docker Compose config), providing true container-level isolation
- Any further actions (clicking, refreshing) are logged
- Real account is completely unaffected
- All attacker data captured: IPs, device fingerprint, actions attempted
- Sandbox session expires after 5 minutes → attacker logged out automatically

---

### Page 6: `/verdict-display` — Judge's God View

**This page is ONLY for judges during evaluation. Not linked from normal portal navigation.**

**Split-screen layout:**
```
┌─────────────────────────┬──────────────────────────────┐
│   NovaTrust Bank        │   NeuroShield Live Analysis   │
│   (Attacker View)       │                              │
│                         │  Session: NS-abc123           │
│   [IFRAME of /login]    │  Source IP: 127.0.0.1        │
│                         │  User: Unknown                │
│                         │                              │
│                         │  ┌─────────────────────────┐ │
│                         │  │  SNN Score:   0.73      │ │
│                         │  │  LNN Class:   BRUTE_FORCE│ │
│                         │  │  XGB Conf:    0.81      │ │
│                         │  │  Behav Δ:     0.61      │ │
│                         │  │  VERDICT: FORGETFUL USER│ │
│                         │  └─────────────────────────┘ │
│                         │                              │
│                         │  [LIVE UPDATING EVERY 2s]    │
│                         │                              │
│                         │  Behavioral Timeline:        │
│                         │  ████████▒▒ Typing Rhythm    │
│                         │  ██████▒▒▒▒ Mouse Velocity   │
│                         │  ████▒▒▒▒▒▒ Nav Pattern      │
└─────────────────────────┴──────────────────────────────┘
```

**Technical implementation:**
- Left panel: iframe of `/login` OR a separate browser window via `window.open`
- Right panel: React component polling `GET /api/verdicts/current-session` every 2 seconds
- Verdict response includes: `snn_score`, `lnn_class`, `xgb_confidence`, `behavioral_delta`, `verdict`
- Real-time confidence score updates with animated progress bars
- Color transitions: green (LEGITIMATE) → yellow (FORGETFUL) → red (HACKER)

---

## End-to-End Protocol Flow

```
1. Judge opens /verdict-display
2. Left panel shows /login page
3. Judge types credentials — useBehavioralTracker() captures every keystroke/mouse event
4. Every 10 seconds: events flushed via POST /api/behavioral to the api gateway
5. api gateway publishes events as JSON to Kafka topic: raw-traffic
6. feature-service consumes raw-traffic → extracts 80-feature CIC vector → publishes to extracted-features
7. inference-service consumes extracted-features:
   SNN encoder → SNN anomaly score
   LNN reservoir → reservoir state + class probs
   XGBoost classifier → final ThreatVerdict (snn_score + lnn_state + behavioral_delta)
8. inference-service writes ThreatVerdict to PostgreSQL and publishes to Kafka: verdicts
9. feedback-service consumes verdicts → labels suspicious sessions → writes to labeled_training_data
10. api gateway polls DB every 2s → broadcasts verdict via WebSocket /ws/alerts
11. Right panel (polling GET /api/verdicts/current-session) updates: SNN score, LNN class,
    XGB confidence, behavioral delta, final verdict
12. If verdict = HACKER → left panel automatically shows /security-alert (sandbox)
    Right panel shows: "Sandbox Active — Attacker Isolated"
13. Judge can view replay via "Replay Session" button
```

---

## Honeypot & Canary Token Map

| Location | Trap Type | Trigger | Alert Severity |
|---|---|---|---|
| `/api/admin` | Honeypot endpoint | Any HTTP request | CRITICAL |
| `/api/debug` | Honeypot endpoint | Any HTTP request | CRITICAL |
| `/.env` | Honeypot file | Any HTTP request | BREACH |
| `/wp-admin` | Honeypot URL | Any HTTP request | WARNING |
| `/api/internal/user-export` | Honeypot API | Any HTTP request | CRITICAL |
| `/internal/staff-portal` | Honeypot link | Click | WARNING |
| `<meta csrf-token>` | Canary token | Token used in API call | CRITICAL |
| `localStorage debug_token` | Canary token | Token sent to external URL | BREACH |
| Transfer form `confirm_routing` | Honeypot field | Field filled on submit | CRITICAL |
| SQL injection in memo | Attack pattern | Pattern matched | WEB_ATTACK alert |

---

## Demo Scenarios for Judges

### Scenario A — Be a Normal User (Expected: LEGITIMATE)
1. Open `/verdict-display`
2. Type credentials slowly and carefully
3. Browse account, look at transactions
4. Make a small transfer ($100)
5. Expected NeuroShield verdict: LEGITIMATE (green)

### Scenario B — Be a Forgetful User (Expected: FORGETFUL_USER)
1. Type wrong password 2–3 times
2. Type slowly, make deliberate mistakes
3. Eventually get in with correct password
4. Expected: FORGETFUL_USER (yellow) — anomalous but consistent with human error

### Scenario C — Be a Hacker (Expected: HACKER)
1. Type rapidly and randomly (simulate automated tool)
2. Try to access `/api/admin` in the URL bar
3. Fill transfer form and try SQL injection in memo
4. Expected: HACKER verdict (red), redirected to sandbox

### Scenario D — Be an Automated Bot (Expected: HACKER + CRITICAL)
1. Run `python redteam/attack_brute_force.py`
2. Watch dashboard: rapid CRITICAL alerts
3. All requests land in sandbox immediately
4. Honeypot hits logged and displayed

---

## Data Retention (Demo Only)

All data in the simulation portal is **ephemeral**. A reset script clears:
- All sandbox sessions
- All verdicts from current demo
- All behavioral events
- Returns all accounts to baseline behavioral profiles

```bash
python redteam/reset_demo.py
# Clears all demo data, re-seeds user profiles
# Takes ~10 seconds
```

This allows the demo to be run multiple times cleanly during judging.
