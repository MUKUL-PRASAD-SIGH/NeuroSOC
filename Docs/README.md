# NeuroShield — Neuromorphic AI Cybersecurity Platform

> **Tagline:** *Thinking like a brain. Defending like a fortress.*
>
> **Architecture Reference:** `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf` — read before setting up any service.
> This document explains why every container in this system is an independent security and scalability boundary.

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Full System Architecture](#2-full-system-architecture)
3. [Microservice Breakdown](#3-microservice-breakdown)
4. [The Hacker vs. The Forgetful User — Behavioral Profiling](#4-the-hacker-vs-the-forgetful-user--behavioral-profiling)
5. [SNN–LNN–XGBoost Detection Ensemble](#5-snnlnnxgboost-detection-ensemble)
6. [Continuous Learning Loop](#6-continuous-learning-loop)
7. [Deception & Sandboxing Layer](#7-deception--sandboxing-layer)
8. [Attack Detection Pipeline](#8-attack-detection-pipeline)
9. [Training Datasets](#9-training-datasets)
10. [Research Backing & Feasibility](#10-research-backing--feasibility)
11. [System Output & Reporting](#11-system-output--reporting)
12. [Simulation Bank Portal](#12-simulation-bank-portal)
13. [Docker Infrastructure](#13-docker-infrastructure)
14. [Kubernetes Production Deployment](#14-kubernetes-production-deployment)
15. [Technology Stack](#15-technology-stack)
16. [Project Structure](#16-project-structure)
17. [Setup & Installation](#17-setup--installation)
18. [Team](#18-team)
19. [Roadmap](#19-roadmap)
20. [What This Document Still Needs](#20-what-this-document-still-needs)
21. [License](#21-license)

---

## 1. Project Overview

**NeuroShield** is an AI-native, neuromorphic cybersecurity platform that fuses **Spiking Neural Networks (SNNs)**, **Liquid Neural Networks (LNNs)**, and **XGBoost gradient boosting** into a three-layer detection ensemble — all running inside an isolated, independently scalable **Docker microservice architecture** backed by **Apache Kafka** as the central event bus.

Unlike rule-based systems, NeuroShield *learns, adapts, and continuously retrains itself* using feedback from real attacker sessions captured in its Docker-isolated sandbox. Every attack the system encounters automatically becomes training data for the next model version.

> **From `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf`:**
> *"Docker enables NeuroShield's distributed microservice architecture by isolating ingestion, detection, sandboxing, and monitoring components into independently scalable and secure containers."*

### What Makes NeuroShield Different?

| Feature | Traditional IDS | ML-Based IDS | NeuroShield |
|---|---|---|---|
| Adaptability | ❌ Static rules | ⚠️ Periodic retraining | ✅ Auto-retraining via live feedback loop |
| Behavioral Biometrics | ❌ | ❌ | ✅ Per-user LNN behavioral fingerprint |
| Neuromorphic Efficiency | ❌ | ❌ | ✅ Event-driven SNN, sub-ms latency |
| Detection Ensemble | Single model | Single model | ✅ SNN + LNN + XGBoost fusion |
| Deception Layer | ❌ | ❌ | ✅ Docker-isolated honeypot + sandbox |
| False Positive Rate | High | Medium | < 1% (HCDS validated) |
| Explainability | Rule trace | Black box | ✅ Per-model causal attribution |
| Scalability | Manual | Manual | ✅ `docker-compose up --scale ingestion=3` |

---

## 2. Full System Architecture

> **Source:** `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf` — "Clean Architecture Diagram" section.

```
┌──────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                               │
│           PCAP  |  NetFlow / IPFIX  |  Logs  |  Bank Portal Events   │
└──────────────────────────────┬───────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│                 INGESTION SERVICE  [Docker Container]                │
│         Collectors │ Parsers │ PCAP Reader │ Scapy                   │
│              Reads raw traffic → publishes to Kafka                  │
│              Scale: docker-compose up --scale ingestion=3            │
└──────────────────────────────┬───────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│                  KAFKA STREAM  [Docker Container]                    │
│            Central Event Bus — decouples ALL services                │
│   Topics: raw-packets │ extracted-features │ verdicts │ feedback     │
│           Services communicate via Kafka ONLY. No direct calls.      │
└──────────────────────────────┬───────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│                 FEATURE ENGINE  [Docker Container]                   │
│      CICFlowMeter-style extraction → exactly 80 CIC features         │
│      Publishes enriched feature vectors to extracted-features topic  │
└──────────────────────────────┬───────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│            DETECTION ENGINE — CORE AI  [Docker Container]           │
│                                                                      │
│   ┌──────────────┐   ┌──────────────┐   ┌─────────────────────────┐│
│   │  SNN Layer   │   │  LNN Layer   │   │  XGBoost + Tree Logic   ││
│   │  (Norse)     │   │  (CT-RNN)    │   │  Ensemble               ││
│   │  < 1ms       │   │  < 50ms      │   │  < 5ms                  ││
│   └──────┬───────┘   └──────┬───────┘   └──────────┬──────────────┘│
│          └──────────────────┴──────────────────────┘               │
│                              ↓                                       │
│                   BEHAVIORAL PROFILER                                │
│         (Typing Rhythm │ Mouse Dynamics │ Nav │ Timing)              │
│                              ↓                                       │
│                      DECISION ENGINE                                 │
│           Weighted Ensemble Fusion → Confidence → Verdict            │
└───────────────────┬──────────────────────────┬───────────────────────┘
                    ↓                          ↓
             NORMAL FLOW               SUSPICIOUS FLOW
                    ↓                          ↓
            ┌──────────┐        ┌──────────────────────────────┐
            │  ALLOW   │        │  SANDBOX  [Docker Container] │
            └──────────┘        │  Docker-isolated decoy app   │
                                │  Attacker sees authentic UI  │
                                │  Real system: unreachable    │
                                └──────────────┬───────────────┘
                                               ↓
                                ┌──────────────────────────────┐
                                │  FEEDBACK ENGINE [Container] │
                                │  Labels attacker sessions    │
                                │  → Kafka feedback topic      │
                                └──────────────┬───────────────┘
                                               ↓
                                ┌──────────────────────────────┐
                                │  RETRAINING SERVICE          │
                                │  [Docker Container]          │
                                │  Batch re-trains SNN, LNN,   │
                                │  XGBoost on new labeled data │
                                └──────────────┬───────────────┘
                                               ↓
                                ┌──────────────────────────────┐
                                │  MODEL STORAGE               │
                                │  Shared Docker volume        │
                                │  ./models → /models          │
                                │  Hot-swap: zero downtime     │
                                └──────────────────────────────┘

┌──────────────────────────────────┐  ┌──────────────────────────────┐
│  DASHBOARD  [Docker Container]   │  │  MONITORING — Grafana        │
│  React UI │ Alerts │ Analytics   │  │  System health │ Traffic     │
│  :3000 Dashboard │ :3001 Bank    │  │  Alert volumes │ Model perf  │
└──────────────────────────────────┘  └──────────────────────────────┘
```

### Kafka: The Nervous System

> **Source:** `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf`:
> *"Kafka is VERY IMPORTANT — it connects everything: Ingestion → Kafka → Feature → Inference"*

Every service communicates exclusively through Kafka topics. No service calls another directly. This architecture means any container can be restarted, upgraded, or scaled without breaking any other.

| Kafka Topic | Producer | Consumer | Payload |
|---|---|---|---|
| `raw-packets` | Ingestion | Feature Engine | Raw PCAP/flow records |
| `extracted-features` | Feature Engine | Inference | 80-feature CIC vectors |
| `verdicts` | Inference | Dashboard, Feedback | ThreatVerdict JSON objects |
| `feedback` | Feedback Engine | Retraining Service | Labeled attack session samples |
| `alerts` | Inference | Dashboard WebSocket | Real-time alert events |

---

## 3. Microservice Breakdown

> **Source:** `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf` — "How Docker Works in Your Project" section.

### Container 1 — Ingestion Service
**Role:** Reads PCAP, NetFlow, log files, and bank portal events. Parses raw traffic and publishes to the `raw-packets` Kafka topic.

**Why Docker:** Runs independently. Can be scaled horizontally for TB/day of ingestion:
```bash
docker-compose up --scale ingestion=3
```

### Container 2 — Feature Engine Service (NEW — from architecture reference)
**Role:** Consumes `raw-packets`; applies CICFlowMeter-style extraction producing exactly 80 bidirectional flow features per record. Publishes to `extracted-features`.

**Why separate from Inference:** Feature extraction is CPU-bound and parallelizable independently from GPU-bound ML inference. Separating them prevents CPU bottleneck from blocking neural network inference.

### Container 3 — Inference Service (Core AI)
**Role:** Loads SNN, LNN, and XGBoost models. Consumes feature vectors, runs the three-model ensemble, applies behavioral profiling, produces verdicts.

**Why Docker:** Isolates all ML dependencies (PyTorch, Norse, XGBoost). Guarantees identical model behavior across laptop, CI runner, and cloud GPU.

### Container 4 — Sandbox Service (Security-Critical)
**Role:** Isolated decoy environment for flagged sessions. Attackers interact with a mirror of the real application but are contained.

> **From `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf`:**
> *"Strong isolation. Attacker cannot escape container. Easy to reset."*
> *"This is actually security-critical."*

The Docker container boundary is a genuine security boundary here. Resetting after each session: `docker-compose restart sandbox`.

### Container 5 — Feedback Engine Service (NEW — from architecture reference)
**Role:** Processes completed sandbox sessions, assigns ground-truth attack-type labels, publishes labeled training examples to the `feedback` Kafka topic.

**Why it matters:** Closes the continuous learning loop — every attack attempt automatically becomes training data.

### Container 6 — Retraining Service (NEW — from architecture reference)
**Role:** Consumes from `feedback` topic. When a configurable batch threshold is reached, triggers retraining of SNN, LNN, and XGBoost. Saves updated weights to the shared `./models` Docker volume.

> **From `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf`:**
> *"Retraining service runs separately. Model update doesn't break system."*

### Container 7 — Dashboard (Frontend)
**Role:** React UI for analyst dashboard (`:3000`) and NovaTrust Bank simulation portal (`:3001`).

### Container 8 — Monitoring (Grafana + Prometheus)
**Role:** Visualizes system health, traffic volumes, alert rates, model performance. Prometheus scrapes all services; Grafana renders dashboards.

> **From architecture reference:** *"Plug-and-play observability."*

---

## 4. The Hacker vs. The Forgetful User — Behavioral Profiling

A critical operational challenge: distinguishing a **malicious actor** from a **legitimate user exhibiting anomalous behavior** (wrong passwords, new device, changed workflows).

### Behavioral Signals Tracked

| Signal | Description | Update Frequency |
|---|---|---|
| **Typing Rhythm** | Inter-keystroke timing, dwell time, bigram latency | Per session |
| **Mouse Dynamics** | Velocity, curvature, click pressure pattern | Per session |
| **Navigation Habits** | Page visit sequences, dwell times, scroll behavior | Daily |
| **Login Timing** | Time-of-day patterns, device fingerprint deltas | Per event |
| **Error Patterns** | Typo frequency, correction behavior | Per session |

### Verdict Logic

```
Δ_behavioral = cosine_distance(current_session_vector, user_profile_vector)

IF Δ_behavioral > 0.70  → HACKER        (sudden, alien behavioral jump)
IF 0.30 < Δ ≤ 0.70      → FORGETFUL_USER (gradual, coherent drift)
IF Δ_behavioral ≤ 0.30  → LEGITIMATE SESSION
```

**Key insight:** A hacker can steal credentials but cannot replicate years of accumulated muscle-memory. The LNN detects the *sudden* discontinuity of an attacker versus the *gradual drift* of a legitimate user changing behavior over time.

### Adaptive Threshold Calibration

Thresholds recalibrate per user via **online Hebbian learning** — a user switching to a new keyboard sees their profile updated without triggering false alarms.

---

## 5. SNN–LNN–XGBoost Detection Ensemble

> **Source:** `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf` — Detection Engine:
> *"SNN + LNN + XGBoost + Tree Logic"*

The detection engine is a **three-model ensemble**. Each model captures a different dimension of the attack signal:

### Layer 1 — Spiking Neural Network (SNN)
- **Strength:** Volume/rate anomalies — DDoS, SYN floods detected in < 1ms per packet
- **Encoding:** Gaussian receptive field spike trains (5 neurons per feature)
- **Learning:** STDP (Spike-Timing Dependent Plasticity) — unsupervised feature learning
- **Hardware:** Intel Loihi 2 (production target), Norse/PyTorch (dev/demo)

### Layer 2 — Liquid Neural Network (LNN)
- **Strength:** Long-range temporal dependencies — APTs, beaconing, slow-burn attacks
- **Architecture:** Continuous-Time RNN (CT-RNN) with 500-neuron random reservoir
- **Training:** Only the readout layer is trained; reservoir weights are fixed (echo state)

### Layer 3 — XGBoost + Tree Logic (NEW from architecture reference)
- **Strength:** High-precision tabular classification on the 80 CIC features; explainable feature importance
- **Tree Logic:** Hard override rules layered on XGBoost predictions:
  `if packet_rate > 10,000/s AND syn_ratio > 0.95 → DDOS regardless of model confidence`
- **Training:** Gradient-boosted on full CIC-IDS2017 + CIC-IDS2018 datasets

### Ensemble Fusion

```python
# Weighted ensemble fusion (weights meta-learned per deployment environment)
snn_score    = snn_detector.anomaly_score(spike_train)           # float [0, 1]
lnn_class    = lnn_classifier.predict_proba(session_sequence)    # array [7 classes]
xgb_class    = xgb_model.predict_proba(feature_vector)           # array [7 classes]
behav_delta  = behavioral_profiler.get_delta(user_id)            # float [0, 1]

confidence   = (0.35 * snn_score
              + 0.30 * lnn_class.max()
              + 0.25 * xgb_class.max()
              + 0.10 * behav_delta)

verdict      = decision_engine.classify(confidence, user_context)
```

---

## 6. Continuous Learning Loop

> **Source:** `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf` — "Continuous learning support":
> *"Retraining service runs separately. Model update doesn't break system."*

```
[Attacker Session Detected]
        ↓
[Sandbox Container — Docker-isolated, no escape]
        ↓  (all actions captured)
[Feedback Engine — assigns ground-truth attack-type label]
        ↓
[Kafka feedback topic — new labeled training sample published]
        ↓
[Retraining Service — waits for configurable batch (e.g. 500 samples)]
        ↓
[Retrains SNN + LNN + XGBoost on new data + historical datasets]
        ↓
[Saves new versioned weights to ./models Docker volume]
        ↓
[Inference Service — detects new model_version.json → hot-swaps weights]
        ↓
[System is now better at detecting the attack pattern that triggered this loop]
```

### Hot-Swap Without Downtime

The Inference container polls `./models/model_version.json` every 60 seconds. When a new version is detected, it loads the new weights in memory before discarding the old ones. If the new model's validation F1 is lower than the previous version, it automatically rolls back. Zero downtime throughout.

---

## 7. Deception & Sandboxing Layer

### Honeypot Network
- Low-interaction honeypots on unused IP space to trap scanners
- High-interaction traps: fake login portals, fake API endpoints mirroring the real bank portal
- Canary Tokens embedded in HTML comments, localStorage, and form fields

### Sandbox Isolation (Docker Security Boundary)
When confidence ≥ 0.7, the session is transparently redirected to the sandbox container:

1. Attacker receives authentic-looking responses from the decoy app
2. The **real system is completely unreachable** — no network route from sandbox to production
3. All attacker actions logged → Feedback Engine → Retraining pipeline
4. Reset after session: `docker-compose restart sandbox` (seconds)

> **Security-critical insight from architecture reference:** The sandbox container runs as a non-root user with `--cap-drop ALL` and a NetworkPolicy (in K8s) restricting egress to the Feedback Engine only. Attacker cannot escape.

### False Positive Rate
Validated at **< 0.9% FPR** via Hybrid Cyber Deception System (HCDS) methodology.

---

## 8. Attack Detection Pipeline

### Supported Attack Categories

| Category | Specific Attacks | Primary Detection Layer |
|---|---|---|
| **DDoS / DoS** | SYN flood, UDP flood, HTTP flood, Slowloris | SNN (rate anomaly) |
| **Reconnaissance** | Port scan, OS fingerprinting, ARP scan | SNN (temporal pattern) |
| **Credential Attacks** | Brute force, credential stuffing, spray | Behavioral Profiler |
| **Web Attacks** | SQL injection, XSS, RCE, SSRF | XGBoost + Tree Logic |
| **APT / Lateral Movement** | Beaconing, exfiltration, privilege escalation | LNN (long-range temporal) |
| **Bot Traffic** | Automated scanning, C2 communication | LNN + XGBoost ensemble |
| **IoT-Specific** | Mirai variants, MQTT exploitation | CICIoT2023-tuned XGBoost |
| **IoMT-Specific** | Medical device spoofing, DICOM attacks | CICIoMT2024-tuned model |

### Real-Time Pipeline (12 Stages)

```
Stage 1:  Ingest    → Ingestion Service reads PCAP/NetFlow → Kafka raw-packets
Stage 2:  Extract   → Feature Engine: 80 CIC features → Kafka extracted-features
Stage 3:  Spike     → SNN encoder: spike train from feature vector (< 1ms)
Stage 4:  SNN       → SNN anomaly score computed
Stage 5:  LNN       → LNN session-level classification (< 50ms)
Stage 6:  XGBoost   → XGBoost tabular classification (< 5ms)
Stage 7:  Profile   → Behavioral delta computation
Stage 8:  Decide    → Weighted ensemble fusion → confidence → verdict
Stage 9:  Act       → ALLOW: log + continue │ SUSPICIOUS: redirect to sandbox
Stage 10: Feedback  → Sandbox session labeled by Feedback Engine → Kafka feedback
Stage 11: Retrain   → Retraining Service batches labels → retrains all three models
Stage 12: Deploy    → Hot-swap updated weights in Inference Service (zero downtime)
```

---

## 9. Training Datasets

| Dataset | Focus | Size | Attack Types |
|---|---|---|---|
| **CIC-IDS2017** | General network intrusion | 2.8M flows | DDoS, DoS, Brute Force, XSS, Infiltration |
| **CSE-CIC-IDS2018** | Modern ML benchmark | 16M+ flows | Above + Bot, Infiltration |
| **CICIoT2023** | IoT network security | 7M+ flows | 33 attack types, 7 categories |
| **CICIoMT2024** | Internet of Medical Things | — | DDoS, DoS, Recon, MQTT, ARP spoofing |
| **NSL-KDD** | Comparative benchmarking | 125K records | DoS, Probe, R2L, U2R |

### Preprocessing Pipeline
1. CICFlowMeter feature extraction → 80 bidirectional flow features
2. Label unification across 5 dataset taxonomies → 7 unified classes
3. SMOTE oversampling for minority attack classes
4. MinMax normalization per feature column
5. Temporal windowing (length 20) for LNN input sequences
6. Gaussian receptive field spike encoding for SNN
7. XGBoost receives raw normalized 80-feature vectors directly (no encoding needed)

---

## 10. Research Backing & Feasibility

### Neuromorphic Intrusion Detection
- **HRSNN:** Up to **99.5% accuracy** on intrusion detection benchmarks (SNN layer ceiling)
- **LNNIDS Framework:** LNNs achieve robust, generalizable attack classification across dataset distributions

### Neuromorphic Cyber Defense
- **Neuromorphic Cyber-Twin (NCT):** SNN integration into digital twin architectures for low-latency adaptive anomaly detection at infrastructure scale

### Deception Technology
- **HCDS:** False positive rate **0.9%** — directly validates the sandbox approach's commercial viability

### Behavioral Biometrics
- Continuous authentication via typing dynamics + mouse: > 97% accuracy, < 2% Equal Error Rate

### Hardware Efficiency
- Intel Loihi 2: **100× energy efficiency** over equivalent GPU inference for SNN workloads

### XGBoost in IDS
- XGBoost on CIC-IDS2017: consistently **> 99% accuracy** with sub-5ms inference — validates its role as the third ensemble member

---

## 11. System Output & Reporting

### Daily CSV Report (Morning Brief — 06:00)

```csv
timestamp, session_id, user_id, source_ip, attack_category, confidence_score,
behavioral_delta, snn_score, lnn_class, xgb_class, verdict,
sandbox_triggered, sandbox_duration_sec, feedback_labeled,
model_version, packets_captured, features_extracted, analyst_notes
```

New fields vs. previous version: `xgb_class`, `feedback_labeled`, `model_version` — reflecting the expanded ensemble and continuous learning loop.

### Verdict Values
- `HACKER` — High confidence; sandboxed; feedback queued for retraining
- `FORGETFUL_USER` — Anomalous but consistent with legitimate drift; soft review
- `LEGITIMATE` — Normal session; logged only
- `INCONCLUSIVE` — Confidence < 0.6; escalated to human analyst

### Real-Time Alert Stream
- WebSocket feed → analyst dashboard
- Severity: INFO / WARNING / CRITICAL / BREACH
- Each alert: which ensemble model triggered it, causal features, recommended action, sandbox replay link

---

## 12. Simulation Bank Portal

A fully functional **NovaTrust Bank** simulated portal deployed for judging and red-team testing.

| Feature | Description |
|---|---|
| `/verdict-display` | Split-screen: attacker view + NeuroShield live analysis |
| Pre-seeded accounts | 3 users with distinct behavioral profiles + 1 admin |
| Live sandbox redirect | HACKER verdict → transparent Docker container redirect |
| Honeypot endpoints | `/api/admin`, `/.env`, `/wp-admin` → CRITICAL alert |
| Canary tokens | In HTML, localStorage, form fields |
| Replay console | Post-session attacker journey replay |

See `SIMULATION_PORTAL_SPEC.md` for complete specification.

---

## 13. Docker Infrastructure

> **Source:** `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf` — Dockerfiles and docker-compose sections.

### Why Docker is Non-Optional

> *"Without Docker → nightmare to run. With Docker → `docker-compose up --build` → spins up your entire SOC system in one command."*
> — `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf`

Without Docker: manually install Python, Node.js, Kafka+Zookeeper, PostgreSQL, Redis, Prometheus, Grafana — with exact version pinning. With Docker: one command.

### Full Service → Container Map

| Service | Image/Build | Port(s) | Key Volume |
|---|---|---|---|
| Zookeeper | `confluentinc/cp-zookeeper:7.5.0` | 2181 | — |
| Kafka | `confluentinc/cp-kafka:7.5.0` | 9092 | — |
| PostgreSQL | `postgres:15-alpine` | 5432 | `postgres_data` |
| Redis | `redis:7-alpine` | 6379 | — |
| Ingestion | `./ingestion-service` | — | `./data:/data` |
| Feature Engine | `./feature-service` | — | `./data:/data` |
| Inference (Core AI) | `./inference-service` | 8000 | `./models:/models` |
| Sandbox | `./sandbox-service` | 8001 | — |
| Feedback Engine | `./feedback-service` | — | `./data:/data` |
| Retraining | `./retraining-service` | — | `./data:/data`, `./models:/models` |
| Dashboard | `./dashboard` | 3000 | — |
| Bank Portal | `./simulation_portal` | 3001 | — |
| Prometheus | `prom/prometheus:latest` | 9090 | `./monitoring/prometheus.yml` |
| Grafana | `grafana/grafana:latest` | 3002 | `grafana_data` |

### Per-Service Dockerfiles

> **Source:** `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf` — Dockerfiles section.

**Ingestion / Feature / Feedback (lightweight Python):**
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

**Inference Service (ML-heavy):**
```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install torch xgboost joblib norse -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

**Sandbox Service (security-hardened):**
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN useradd -m sandbox_user && chown -R sandbox_user /app
USER sandbox_user
CMD ["python", "main.py"]
# Deploy with: --cap-drop ALL --security-opt no-new-privileges:true
```

**Retraining Service:**
```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "retrain.py"]
```

**Dashboard / Bank Portal (React + Nginx, multi-stage):**
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json .
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### Scaling

```bash
# Handle TB/day traffic with 3 ingestion nodes
docker-compose up --scale ingestion=3

# Parallel inference for demo load
docker-compose up --scale inference=2

# Hot-swap model — zero downtime
cp new_weights/snn_best.pt ./models/snn_best.pt
# Inference container detects new model_version.json and hot-loads within 60s

# Safe experimentation — break one, others keep running
docker-compose restart inference

# Reset sandbox between demo runs
docker-compose restart sandbox
```

### docker-compose.yml Structure

```yaml
version: '3.8'
services:
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    ports: ["9092:9092"]
    depends_on: [zookeeper]

  ingestion:
    build: ./ingestion-service
    depends_on: [kafka]

  feature:
    build: ./feature-service
    depends_on: [kafka]

  inference:
    build: ./inference-service
    volumes: [./models:/models]
    depends_on: [kafka, postgres, redis]

  sandbox:
    build: ./sandbox-service
    security_opt: [no-new-privileges:true]
    cap_drop: [ALL]

  feedback:
    build: ./feedback-service
    volumes: [./data:/data]
    depends_on: [kafka]

  retraining:
    build: ./retraining-service
    volumes:
      - ./data:/data
      - ./models:/models

  dashboard:
    build: ./dashboard
    ports: ["3000:80"]

  simulation_portal:
    build: ./simulation_portal
    ports: ["3001:80"]

  grafana:
    image: grafana/grafana:latest
    ports: ["3002:3000"]
```

---

## 14. Kubernetes Production Deployment

> **Source:** `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf` — Kubernetes section:
> *"Docker = local / small scale. Kubernetes = real-world scale."*
> *"Your system handles TB/day logs, needs scaling, needs fault tolerance."*

### Docker → Kubernetes Mapping

| Docker Compose | Kubernetes |
|---|---|
| Container | Pod |
| Service definition | Deployment |
| Service name (DNS) | Kubernetes Service |
| Volume mount | PersistentVolumeClaim |
| `--scale N` | `replicas: N` |
| Network | Namespace + NetworkPolicy |

### Inference Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
  namespace: neuroshield
spec:
  replicas: 3
  selector:
    matchLabels:
      app: inference
  template:
    metadata:
      labels:
        app: inference
    spec:
      containers:
      - name: inference
        image: neuroshield/inference:latest
        ports:
        - containerPort: 8000
        volumeMounts:
        - name: models
          mountPath: /models
      volumes:
      - name: models
        persistentVolumeClaim:
          claimName: models-pvc
```

### Horizontal Pod Autoscaler

```yaml
# From docs/DOCKER_ARCHITECTURE_REFERENCE.pdf
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa
  namespace: neuroshield
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

> *"System scales when traffic increases."* — `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf`

### Sandbox Network Policy

```yaml
# Enforces at kernel level: sandbox can ONLY talk to feedback-service
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sandbox-isolation
  namespace: neuroshield
spec:
  podSelector:
    matchLabels:
      app: sandbox
  policyTypes: [Egress]
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: feedback
```

---

## 15. Technology Stack

### Core AI / ML
| Component | Technology |
|---|---|
| Language | Python 3.10 / 3.11 |
| SNN Framework | Norse (PyTorch-based) |
| LNN Framework | Custom CT-RNN (PyTorch 2.x) |
| Ensemble Model 3 | **XGBoost 2.x** |
| Feature Extraction | CICFlowMeter, Scapy |
| Neuromorphic HW | Intel Loihi 2 (production target) |
| ML Ops | joblib, Weights & Biases (optional) |

### Streaming & Data
| Component | Technology |
|---|---|
| Central Event Bus | **Apache Kafka (Confluent 7.5)** |
| Coordination | Apache Zookeeper |
| Session State | Redis 7 |
| Event Storage | PostgreSQL 15 |

### API & Backend
| Component | Technology |
|---|---|
| API Framework | FastAPI + uvicorn |
| Async DB | asyncpg |
| Real-time | Native WebSocket |
| Reporting | SMTP (SendGrid) |

### Frontend
| Component | Technology |
|---|---|
| Framework | React 18 + TypeScript + Vite |
| Styling | TailwindCSS |
| Charts | Recharts + D3.js |
| Maps | Leaflet.js |

### Infrastructure
| Component | Technology |
|---|---|
| Containers | Docker + Docker Compose v3.8 |
| Production Orchestration | Kubernetes |
| Autoscaling | Kubernetes HPA |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus + Grafana |

---

## 16. Project Structure

```
neuroshield/
│
├── ingestion-service/            # Container 1: Traffic collection & parsing
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
│
├── feature-service/              # Container 2: CIC feature extraction (80 features)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
│
├── inference-service/            # Container 3: Core AI detection (SNN+LNN+XGBoost)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                   # Kafka consumer → ensemble → Kafka producer
│   ├── core/
│   │   ├── snn/
│   │   │   ├── encoder.py
│   │   │   ├── network.py
│   │   │   └── stdp.py
│   │   ├── lnn/
│   │   │   ├── reservoir.py
│   │   │   └── classifier.py
│   │   ├── xgboost/
│   │   │   ├── model.py          # XGBoost wrapper + predict_proba
│   │   │   └── tree_logic.py     # Hard rule overrides
│   │   ├── behavioral/
│   │   │   ├── profiler.py
│   │   │   ├── signals.py
│   │   │   └── comparator.py
│   │   └── engine.py             # Ensemble fusion decision engine
│   └── api/
│       ├── main.py               # FastAPI app + WebSocket
│       └── routes/
│
├── sandbox-service/              # Container 4: Docker-isolated attacker decoy
│   ├── Dockerfile                # Non-root, cap-drop ALL
│   ├── requirements.txt
│   └── main.py
│
├── feedback-service/             # Container 5: Ground-truth labeling engine
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
│
├── retraining-service/           # Container 6: Continuous model updater
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── retrain.py                # Main retraining orchestrator
│   ├── train_snn.py
│   ├── train_lnn.py
│   └── train_xgboost.py
│
├── dashboard/                    # Container 7: Analyst React UI
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│
├── simulation_portal/            # Container 8: NovaTrust Bank demo
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│
├── datasets/
│   ├── download.sh
│   └── preprocess.py
│
├── models/                       # Shared Docker volume
│   ├── snn_best.pt
│   ├── lnn_best.pt
│   ├── xgboost_best.json
│   └── model_version.json        # Hot-swap version tracker
│
├── monitoring/
│   └── prometheus.yml
│
├── k8s/                          # Kubernetes manifests (production)
│   ├── inference-deployment.yaml
│   ├── inference-hpa.yaml
│   ├── sandbox-networkpolicy.yaml
│   └── ...
│
├── redteam/
│   ├── attack_brute_force.py
│   ├── attack_ddos.py
│   ├── attack_normal_user.py
│   ├── seed_profiles.py
│   └── reset_demo.py
│
├── docs/
│   ├── MASTER_PLAN.md
│   ├── TEAM_ROLES.md
│   ├── ANTIGRAVITY_PROMPTS.md
│   ├── SIMULATION_PORTAL_SPEC.md
│   ├── EXTERNAL_INTEGRATIONS.md
│   └── DOCKER_ARCHITECTURE_REFERENCE.pdf   ← source reference doc
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 17. Setup & Installation

### Prerequisites
- Docker Engine 24+ and Docker Compose v2
- Python 3.10+ (for local training scripts)
- Node.js 20+ (for local frontend dev only)
- 16 GB RAM minimum; 32 GB recommended for training
- CUDA GPU optional (inference runs on CPU if unavailable)

### Quick Start

```bash
# 1. Clone
git clone https://github.com/your-org/neuroshield.git && cd neuroshield

# 2. Configure environment
cp .env.example .env   # Edit with your values (see EXTERNAL_INTEGRATIONS.md)

# 3. Start everything (14 containers)
docker-compose up --build

# 4. Seed behavioral profiles for demo accounts (run once after first startup)
docker-compose exec inference python /app/redteam/seed_profiles.py

# 5. Access interfaces
# Analyst Dashboard:       http://localhost:3000
# NovaTrust Bank Portal:   http://localhost:3001
# API Docs:                http://localhost:8000/docs
# Grafana Monitoring:      http://localhost:3002
# Prometheus:              http://localhost:9090

# 6. Scale for high-volume demo
docker-compose up --scale ingestion=3

# 7. Reset demo between judge runs
docker-compose exec inference python /app/redteam/reset_demo.py
```

### Environment Variables

```env
# Kafka (use Docker service names, not localhost)
KAFKA_BOOTSTRAP=kafka:9092
KAFKA_TOPIC_RAW=raw-packets
KAFKA_TOPIC_FEATURES=extracted-features
KAFKA_TOPIC_VERDICTS=verdicts
KAFKA_TOPIC_FEEDBACK=feedback
KAFKA_TOPIC_ALERTS=alerts

# Database
DATABASE_URL=postgresql://ns_user:ns_pass@postgres:5432/neuroshield
REDIS_URL=redis://redis:6379

# Models
MODEL_PATH=/models
MODEL_VERSION_FILE=/models/model_version.json
RETRAIN_BATCH_SIZE=500

# Reporting
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASS=SG.your_key
REPORT_TO=analyst@yourorg.com

# Security
API_KEY=your_long_random_key
SANDBOX_TIMEOUT_SEC=300
```

---

## 18. Team

| Role | Primary Ownership |
|---|---|
| **ML/AI Lead** | SNN + LNN + XGBoost training, inference-service core, behavioral profiler, retraining-service |
| **Backend Lead** | Feature-service, feedback-service, Kafka pipeline, FastAPI, sandbox logic, PostgreSQL schema |
| **Frontend Lead** | Dashboard (`:3000`), bank portal (`:3001`), WebSocket UI, behavioral tracker hook |
| **DevOps / Research Lead** | All Dockerfiles, docker-compose.yml, K8s manifests, CI/CD, dataset curation, research validation |

See `TEAM_ROLES.md` for full RACI matrix, week-by-week sprint plan, and risk register.

---

## 19. Roadmap

### Phase 1 — Environment & Data (Weeks 1–2)
- [ ] All Dockerfiles building cleanly
- [ ] Dataset download + preprocessing pipeline
- [ ] Kafka topics created, producer/consumer tested

### Phase 2 — Ingestion + Feature (Week 2–3)
- [ ] Ingestion Service reads PCAP/NetFlow → Kafka
- [ ] Feature Engine extracts 80 CIC features → Kafka

### Phase 3 — Core AI (Weeks 3–5)
- [ ] SNN encoder + STDP training
- [ ] LNN reservoir + supervised readout
- [ ] XGBoost training on CIC-IDS2017
- [ ] Ensemble fusion decision engine

### Phase 4 — Continuous Learning (Weeks 5–6)
- [ ] Sandbox service (Docker-isolated, security-hardened)
- [ ] Feedback Engine (labeling pipeline → Kafka)
- [ ] Retraining Service (batch retrain + hot-swap)

### Phase 5 — Interfaces (Weeks 7–8)
- [ ] Analyst dashboard (React, WebSocket)
- [ ] NovaTrust Bank simulation portal
- [ ] Judge split-screen verdict display

### Phase 6 — Testing + Demo (Weeks 9–12)
- [ ] All integration tests passing
- [ ] Red-team runs (4 scenarios)
- [ ] Benchmark evaluation (all 5 datasets)
- [ ] Kubernetes manifests complete
- [ ] Demo script rehearsed 3+ times

---

## 20. What This Document Still Needs

> Track these gaps before treating this README as a complete project reference.

| Missing Item | Priority | Owner |
|---|---|---|
| **model_version.json schema** — exact format, hot-swap trigger logic, rollback conditions | 🔴 High | ML/AI Lead |
| **Kafka topic schemas** — exact JSON structure for each of the 5 topics | 🔴 High | Backend Lead |
| **XGBoost hyperparameter table** — learning_rate, max_depth, n_estimators, colsample_bytree | 🔴 High | ML/AI Lead |
| **Retraining trigger conditions** — batch size, min F1 delta to accept new model | 🔴 High | ML/AI Lead |
| **Actual benchmark results** — achieved F1, accuracy, FPR (not just literature claims) | 🔴 High | ML/AI Lead |
| **Sandbox hardening checklist** — complete `--cap-drop` flags, seccomp profile, K8s NetworkPolicy | 🔴 High | DevOps Lead |
| **Grafana dashboard JSON** — import-ready file for all monitoring views | 🟡 Medium | DevOps Lead |
| **Failure mode playbook** — what happens if Kafka crashes, inference OOMs, sandbox fails | 🟡 Medium | DevOps Lead |
| **API auth spec** — key rotation procedure, which endpoints are public vs authenticated | 🟡 Medium | Backend Lead |
| **Data retention policy** — how long sandbox logs, verdicts, behavioral profiles are kept | 🟡 Medium | Backend Lead |
| **Feedback Engine labeling logic** — how ground-truth attack-type labels are assigned to sandbox sessions | 🟡 Medium | ML/AI Lead |
| **GDPR / privacy notice** — for behavioral data collection from demo participants | 🟢 Low | All |
| **CONTRIBUTING.md** — for post-hackathon contributors | 🟢 Low | DevOps Lead |
| **Video demo link** — 5-min walkthrough of all 4 judge scenarios | 🟢 Low | All |

---

## 21. License

MIT License. See `LICENSE` for details.

---

*NeuroShield — Because attackers adapt. So should your defense.*
*Architecture reference: `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf`*
