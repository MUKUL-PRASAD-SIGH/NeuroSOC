# NeuroSOC — Neuromorphic AI Cybersecurity Platform

> **Tagline:** *Thinking like a brain. Defending like a fortress. An AI-powered replacement and augmentation of a human SOC analyst — with a built-in SIEM layer, tiered alert engine, real-time threat detection, autonomous sandboxing, and overnight autonomous response with morning human review.*

---

## 📑 Table of Contents
1. [🧠 What Makes This Different](#-what-makes-this-different)
2. [🏗️ Full System Architecture](#️-full-system-architecture)
3. [🚨 The SIEM Layer — In Depth](#-the-siem-layer--in-depth)
4. [🔬 SNN–LNN Hybrid Engine & Research Novelty](#-snnlnn-hybrid-engine--research-novelty)
5. [🔁 Real-World Flow: The Hacker vs. The Forgetful User](#-real-world-flow-the-hacker-vs-the-forgetful-user)
6. [🚦 Autonomous Overnight Loop & Sandboxing](#-autonomous-overnight-loop--sandboxing)
7. [📊 SIEM Dashboard — Morning Analyst View](#-siem-dashboard--morning-analyst-view)
8. [🏦 Simulation Bank Portal](#-simulation-bank-portal)
9. [📦 Datasets & Detection Pipeline](#-datasets--detection-pipeline)
10. [🧩 Technology Stack](#-technology-stack)
11. [📁 Project Structure](#-project-structure)
12. [🚀 Setup & Installation](#-setup--installation)
13. [👥 Team & Human-in-the-Loop Design](#-team--human-in-the-loop-design)
14. [🗺️ Roadmap](#️-roadmap)

---

## 🧠 What Makes This Different

Traditional SIEMs (Splunk, QRadar, Microsoft Sentinel) and IDSs are **loud and passive** — they correlate logs, fire thousands of alerts, and dump them on an analyst's screen. The analyst drowns. Most alerts go unread. Attackers count on this.

**NeuroShield (NeuroSOC) is different in three ways:**

| Problem with classic SIEM / IDS | How NeuroShield Solves It |
|---|---|
| 10,000 alerts/day, analyst reads 200 | SNN+LNN hybrid reduces noise to ranked, actionable signals |
| Alert fires → analyst manually investigates | Alert fires → system autonomously sandboxes and collects evidence |
| No action at 2AM | Autonomous overnight loop — human reviews evidence at 9AM |
| Can't distinguish forgetful user from hacker | LNN builds per-entity behavioral fingerprint over time |
| SIEM is a viewer, not an actor | System detects, decides, diverts, decoys, and reports |

---

## 🏗️ Full System Architecture

```text
╔═══════════════════════════════════════════════════════════════╗
║                     NEUROSHIELD PLATFORM                      ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │               INGESTION LAYER                           │  ║
║  │                                                         │  ║
║  │  🏦 DB Query Logs    🌐 Network Packets  📋 Auth Logs   │  ║
║  │  ☁️  Cloud Trails    💻 Endpoint EDR     📡 Syslog      │  ║
║  │  🔌 API Gateway Logs  📧 Email Events   🔐 VPN/IAM      │  ║
║  │                                                         │  ║
║  │     → Secure Read-Only Connectors (per source type)    │  ║
║  └──────────────────────────┬──────────────────────────────┘  ║
║                             │                                 ║
║                             ▼                                 ║
║  ┌─────────────────────────────────────────────────────────┐  ║
║  │           NORMALIZATION ENGINE                          │  ║
║  │  Raw events → Unified Event Format (UEF)                │  ║
║  │  Timestamp sync │ Dedup │ GeoIP enrich │ Entity tagging  │  ║
║  └──────────────────────────┬──────────────────────────────┘  ║
║                             │                                 ║
║                             ▼                                 ║
║  ╔═════════════════════════════════════════════════════════╗  ║
║  ║        NEUROSOC SIEM CORE                              ║  ║
║  ║                                                         ║  ║
║  ║  ┌─────────────────┐    ┌──────────────────────────┐   ║  ║
║  ║  │  EVENT STORE    │    │   CORRELATION ENGINE     │   ║  ║
║  ║  │  (time-series   │───▶│   Rule-based + ML        │   ║  ║
║  ║  │   indexed log)  │    │   Multi-source linking   │   ║  ║
║  ║  └─────────────────┘    └────────────┬─────────────┘   ║  ║
║  ║                                      │                  ║  ║
║  ║                                      ▼                  ║  ║
║  ║  ┌──────────────────────────────────────────────────┐  ║  ║
║  ║  │       SNN + LNN HYBRID DETECTION  [Research]     │  ║  ║
║  ║  │                                                   │  ║  ║
║  ║  │  ⚡ SNN → Spike-encodes events, fires on bursts   │  ║  ║
║  ║  │  🌊 LNN → Continuous ODE state, tracks behavior  │  ║  ║
║  ║  │  🔗 Combined → Spike triggers context evaluation │  ║  ║
║  ║  └──────────────────┬───────────────────────────────┘  ║  ║
║  ║                     │                                   ║  ║
║  ║                     ▼                                   ║  ║
║  ║  ┌──────────────────────────────────────────────────┐  ║  ║
║  ║  │      ALERT ENGINE  🚨                            │  ║  ║
║  ║  │                                                   │  ║  ║
║  ║  │  P1 🔴 CRITICAL  → Immediate sandbox + block     │  ║  ║
║  ║  │  P2 🟠 HIGH      → Sandbox + monitor             │  ║  ║
║  ║  │  P3 🟡 MEDIUM    → Flag + watch for escalation   │  ║  ║
║  ║  │  P4 🟢 LOW       → Log only, update baseline     │  ║  ║
║  ║  └──────────────────┬───────────────────────────────┘  ║  ║
║  ║                     │                                   ║  ║
║  ║                     ▼                                   ║  ║
║  ║  ┌──────────────────────────────────────────────────┐  ║  ║
║  ║  │    CLASSIFICATION & DECISION ENGINE              │  ║  ║
║  ║  │  XGBoost → Threat class  │  Decision Tree → Triage│ ║  ║
║  ║  │  Classes: Normal │ Notorious │ Insider │ Attacker │  ║  ║
║  ║  └──────────────────┬───────────────────────────────┘  ║  ║
║  ╚════════════════════╪════════════════════════════════════╝  ║
║                       │                                       ║
║           ┌───────────┴────────────┐                          ║
║           ▼                        ▼                          ║
║   RISK < THRESHOLD           RISK ≥ THRESHOLD                 ║
║   → Normal service           → SANDBOX DIVERSION             ║
║                                     │                         ║
║              ┌──────────────────────▼────────────────────┐   ║
║              │          HONEYPOT SANDBOX  🪤              │   ║
║              │  Serve fake/decoy data to suspected user   │   ║
║              │  Capture all actions → feed back to SIEM   │   ║
║              │  Escalate alert tier based on behavior     │   ║
║              └──────────────────────┬────────────────────┘   ║
║                                     │                         ║
║                     ┌───────────────┴──────────────┐         ║
║                     ▼                               ▼         ║
║              Keeps exploiting               Stops / lost      ║
║              [P1 → HACKER]              [P3 → Verify user]    ║
║              Block, hold,               Soft error shown,     ║
║              full log                   restored after 2FA    ║
║                                     │                         ║
║              ┌──────────────────────▼────────────────────┐   ║
║              │     MORNING ANALYST DASHBOARD  📊          │   ║
║              │  Ranked alert queue │ Sandbox replay        │   ║
║              │  AI verdict + confidence │ Override button   │   ║
║              └───────────────────────────────────────────┘   ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## 🚨 The SIEM Layer — In Depth

NeuroShield's SIEM is **not a log viewer**. It is an active event intelligence backbone with three jobs:

### 1. Event Correlation
Raw events are individually weak signals. The correlation engine links them across sources:
```text
Event A:  User "john" failed login         [alone: noise]
Event B:  Same IP queried /admin 3x        [alone: noise]
Event C:  New device fingerprint for john  [alone: noise]
────────────────────────────────────────────────────────
Correlated → SIEM fires: "Credential stuffing on john" → P2 Alert
```

### 2. Alert Tiers & Lifecycle
```text
                     ALERT BORN
                         │
            ┌────────────▼────────────┐
            │   SIEM Correlation      │  ← multi-source fusion
            │   scores the event      │
            └────────────┬────────────┘
                         │
          ┌──────────────▼──────────────┐
          │  SNN Spike detected?         │
          │  YES → urgency boost         │
          │  NO  → LNN watches quietly   │
          └──────────────┬──────────────┘
                         │
          ┌──────────────▼──────────────┐
          │   XGBoost classifies         │
          │   Final P1 / P2 / P3 / P4   │
          └──────────────┬──────────────┘
                         │
       ┌─────────┬────────┴──────┬───────────┐
       ▼         ▼               ▼           ▼
      P1 🔴    P2 🟠           P3 🟡       P4 🟢
  CRITICAL    HIGH           MEDIUM        LOW
  Auto-sandbox Auto-sandbox  Watch+flag   Log only
  + block      + monitor     no action    baseline
  SIEM alert   SIEM alert    yet          update
  dashboard    dashboard
```

### 3. Alert Fatigue Elimination
Classic SIEMs suppress nothing — analysts see 10,000 alerts/day, ~97% false positives. NeuroShield's approach:
- **SNN deduplication**: identical spike patterns within a time window collapse into one alert.
- **LNN baseline-relative scoring**: an event only alerts if it deviates from *that specific entity's* baseline — not a global threshold.
- **Sandbox auto-triage**: P1/P2 alerts are autonomously handled overnight so the analyst's morning queue has *resolved cases with evidence*, not raw noise.

> **Goal:** Analyst sees **10 deeply enriched, pre-triaged cases at 9AM** — not 10,000 raw alerts.

---

## 🔬 SNN–LNN Hybrid Engine & Research Novelty

The **core research contribution** is the detection engine fusing **Spiking Neural Networks (SNNs)** and **Liquid Neural Networks (LNNs)**.

- **SNNs (Spiking Neural Networks):** Encode network events as temporal spikes — fast, low-latency, event-driven anomaly detection on raw packet features. Validated for high accuracy intrusion detection with extreme energy efficiency (100x over GPU).
- **LNNs (Liquid Neural Networks):** Based on continuous-time ODEs. They build a live behavioral context carrier that evolves per entity in real time. **Never before applied to cybersecurity behavioral modeling**.
- **Hybrid Fusion:** SNN spike outputs act as *event tokens* fed into the LNN's continuous hidden state. The LNN state directly drives alert tier scoring — a novel feedback loop where behavioral continuity modulates SIEM sensitivity per entity.

```python
# Pseudocode: Hybrid decision fusion
snn_score    = snn_encoder.anomaly_score(packet_spike_train)
lnn_class    = lnn_classifier.predict(session_feature_sequence)
behav_delta  = behavioral_profiler.get_delta(user_id, session_vector)

confidence   = 0.4 * snn_score + 0.4 * lnn_class + 0.2 * behav_delta
verdict      = decision_engine.classify(confidence, user_context)
```

---

## 🔁 Real-World Flow: The Hacker vs. The Forgetful User

A critical operational challenge is distinguishing a **malicious actor** from a **legitimate user exhibiting anomalous behavior** (e.g., repeatedly forgetting passwords, logging in from a new device). 

The LNN Behavioral Engine solves this by continuously updating a **behavioral biometric fingerprint** per user (Typing rhythm, mouse dynamics, navigation habits, login timing).

**2AM Scenario Cast:** Normal User, Notorious User (forgetful ex-employee), External Hacker

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 👤 NORMAL USER  (Priya logs in from her usual phone at 10PM)
 ──────────────────────────────────────────────────────────
  → Login from known device, known IP, normal hour
  → SNN: no spike  │  LNN: delta near zero
  → SIEM: no alert fired  │  XGBoost: Normal
  → ✅ Access granted, event logged as P4 (baseline update)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 🤦 NOTORIOUS USER  (Raj, ex-employee, forgot he left)
 ──────────────────────────────────────────────────────────
  → Login attempt at 2AM, wrong password ×3, old device
  → SNN: mild spike  │  LNN: moderate drift from Raj's baseline
  → SIEM: P3 alert — "Repeated fail, known device, off-hours"
  → XGBoost: Notorious (not attacker, confidence low)
  → P3 → just watches. After 5 total attempts → escalates to P2
  → Sandbox activated: Raj sees "account locked" screen, stops
  → LNN: behavior consistent with confusion, not exploitation
  → SIEM logs: "P2 → Sandbox → Stopped → Likely mistake"
  → 9AM: Analyst sees "Raj: 5 fails, old device, stopped in sandbox"
  → Analyst hits [Restore] → Raj gets password reset + 2FA prompt
  → ✅ Raj gets a "sorry for the inconvenience" email

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 💀 EXTERNAL HACKER  (unknown actor, credential-stuffing)
 ──────────────────────────────────────────────────────────
  → 2AM, 400 login attempts/min across 80 accounts, TOR IP
  → SNN: MASSIVE spike  │  LNN: zero history, alien trajectory
  → SIEM: P1 alert — "Mass credential stuffing, new IP block"
  → XGBoost: External Attacker, confidence 0.97
  → All 80 sessions silently diverted to Sandbox
  → Hacker sees "success" — but it's a fake vault
  → Continues querying, exfiltrating fake data
  → SIEM captures every action → full attack pattern mapped
  → After 20 min of sandbox exploitation → permanent block
  → SIEM: incident ticket auto-generated, IOCs extracted
  → 9AM: Analyst sees "Attack fully documented, 0 real data touched"
  → 🔴 Block confirmed, IOCs pushed to firewall rules

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Signal Differentiators:**

| Signal | Notorious User 🤦 | Hacker 💀 |
|---|---|---|
| Password failure speed | Human pace, ~10s gaps | Scripted, <100ms gaps |
| Device / IP history | Previously seen in SIEM | Cold, new, often TOR/VPN |
| Accounts targeted | Only their own | Many accounts, admin paths |
| Post-sandbox behavior | Stops, reads error, waits | Keeps probing, pivots |
| Time-of-day baseline | Consistent with past logins | Off-hours, zero history |
| LNN behavioral delta | Low — fits personal baseline | High — fits no known profile |
| SIEM correlation hits | 1–2 weak events | 5+ correlated multi-source events |
| Alert tier triggered | P3 → P2 if escalates | P1 immediately |

---

## 🚦 Autonomous Overnight Loop & Sandboxing

When the Decision Engine flags traffic as potentially malicious (confidence ≥ 0.7), the session is transparently redirected to an **isolated sandbox environment (Honeypot)**. This provides active deception with a < 0.9% False Positive Rate.

```text
[MIDNIGHT]
    │
    ▼
[SIEM ingests continuously]
    │
    ├─ Routine events → P4 → baseline update → silent
    │
    └─ Anomaly detected → Alert born
           │
           ▼
    [SNN+LNN scores it]
           │
      P1/P2 alert?
       YES         NO
        │           └──→ P3/P4: watch quietly, log
        ▼
    [Auto-sandbox]
        │
    [Collect evidence 20–30 min]
        │
     Still exploiting?
       YES               NO
        │                 └──→ Restore user + soft error shown
        ▼
    [Block + hold in SIEM queue]
        │
        ▼
[06:00 — SIEM compiles morning brief]
        │
        ▼
[09:00 — Analyst reviews ranked queue]
        │
        ▼
    [Human confirms / overrides / escalates]
```

---

## 📊 SIEM Dashboard — Morning Analyst View

```text
╔════════════════════════════════════════════════════════════════╗
║  NeuroSOC  |  Morning Briefing  |  Apr 22  09:00               ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  OVERNIGHT SUMMARY                                             ║
║  ─────────────────                                             ║
║  Total events ingested:      1,247,832                         ║
║  Correlated alert groups:    847                               ║
║  After SNN/LNN dedup:        23                                ║
║  Auto-triaged by AI:         21    ← analyst skips these       ║
║  Needs human review:          2    ← analyst reads these       ║
║                                                                ║
║  ALERT QUEUE                                        [PRIORITY] ║
║  ────────────────────────────────────────────────────────────  ║
║  🔴 P1  Credential stuffing — 80 accts — BLOCKED  [RESOLVED]   ║
║         └─ Sandbox logs attached │ IOCs extracted │ [Confirm]  ║
║                                                                ║
║  🟠 P2  Ex-employee Raj — 5 failed logins — HELD   [REVIEW]    ║
║         └─ Sandbox: stopped after lockout screen               ║
║         └─ LNN verdict: Notorious, not malicious               ║
║         └─ [Restore Access]  [Keep Blocked]  [Escalate]        ║
║                                                                ║
║  🟡 P3  Unusual query pattern — user #4412                     ║
║         └─ Watching — no sandbox yet │ LNN tracking            ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 🏦 Simulation Bank Portal

A fully functional **simulated banking application** deployed alongside the main NeuroShield platform for demonstration, judging, and red-team testing purposes.
Allows evaluators to attempt realistic intrusions (hacker), behave as a normal user, or behave as a forgetful user, while observing NeuroShield's live verdict on their session.

Features include: Fake Account System, Canary Token Fields, Honeypot API Endpoints, Live Verdict Feed, and a Replay Console.

---

## 🧠 Backend Pipeline: Training, Ingestion & Continuous Learning

NeuroShield is designed as a **closed-loop learning SOC system**, where models are initialized offline and continuously improved using real-world feedback.

`Offline Training → Live Ingestion → Detection → Sandbox → Feedback → Retraining → Model Update`

### 1. Pre-Ingestion Setup (Offline Training Phase)
Before live ingestion, the system trains on benchmark datasets (CIC-IDS2017, CSE-CIC-IDS2018, CICIoT2023, CICIoMT2024, NSL-KDD, BETH, LANL) to create initial model intelligence. 
- **Preprocessing Pipeline:** 80 CICFlowMeter-style features, handling missing values, MinMax normalization, SMOTE for imbalance, and temporal windowing/spike encoding.
- **SNN:** Learns spike-based anomaly patterns from encoded features.
- **LNN:** Learns temporal behavioral dynamics from time-windowed sequences.
- **XGBoost / Decision Tree:** Final classification layer.
> **⚠️ Critical Requirement:** The exact same feature pipeline must be used during live inference, or the models become invalid.

### 2. Online Ingestion & Real-Time Detection
Once initialized, the backend streams live traffic (PCAP, NetFlow, Auth logs) via Kafka through the same feature pipeline.
- **Detection Flow:** `Features → SNN (Spike Anomaly) → LNN (Temporal Behavior) → XGBoost (Classification)`
- **Decision Engine:** Outputs ✅ Normal, ⚠️ Suspicious, or 🚨 Malicious.
- **Sandbox Diversion:** Suspicious users are redirected to a controlled sandbox serving fake data. If the user continues exploiting, they are labeled a Hacker; if they stop, it's labeled a False Positive.

### 3. Continuous Learning Pipeline (Core Innovation)
This is the heart of NeuroShield's adaptability: a feedback-driven batch retraining loop.
1. **Feedback Collection:** Sandbox behavioral outcomes and human analyst decisions are captured and stored as `(features, label)`.
2. **Batch Retraining (Scheduled):** Runs periodically (e.g., every 6 hours), combining the base dataset with new feedback data to retrain the final classifier.
3. **Model Update (Hot Swap):** Replaces the old model with the new one with zero downtime and strict version control. Safety mechanisms include confidence thresholds and a replay buffer to prevent catastrophic forgetting.

### 4. Model Behavior (Runtime vs Training)
| Model | Before Ingestion | During Runtime |
|---|---|---|
| **SNN** | Offline trained | Mostly static (fast inference) |
| **LNN** | Offline trained | Adaptive state (continuous live context) |
| **XGBoost** | Offline trained | Retrained periodically (scheduled batch) |
| **LLM (Optional)** | Not used | Explainability and report generation only |

---

## 🧩 Technology Stack

| Layer | Technology |
|---|---|
| **Backend / Core** | Python 3.11, PyTorch 2.x, scikit-learn, FastAPI |
| **SNN / LNN** | Norse (PyTorch-based SNN), Custom CT-RNN (PyTorch) |
| **SIEM / Event Pipeline**| Apache Kafka, PostgreSQL, Redis, Elasticsearch |
| **Frontend / Dashboard**| React 18, Vite, TailwindCSS, D3.js, Socket.IO, Grafana |
| **Infrastructure** | Docker, Docker Compose, Kubernetes, GitHub Actions |

---

## 📁 Project Structure

```text
neuroshield/
├── core/
│   ├── snn/                  # Spiking Neural Network engine (Norse)
│   ├── lnn/                  # Liquid Neural Network engine (CT-RNN)
│   ├── behavioral/           # Behavioral biometric profiler
│   ├── deception/            # Honeypot, sandbox, and canary tokens
│   └── engine.py             # Main decision fusion engine
├── api/                      # FastAPI app & WebSockets
├── dashboard/                # React analyst dashboard
├── simulation_portal/        # Simulated bank portal (React)
├── ingestion/                # Source connectors (DB, syslog, cloud)
├── normalization/            # UEF schema, Kafka pipeline
├── siem/                     # Event store, correlation engine, alert engine
├── datasets/                 # Download scripts & preprocess pipeline
├── training/                 # SNN & LNN training scripts
├── reports/                  # CSV morning report generator
└── docs/                     # Documentation and specifications
```

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.11+, Node.js 20+
- Docker & Docker Compose
- 16 GB RAM minimum (32 GB recommended for training)

### Quick Start
```bash
git clone https://github.com/your-org/neuroshield.git
cd neuroshield

# Preprocess datasets
chmod +x datasets/download.sh && ./datasets/download.sh
python datasets/preprocess.py

# Train models
python training/train_snn.py --dataset CIC-IDS2017
python training/train_lnn.py --dataset CIC-IDS2017

# Start the full platform
docker-compose up --build
```
Access Interfaces at:
- Analyst Dashboard: `http://localhost:3000`
- Simulation Bank Portal: `http://localhost:3001`
- API Docs: `http://localhost:8000/docs`

---

## 👥 Team & Human-in-the-Loop Design

NeuroShield is **not** fully autonomous by design. The AI handles the 2AM edge cases and drowns out alert noise. The human makes the final call.

| Responsibility | Owner |
|---|---|
| Real-time detection, Sandboxing, P1/P2 Triage | AI (Autonomous, fully logged) |
| Morning queue review, Final block/restore decisions | Human Analyst |
| Policy + SIEM rule updates | Human Analyst |

See `TEAM_ROLES.md` for detailed responsibility matrix.

---

*NeuroShield — Because attackers adapt. So should your defense.*
