# Phase 2 — Feature Engine Service

> **Master Plan Reference:** Phase 2 (Week 1–2)
> **Owner:** Backend Lead

---

## What Was Built

### `feature-service/main.py`

A Kafka consumer/producer microservice that sits between ingestion and inference.

**Data flow:**
```
[raw-packets] → Feature Engine → [extracted-features]
```

### Core Logic

| Component | Description |
|---|---|
| `FlowRecord` | Accumulates per-packet data for one bidirectional flow |
| `_flow_key()` | Canonical bidirectional key — smaller IP first, ensures A→B and B→A land in same flow |
| `_janitor()` | Background thread, scans table every 1s, flushes complete/stale flows |
| `extract_features()` | Produces exactly 80 floats from a completed `FlowRecord` |
| LRU eviction | `OrderedDict` capped at 100,000 flows — prevents OOM under DDoS |

### Flow Completion Triggers
1. TCP `FIN` or `RST` flag seen
2. `FLOW_TIMEOUT_SECONDS` (default 3s) of inactivity

### The 80 Features (CICFlowMeter-compatible)

| Range | Category |
|---|---|
| 1–7 | Flow timing + IAT stats |
| 8–19 | Fwd/Bwd packet length stats |
| 20–29 | Fwd/Bwd inter-arrival time stats |
| 30–37 | TCP flag counts (SYN, ACK, FIN, RST, PSH, URG, CWE, ECE) |
| 38–43 | Header lengths + directional packet rates + down/up ratio |
| 44–51 | Packet size stats (min, max, mean, std, variance, avg, seg sizes) |
| 52–59 | Subflow counts + initial window bytes + segment size |
| 60–67 | Active/Idle period statistics |
| 68–71 | PSH/URG flag direction breakdown |
| 72–75 | Percentile features (p25/p75 for fwd and bwd lengths) |
| 76–80 | Flow-level ratios (SYN ratio, ACK ratio, bytes/pkt, pkt variance) |

> **CRITICAL:** The feature order in `FEATURE_NAMES` is the contract between this service and all downstream models. It is saved to `/data/feature_columns.txt` on startup. The preprocessing pipeline and inference service **must** use this exact order.

---

## Checkpoints

### Checkpoint 2A — Feature columns file exists
```bash
docker-compose exec feature cat /data/feature_columns.txt | wc -l
# Expected: 80
```

### Checkpoint 2B — Messages appear on extracted-features
```bash
docker-compose exec kafka kafka-console-consumer \
  --topic extracted-features --bootstrap-server kafka:9092 \
  --max-messages 3 --from-beginning
```
Each message must contain:
- `"features"`: array of **exactly 80 floats**
- `"flow_id"`, `"src_ip"`, `"dst_ip"`, `"n_packets"` keys
- No `null` or `NaN` values

### Checkpoint 2C — Assert in code
```python
assert len(features) == 80  # built into extract_features()
```
If this triggers, the service crashes loudly rather than silently publishing bad data.

---

## Known Issues & Resolutions

| Issue | Resolution |
|---|---|
| Kafka not ready at startup | 10 retries × 15s = 150s total wait (same as kafka_setup) |
| Flow table grows unboundedly under DDoS | LRU eviction at `MAX_FLOWS=100000` (env-configurable) |
| NaN / Inf in features (division by zero on empty flows) | All features sanitized: `0.0 if isnan or isinf` |
| Bidirectional flows split across two keys | `_flow_key()` always puts smaller IP first |
| 80 feature count drift if someone edits list | `assert len(FEATURE_NAMES) == 80` at module load |
| Feature order mismatch with models | `/data/feature_columns.txt` written on startup — compare with model training schema |

---

## Next: Phase 3 — Dataset Preprocessing Pipeline

`datasets/preprocess.py` — unifies CIC-IDS2017/2018, NSL-KDD, CICIoT2023, CICIoMT2024 into `unified_train.csv` and `unified_test.csv` using the **same 80-feature schema** from `feature_columns.txt`.
