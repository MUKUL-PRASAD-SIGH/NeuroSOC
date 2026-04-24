# Phase 0 + 1 — Environment Setup & Ingestion Service

> **Master Plan Reference:** Phase 0 (Days 1–2) + Phase 1 (Week 1)
> **Owner:** DevOps/Research Lead + Backend Lead

---

## What Was Built

### Phase 0 — Scaffold & Docker Compose

| File | Purpose |
|---|---|
| `docker-compose.yml` | 14 services — all env vars inlined, **no `env_file` dependency** |
| `.env.example` | Template only — reference for overrides |
| `.env` | Copy of `.env.example` — exists for optional local overrides |
| `models/model_version.json` | Hot-swap version tracker |
| `monitoring/prometheus.yml` | Scrapes inference + sandbox |
| `data/pcap/` | Pre-created bind-mount target for PCAP files |

#### Directory Structure
```text
neuroshield/
├── ingestion-service/      ✅ IMPLEMENTED (Phase 1)
├── feature-service/        ✅ IMPLEMENTED (Phase 2)
├── inference-service/core/ ⬜ Phase 4–7 (SNN, LNN, XGBoost, Engine)
├── sandbox-service/        ⬜ Phase 10
├── feedback-service/       ⬜ Phase 8
├── retraining-service/     ⬜ Phase 8
├── dashboard/              ⬜ Phase 11
├── simulation_portal/      ⬜ Phase 11
├── datasets/               ⬜ Phase 3
├── models/                 Shared volume (hot-swap)
├── monitoring/             Prometheus config ✅
├── k8s/                    ⬜ Phase 12
├── redteam/                ⬜ Phase 13
└── tests/                  ⬜ Phase 13
```

---

## Phase 1 — Ingestion Service

### `kafka_setup.py`
- Creates 5 topics: `raw-packets` (3p), `extracted-features` (3p), `verdicts`, `feedback`, `alerts`
- **10 retries × 15s = 150s total wait** (Confluent Kafka takes 30–90s to boot)
- Configurable via `KAFKA_SETUP_RETRIES` / `KAFKA_SETUP_DELAY` env vars

### `main.py` — Three ingestion modes

| Mode | Env value | Transport | Use when |
|---|---|---|---|
| `bank_portal` | `INGESTION_MODE=bank_portal` | HTTP POST `/ingest` | **Phase 1 testing — no files needed** |
| `pcap` | `INGESTION_MODE=pcap` | Scapy streams `.pcap` files | Phase 2–3 (realistic traffic) |
| `netflow` | `INGESTION_MODE=netflow` | UDP 2055 | Production NetFlow integration |
| `all` | `INGESTION_MODE=all` (default) | All three concurrently | Full deployment |

### Synthetic fallback
If PCAP mode is selected but `/data/pcap/` contains no `.pcap` files → service **auto-falls back to synthetic generator** (2 packets/sec). Container stays alive, Kafka stays verifiable.

---

## ⚠️ Real-World Issues Encountered & Fixed

### Issue 1 — `.env` file missing → docker-compose crash
**Symptom:** `ERROR: .env not found` when running `docker-compose up`

**Root cause:** Original compose used `env_file: .env` on every service. Docker requires the file to physically exist even if empty.

**Fix applied:** Removed ALL `env_file: .env` references. Every service now has explicit `environment:` block with all required vars inlined.

```yaml
# BEFORE (broken)
env_file: .env

# AFTER (fixed)
environment:
  KAFKA_BOOTSTRAP: kafka:9092
  DATABASE_URL: postgresql://ns_user:ns_pass@postgres:5432/neuroshield
```

> **For future phases:** Never add `env_file: .env` to new services. Inline env vars or use `env_file: .env.example` if you need a reference.

---

### Issue 2 — No PCAP file → nothing published to Kafka
**Symptom:** Ingestion container starts, logs "No .pcap files found", exits silently. Kafka topic empty.

**Fix applied:** No-file case now falls through to **synthetic generator** — emits realistic dummy packets at 2/sec. Service stays up and Kafka is always verifiable.

**For Phase 1 testing:** Use `bank_portal` mode instead — no files at all:
```yaml
# In docker-compose.yml ingestion.environment:
INGESTION_MODE: bank_portal
```

---

### Issue 3 — Kafka healthcheck timing
**Symptom:** Ingestion starts before Kafka is ready → `NoBrokersAvailable` → container crashes on first attempt.

**Fix applied:** Kafka now has a proper `healthcheck`, and all dependent services use `condition: service_healthy`. This guarantees Kafka is accepting connections before any microservice tries to connect.

---

## Phase 1 Checkpoints

### ✅ Checkpoint 1A — Infrastructure up
```bash
docker-compose up -d zookeeper kafka postgres redis
docker-compose ps
# All 4: State = Up (healthy)
```

### ✅ Checkpoint 1B — Kafka topics created
```bash
docker-compose exec kafka kafka-topics --list --bootstrap-server kafka:9092
# Expected output (5 lines):
# alerts
# extracted-features
# feedback
# raw-packets
# verdicts
```

### ✅ Checkpoint 1C — Ingestion publishes (bank_portal mode)
```bash
# Terminal 1: start ingestion
docker-compose up ingestion

# Terminal 2: send a test event
curl -X POST http://localhost:8080/ingest \
  -H "Content-Type: application/json" \
  -d '{"events": [{"src_ip": "192.168.1.1", "dst_ip": "10.0.0.1", "src_port": 54321, "dst_port": 443, "protocol": "TCP", "length": 1200}], "session_id": "test-001", "user_id": "alice"}'

# Terminal 3: confirm Kafka received it
docker-compose exec kafka kafka-console-consumer \
  --topic raw-packets --bootstrap-server kafka:9092 --max-messages 5
# Expected: JSON with packet_id, timestamp, source: "bank_portal"
```

### ✅ Checkpoint 1D — Health endpoint
```bash
curl http://localhost:8080/health
# Expected: {"status":"ok","service":"ingestion","kafka":"kafka:9092","published":N}

curl http://localhost:8080/stats
# Expected: {"published_total":N,"pcap_dir":"/data/pcap","pcap_files":0}
```

---

## Note for Future Phases

| Phase | Needs PCAP? | Notes |
|---|---|---|
| Phase 1 (now) | ❌ No | Use `bank_portal` mode |
| Phase 2 Feature Engine | ❌ No | Consumes Kafka, synthetic packets trigger flows |
| Phase 3 Dataset | ❌ No | Works from downloaded CIC CSVs, not live traffic |
| Phase 4–7 Training | ❌ No | Uses `datasets/processed/unified_train.csv` |
| Phase 11 Red Team | ✅ Yes | Download from Wireshark sample captures |

> To add a real PCAP later: place any `.pcap` file in `./data/pcap/` and set `INGESTION_MODE=pcap`. No rebuild needed — it's a bind-mount.