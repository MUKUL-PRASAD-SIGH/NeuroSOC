# MASTER PLAN — NeuroShield Development via Antigravity Vibe Coding

> **Platform:** Antigravity (AI-powered vibe coding environment)
> **Architecture Reference:** `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf` — read before starting Phase 0.
> This plan is the implementation schedule for the system described in that document and the README.
>
> **Team Size:** 4 members
> **Total Duration:** 12 weeks
> **Deliverables:** 8 Docker microservices + Analyst Dashboard + Simulation Bank Portal + Complete CI/CD

---

## How to Read This Document

Each phase has:
- **Objective** — What we're building
- **Subphases** — Granular steps
- **Antigravity Prompt** — Exact text to paste
- **Expected Output** — What Antigravity should generate
- **Potential Issues** — What might go wrong
- **Issue Resolutions** — How to fix them
- **External Work** — Tasks Antigravity cannot do (manual)
- **Testing Gate** — Must pass before next phase

---

## Architecture Context (Read First)

As described in `DOCKER_ARCHITECTURE_REFERENCE.pdf`, the full data flow is:

```
Ingestion → Kafka → Feature Engine → Inference (SNN+LNN+XGBoost) → Decision Engine
→ ALLOW or SANDBOX → Feedback Engine → Retraining Service → Model Update (hot-swap)
```

Every stage is a separate Docker container. Kafka is the only communication channel between services. This plan builds them in order of data flow dependency.

---

## ⚠️ Operational Lessons (Updated from Implementation — Read Before Each Phase)

These were discovered during Phase 0–1 implementation. Apply to ALL future phases.

| # | Lesson | Rule |
|---|---|---|
| 1 | **Never use `env_file: .env`** | All docker-compose services must use explicit `environment:` blocks. `.env` is optional override only. Missing `.env` crashes compose entirely. |
| 2 | **Don't use PCAP for Phase 1 testing** | Use `INGESTION_MODE=bank_portal`. No files needed. PCAP only needed Phase 11+ (red team). |
| 3 | **Kafka needs a real healthcheck** | `depends_on: - kafka` alone is NOT enough. Kafka takes 30–90s to boot. Always use `condition: service_healthy` with the `kafka-topics --list` healthcheck. |
| 4 | **Ingestion port is 8080, not 8000** | API (FastAPI inference service) is on 8000. Ingestion HTTP endpoint is on 8080. Curl test target: `http://localhost:8080/ingest` |
| 5 | **Feature columns order is a contract** | `/data/feature_columns.txt` defines the 80-feature order. ALL models (SNN, LNN, XGBoost) must use this exact order. Never reorder without retraining. |
| 6 | **Empty PCAP dir → synthetic fallback** | Ingestion auto-generates synthetic packets if no `.pcap` files exist. Kafka is always verifiable. |
| 7 | **Flow table LRU cap** | Feature engine caps at 100k flows. Under DDoS simulation, reduce `FLOW_TIMEOUT_SECONDS` to 1 for faster eviction. |

---

## PHASE 0 — Repository & Environment Setup
**Duration:** Day 1–2 | **Owner:** DevOps/Research Lead

### Subphase 0.1 — Repository Scaffold (Manual — External)

```bash
gh repo create neuroshield --private --clone && cd neuroshield

# Create all 8 service directories (from architecture reference)
mkdir -p ingestion-service feature-service inference-service/core/{snn,lnn,xgboost,behavioral} \
         inference-service/api/routes sandbox-service feedback-service \
         retraining-service dashboard/src simulation_portal/src \
         datasets models monitoring k8s redteam docs

# Python environments per service
for svc in ingestion-service feature-service inference-service sandbox-service feedback-service retraining-service; do
  touch $svc/requirements.txt $svc/main.py $svc/Dockerfile
done

# Frontend scaffolds
cd dashboard && npm create vite@latest . -- --template react-ts && cd ..
cd simulation_portal && npm create vite@latest . -- --template react-ts && cd ..

# Model version file (needed for hot-swap)
echo '{"version": "0.0.0", "snn": null, "lnn": null, "xgboost": null}' > models/model_version.json

git add . && git commit -m "chore: initial scaffold — 8 service structure"
```

**Expected output:** Clean repo matching the structure in README.md Section 16.

**Potential Issues:**
- Kafka requires Java → Install OpenJDK 17 before any Kafka-related testing
- Norse installation on Windows → Use WSL2 or a cloud Linux VM

---

### Subphase 0.2 — Docker Compose (Antigravity)

**Antigravity Prompt:**
```
Create a Docker Compose v3.8 file for NeuroShield — a microservice cybersecurity platform.
Reference architecture: 14 services, all on a shared bridge network called neuroshield-net.

Services:
1. zookeeper: image confluentinc/cp-zookeeper:7.5.0, port 2181, 
   ZOOKEEPER_CLIENT_PORT=2181, ZOOKEEPER_TICK_TIME=2000

2. kafka: image confluentinc/cp-kafka:7.5.0, port 9092, depends_on: zookeeper,
   KAFKA_BROKER_ID=1, KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181,
   KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092,
   KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1,
   KAFKA_AUTO_CREATE_TOPICS_ENABLE=true

3. postgres: image postgres:15-alpine, port 5432, 
   POSTGRES_DB=neuroshield, POSTGRES_USER=ns_user, POSTGRES_PASSWORD=ns_pass,
   volume postgres_data:/var/lib/postgresql/data,
   healthcheck: pg_isready -U ns_user every 10s

4. redis: image redis:7-alpine, port 6379,
   healthcheck: redis-cli ping every 10s

5. ingestion: build ./ingestion-service, depends_on: [kafka],
   volumes: ./data:/data, env_file: .env

6. feature: build ./feature-service, depends_on: [kafka],
   volumes: ./data:/data, env_file: .env

7. inference: build ./inference-service, ports: 8000:8000,
   depends_on: [kafka, postgres, redis] (all healthy),
   volumes: ./models:/models, env_file: .env

8. sandbox: build ./sandbox-service, ports: 8001:8001,
   security_opt: [no-new-privileges:true], cap_drop: [ALL],
   env_file: .env

9. feedback: build ./feedback-service, depends_on: [kafka],
   volumes: ./data:/data, env_file: .env

10. retraining: build ./retraining-service,
    volumes: [./data:/data, ./models:/models], env_file: .env

11. dashboard: build ./dashboard, ports: 3000:80

12. simulation_portal: build ./simulation_portal, ports: 3001:80

13. prometheus: image prom/prometheus:latest, port 9090,
    volumes: ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

14. grafana: image grafana/grafana:latest, ports: 3002:3000,
    volumes: grafana_data:/var/lib/grafana,
    GF_SECURITY_ADMIN_PASSWORD=neuroshield_admin

Named volumes: postgres_data, grafana_data
Output ONLY docker-compose.yml. No explanation text.
```

**Expected Output:** Complete `docker-compose.yml` with all 14 services, proper `depends_on`, health checks, volumes, security_opt for sandbox.

**Potential Issues:**
1. Confluent Kafka image may need `KAFKA_LISTENERS` in addition to `KAFKA_ADVERTISED_LISTENERS` → Add `KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092`
2. `depends_on` with `condition: service_healthy` requires health checks to be defined — verify postgres and redis health checks exist
3. `cap_drop: [ALL]` syntax in Compose v3.8 uses list format, not string

**Verify with:** `docker-compose config` → no YAML errors printed.

**Testing Gate 0:** `docker-compose up postgres redis kafka zookeeper` → all four start cleanly. Kafka topic creation works: `docker-compose exec kafka kafka-topics --create --topic raw-packets --bootstrap-server kafka:9092`

---

## PHASE 1 — Kafka Topic Setup & Ingestion Service
**Duration:** Week 1 | **Owner:** Backend Lead

### Subphase 1.1 — Kafka Topic Initialization (Antigravity)

**Antigravity Prompt:**
```
Write a Python script called ingestion-service/kafka_setup.py that:
1. Connects to Kafka at KAFKA_BOOTSTRAP env var (default: kafka:9092)
2. Creates these topics if they don't exist, using kafka-python AdminClient:
   - raw-packets: 3 partitions, replication_factor=1
   - extracted-features: 3 partitions, replication_factor=1
   - verdicts: 1 partition, replication_factor=1
   - feedback: 1 partition, replication_factor=1
   - alerts: 1 partition, replication_factor=1
3. Prints confirmation: "Topic [name] created" or "Topic [name] already exists"
4. Exits with code 0 on success, 1 on connection failure (with helpful error message)
Use kafka-python library. Add retry logic: try 3 times with 5s delay before giving up.
Run this as an init step in the ingestion service Dockerfile CMD:
CMD ["sh", "-c", "python kafka_setup.py && python main.py"]
```

**Potential Issues:**
1. Kafka not ready when script runs → The retry logic handles this, but increase to 5 retries with 10s delay for Docker startup timing
2. `NewTopic` vs `CreateTopicsRequest` API — use `NewTopic` from `kafka.admin`

### Subphase 1.2 — Ingestion Service (Antigravity)

**Antigravity Prompt:**
```
Write ingestion-service/main.py — a Kafka producer service for NeuroShield.

The service reads network traffic and publishes to the raw-packets Kafka topic.

PCAP mode (reads from file or live capture):
- Uses Scapy to read PCAP files from /data/pcap/ directory (glob *.pcap)
- For each packet: extracts fields: src_ip, dst_ip, src_port, dst_port, protocol, 
  length, timestamp, flags (TCP SYN/ACK/FIN), ttl
- Publishes to Kafka topic 'raw-packets' as JSON: 
  {packet_id: uuid, timestamp: float, src_ip, dst_ip, src_port, dst_port, 
   protocol: str, length: int, flags: dict, ttl: int, source: 'pcap'}

NetFlow mode (receives JSON NetFlow records via UDP port 2055):
- Listens on UDP 2055, receives JSON NetFlow records
- Publishes to same Kafka topic with source: 'netflow'

Bank Portal mode (receives behavioral events via HTTP POST /ingest):
- FastAPI endpoint POST /ingest that accepts a list of event dicts
- Publishes to raw-packets with source: 'bank_portal'

Configuration via environment variables:
- KAFKA_BOOTSTRAP (default: kafka:9092)
- INGESTION_MODE: 'pcap', 'netflow', 'bank_portal', or 'all' (default: all)
- DATA_DIR: /data/pcap (for pcap mode)

Use kafka-python KafkaProducer. Include proper error handling and a main() entrypoint.
Log every 1000 packets published: "Published 1000 packets to raw-packets"
```

**Expected Output:** `main.py` with three ingestion modes, Kafka producer.

**Potential Issues:**
1. Scapy requires root for live capture → In Docker, either run with `--cap-add NET_RAW` or use pcap file replay only
2. NetFlow UDP listener and FastAPI HTTP server need to run concurrently → Use `asyncio` + `uvicorn` for FastAPI, `threading` for UDP listener
3. PCAP files may be large — process in chunks, don't load entire file into memory

**Testing Gate 1:** `docker-compose exec kafka kafka-console-consumer --topic raw-packets --bootstrap-server kafka:9092 --max-messages 10` shows JSON packet records after running the ingestion service against a sample PCAP file.

---

## PHASE 2 — Feature Engine Service
**Duration:** Week 1–2 | **Owner:** Backend Lead

> **New service added from `DOCKER_ARCHITECTURE_REFERENCE.pdf`:** The Feature Engine is separate from Inference because feature extraction is CPU-bound and must be independently scalable.

### Subphase 2.1 — CIC Feature Extractor (Antigravity)

**Antigravity Prompt:**
```
Write feature-service/main.py — a Kafka consumer/producer service that extracts 
CICFlowMeter-style features from raw packet data.

The service:
1. Consumes from Kafka topic 'raw-packets' (group_id='feature-engine')
2. Groups packets into bidirectional flows by (src_ip, dst_ip, src_port, dst_port, protocol) tuple
   — a flow is complete when: 3 seconds of inactivity OR TCP FIN/RST flag seen
3. For each complete flow, extracts these 80 features (based on CICFlowMeter):
   Flow duration, total fwd packets, total bwd packets, fwd packets length total,
   bwd packets length total, fwd packet length max/min/mean/std, bwd packet length max/min/mean/std,
   flow bytes/s, flow packets/s, flow IAT mean/std/max/min, fwd IAT total/mean/std/max/min,
   bwd IAT total/mean/std/max/min, fwd PSH flags, bwd PSH flags, fwd URG flags, bwd URG flags,
   fwd header length, bwd header length, fwd packets/s, bwd packets/s,
   min packet length, max packet length, packet length mean/std/variance,
   FIN flag count, SYN flag count, RST flag count, PSH flag count,
   ACK flag count, URG flag count, CWE flag count, ECE flag count,
   down_up_ratio, avg packet size, avg fwd segment size, avg bwd segment size,
   fwd header length again, subflow fwd packets/bytes, subflow bwd packets/bytes,
   init_win_bytes_forward, init_win_bytes_backward, act_data_pkt_fwd,
   min_seg_size_forward, active mean/std/max/min, idle mean/std/max/min
   (Fill remaining features to reach exactly 80 with zeros if needed — log a warning)
4. Publishes extracted feature vector to Kafka topic 'extracted-features' as JSON:
   {flow_id: str, src_ip, dst_ip, src_port, dst_port, protocol, 
    features: [80 floats], timestamp: float, n_packets: int}
5. Uses collections.defaultdict to accumulate flow state
6. Background thread cleans up stale flows (> 3s inactive) every second

Use kafka-python KafkaConsumer + KafkaProducer.
Configuration from env: KAFKA_BOOTSTRAP, FLOW_TIMEOUT_SECONDS (default: 3)
Log every 100 flows extracted.
```

**Expected Output:** Complete `main.py` with flow accumulation, 80-feature extraction, Kafka consumer/producer.

**Potential Issues:**
1. 80 features is a lot — Antigravity may only implement ~40. Verify count with `assert len(features) == 80`
2. Flow state accumulation will grow unboundedly for DDoS traffic (millions of flows) → Limit flow table to 100,000 entries using `collections.OrderedDict` with LRU eviction
3. Scapy packet deserialization from JSON loses some fields → Ensure ingestion service includes all needed fields in the raw JSON

**Testing Gate 2:** Consume 10 messages from `extracted-features` topic. Each must be a dict with `features` array of exactly 80 floats, no NaN values.

---

## PHASE 3 — Dataset Pipeline
**Duration:** Week 1–2 | **Owner:** DevOps/Research Lead + ML/AI Lead

### Subphase 3.1 — Dataset Download (Manual — External)

Register and download from https://www.unb.ca/cic/ (free, requires account):
- CIC-IDS2017 → `datasets/raw/CIC-IDS2017/`
- CSE-CIC-IDS2018 → `datasets/raw/CIC-IDS2018/`
- CICIoT2023 → `datasets/raw/CICIoT2023/`
- CICIoMT2024 → `datasets/raw/CICIoMT2024/`

NSL-KDD (no registration):
```bash
wget https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTrain+.txt -P datasets/raw/NSL-KDD/
```

### Subphase 3.2 — Preprocessing Pipeline (Antigravity)

**Antigravity Prompt:**
```
Write datasets/preprocess.py that unifies all 5 CIC datasets into one training set.

1. Recursively loads all CSV files from datasets/raw/ (handle utf-8 and latin-1 encoding)
2. Strips whitespace from all column names, converts to snake_case
3. Drops columns with >50% nulls or inf; fills remaining with column median
4. Maps labels to 7 unified classes:
   - 'DDoS' or 'DoS' (case-insensitive) → 'DDOS'
   - 'Brute' → 'BRUTE_FORCE'
   - 'Scan' or 'Probe' or 'Recon' → 'RECONNAISSANCE'
   - 'XSS' or 'SQL' or 'Web' or 'Injection' → 'WEB_ATTACK'
   - 'Bot' → 'BOT'
   - 'BENIGN' or 'Normal' or 'Benign' → 'BENIGN'
   - All others → 'OTHER'
5. Keeps only numeric columns + label column
6. Applies MinMaxScaler (save to datasets/scaler.pkl via joblib)
7. Applies SMOTE (sampling_strategy='minority', min 1000 samples per class)
8. Stratified 80/20 train/test split
9. Saves: datasets/processed/unified_train.csv, unified_test.csv
10. Saves column list to datasets/feature_columns.txt (one per line)
11. Prints class distribution before and after SMOTE

Handle FileNotFoundError gracefully. Add chunked reading (chunksize=100000) for large files.
Guard with if __name__ == '__main__'.
```

**Potential Issues:**
1. SMOTE on 16M rows will OOM → Stratified subsample to 500k rows before SMOTE for dev; use full data only for final training run
2. Column name differences across datasets → Antigravity may not know exact CIC schemas; manually check after running

**Testing Gate 3:** `python preprocess.py` → both CSVs exist; `head -1 unified_train.csv` shows columns; no NaN in output (`pd.read_csv().isna().sum().sum() == 0`).

---

## PHASE 4 — SNN Engine
**Duration:** Week 2–3 | **Owner:** ML/AI Lead

### Subphase 4.1 — Spike Encoder (Antigravity)

**Antigravity Prompt:**
```
Write inference-service/core/snn/encoder.py using PyTorch 2.x and Norse library.

Class SpikeEncoder:
- __init__(self, n_features=80, n_neurons_per_feature=5, T=100)
- _create_gaussian_receptive_fields(): 
  n_neurons_per_feature Gaussian RFs per feature, centers evenly spaced [0,1],
  sigma = 1/(2 * n_neurons_per_feature)
- encode(features: np.ndarray) -> torch.Tensor:
  Input [batch, n_features] (normalized 0-1)
  Gaussian activation per RF → Bernoulli spike sampling over T timesteps
  Output [T, batch, n_features * n_neurons_per_feature]  i.e. [100, batch, 400]
- encode_deterministic(features) -> torch.Tensor: rate coding, same output shape
- decode(spike_train) -> np.ndarray: mean firing rate per group → [batch, n_features]

Test block: encode batch of 4 samples, assert output shape == torch.Size([100, 4, 400])
```

**Potential Issues:**
1. Norse API version → Pin `norse==0.0.7` in requirements.txt
2. Output shape transposition common mistake → Verify [T, batch, features] order, not [batch, T, features]

### Subphase 4.2 — SNN Network + Training (Antigravity)

**Antigravity Prompt:**
```
Write two files:

FILE 1: inference-service/core/snn/network.py
Class SNNAnomalyDetector(torch.nn.Module):
- LIF hidden layers (Norse LIFRecurrentCell): 400 → 256 → 128 neurons
- Linear readout: 128 → 7 (one per class)
- forward(spike_train [T, batch, 400]) -> (logits [batch, 7], anomaly_score [batch])
  anomaly_score = 1.0 - softmax(logits)[:, 0]  (index 0 = BENIGN)
- CLASS_NAMES = ['BENIGN','DDOS','BRUTE_FORCE','RECONNAISSANCE','WEB_ATTACK','BOT','OTHER']
- save(path) and load(path) class method

FILE 2: retraining-service/train_snn.py
- Loads datasets/processed/unified_train.csv
- Instantiates SpikeEncoder + SNNAnomalyDetector
- Trains 50 epochs, Adam lr=1e-3, CrossEntropyLoss
- STDP post-hoc: after optimizer.step(), strengthen weights of co-firing neuron pairs
  (both fired in same 5-timestep window, co-activation threshold > 0.7)
- Saves best checkpoint to /models/snn_best.pt based on validation F1
- Saves confusion matrix to retraining-service/results/snn_confusion_matrix.png
- Updates /models/model_version.json: increment version, set snn field to new path
```

**Potential Issues:**
1. Dead neurons early in training (all-zero outputs) → Add batch normalization before each LIF layer
2. `--device cuda` argument needed for GPU → Add `argparse` with `--device` flag

**Testing Gate 4:** SNN achieves ≥ 90% validation accuracy. `model_version.json` updated with new snn path.

---

## PHASE 5 — LNN Engine
**Duration:** Week 3 | **Owner:** ML/AI Lead

**Antigravity Prompt:**
```
Write two files:

FILE 1: inference-service/core/lnn/reservoir.py
Class LiquidReservoir(torch.nn.Module):
- __init__(input_size=80, reservoir_size=500, spectral_radius=0.9, 
            leak_rate=0.3, sparsity=0.1)
- Sparse random W_res (reservoir_size × reservoir_size), scaled to spectral_radius
  (max eigenvalue magnitude = spectral_radius)
- Dense W_input (reservoir_size × input_size)
- Register both as buffers (NOT parameters — reservoir weights are NEVER trained)
- forward(x [seq_len, batch, 80], initial_state=None):
  state_t = (1-leak)*state_{t-1} + leak*tanh(W_res @ state_{t-1} + W_input @ x_t)
  Returns (all_states [seq_len, batch, 500], final_state [batch, 500])
- compute_spectral_radius() -> float (for verification)

FILE 2: inference-service/core/lnn/classifier.py + retraining-service/train_lnn.py
LNNClassifier: linear readout on last timestep of reservoir states → 7 classes
train_lnn.py: 
- Loads unified_train.csv, creates sliding windows of length 20
- Trains ONLY readout layer (reservoir.parameters() all require_grad=False)
- Saves best to /models/lnn_best.pt
- Updates model_version.json lnn field
```

**Potential Issues:**
1. Spectral radius scaling: must verify eigenvalues AFTER initialization — Antigravity often forgets
2. `requires_grad=False` check: add assertion `assert not any(p.requires_grad for p in reservoir.parameters())`

**Testing Gate 5:** `reservoir.compute_spectral_radius()` returns value between 0.85–0.95. LNN achieves ≥ 92% accuracy.

---

## PHASE 6 — XGBoost Model (NEW from architecture reference)
**Duration:** Week 3 | **Owner:** ML/AI Lead

> **Source:** `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf` — Detection Engine: *"SNN + LNN + XGBoost + Tree Logic"*

**Antigravity Prompt:**
```
Write two files for the XGBoost component of NeuroShield's detection ensemble:

FILE 1: inference-service/core/xgboost/model.py
Class XGBoostClassifier:
- __init__(model_path: str = None)
  Loads XGBoost model from model_path if provided, else initializes new
- predict_proba(features: np.ndarray) -> np.ndarray:
  Input: [batch, 80] normalized feature vectors
  Output: [batch, 7] class probabilities
- get_top_class(features) -> tuple[str, float]: (class_name, confidence)
- feature_importance() -> dict[str, float]: feature name → importance score
- save(path: str) and load(path: str)
- CLASS_NAMES = ['BENIGN','DDOS','BRUTE_FORCE','RECONNAISSANCE','WEB_ATTACK','BOT','OTHER']

FILE 2: inference-service/core/xgboost/tree_logic.py
Class TreeLogicOverride:
- Hard rules that OVERRIDE XGBoost predictions regardless of model confidence:
  Rule 1: if packet_rate > 10000 AND syn_ratio > 0.95 → force class='DDOS', confidence=0.99
  Rule 2: if unique_dst_ports > 1000 in 60s → force class='RECONNAISSANCE', confidence=0.95
  Rule 3: if login_attempts > 50 in 60s AND all_different_passwords → force 'BRUTE_FORCE'
- apply(features: dict, xgb_prediction: str, xgb_confidence: float) -> tuple[str, float]
  Returns (possibly overridden class, confidence)

FILE 3: retraining-service/train_xgboost.py
- Loads unified_train.csv
- XGBClassifier params: n_estimators=500, max_depth=6, learning_rate=0.1,
  subsample=0.8, colsample_bytree=0.8, use_label_encoder=False, eval_metric='mlogloss'
- 5-fold cross-validation, reports mean F1 per fold
- Trains on full training set, evaluates on test set
- Saves model to /models/xgboost_best.json
- Prints feature importance top 10
- Updates model_version.json xgb field
```

**Expected Output:** Three files: XGBoost wrapper, tree logic overrides, training script.

**Potential Issues:**
1. XGBoost label encoding: labels must be integers 0–6 → Add `LabelEncoder` to training script
2. Tree Logic rules need raw packet features (packet_rate, syn_ratio) but XGBoost receives normalized flow features → Pass BOTH normalized features (for XGBoost) and raw metrics dict (for TreeLogic) to the override
3. XGBoost model file format: use `.json` not `.pkl` for portability across XGBoost versions

**Testing Gate 6:** XGBoost achieves ≥ 99% accuracy on CIC-IDS2017 validation set. `model_version.json` has all three fields (snn, lnn, xgb) populated.

---

## PHASE 7 — Behavioral Profiler & Decision Engine
**Duration:** Week 4 | **Owner:** ML/AI Lead + Backend Lead

### Subphase 7.1 — Behavioral Profiler (Antigravity)

**Antigravity Prompt:**
```
Write inference-service/core/behavioral/signals.py and profiler.py:

signals.py — extracts 20-dimensional session vector from browser events:
Input: List[dict] where each dict has: {type, timestamp, key, x, y, page, element}
Event types: 'keydown', 'keyup', 'mousemove', 'click', 'scroll', 'pagevisit'
Functions:
- extract_typing_rhythm(events) -> np.ndarray: inter-keystroke intervals (ms)
- extract_dwell_times(events) -> np.ndarray: keydown to keyup durations per key
- extract_mouse_velocity(events) -> np.ndarray: pixel/ms between consecutive mousemoves
- extract_mouse_curvature(events) -> np.ndarray: direction change angles
- extract_session_vector(events) -> np.ndarray shape [20]:
  [mean_iki, std_iki, mean_dwell, std_dwell, mean_vel, std_vel, 
   mean_curve, std_curve, click_rate, scroll_depth, session_duration,
   page_count, error_rate, mean_pause_between_words, 
   and 6 more: percentiles p25/p75 of iki, dwell, velocity]

profiler.py — UserProfile + BehavioralProfiler:
- UserProfile dataclass: user_id, profile_vector [20], profile_std [20],
  session_count, last_updated, alpha=0.1
- BehavioralProfiler:
  - update_profile(user_id, session_vector): EMA update with alpha=0.1
  - compute_delta(user_id, session_vector) -> float: cosine distance; default 0.5 for new users
  - classify_delta(delta) -> Literal['HACKER','FORGETFUL_USER','LEGITIMATE']
    HACKER if > 0.70, FORGETFUL_USER if 0.30-0.70, LEGITIMATE if <= 0.30
  - save_profile(user_id) / load_profile(user_id): persists to PostgreSQL
```

### Subphase 7.2 — Ensemble Fusion Decision Engine (Antigravity)

**Antigravity Prompt:**
```
Write inference-service/core/engine.py — the main decision fusion engine.

ThreatVerdict dataclass fields:
session_id, user_id, source_ip, snn_score, lnn_class, xgb_class,
behavioral_delta, confidence, verdict, timestamp, model_version, features_dict

DecisionEngine class:
- On __init__: loads SNNAnomalyDetector, LNNClassifier, XGBoostClassifier, 
  TreeLogicOverride, BehavioralProfiler from model paths
- analyze_session(session_data: dict) -> ThreatVerdict:
  a. Extract 80 features from session_data['flow_features'] (already extracted by Feature Engine)
  b. snn_score = snn_detector.anomaly_score(spike_train)
  c. lnn_class, lnn_conf = lnn_classifier.predict_proba(session_sequence)
  d. xgb_class, xgb_conf = xgb_model.predict_proba(features) → apply TreeLogicOverride
  e. behav_delta = behavioral_profiler.compute_delta(user_id, session_vector)
  f. confidence = 0.35*snn_score + 0.30*lnn_conf + 0.25*xgb_conf + 0.10*behav_delta
  g. Verdict logic:
     confidence > 0.80 → HACKER
     0.50 < conf <= 0.80 → if behav_delta > 0.50: HACKER else FORGETFUL_USER  
     0.30 < conf <= 0.50 → FORGETFUL_USER
     conf <= 0.30 → LEGITIMATE
     any Exception → INCONCLUSIVE
  h. If HACKER: publish session_id to 'alerts' Kafka topic
  i. Update user behavioral profile
  j. Publish ThreatVerdict to 'verdicts' Kafka topic
  k. Return ThreatVerdict
- check_model_version(): polls model_version.json every 60s; hot-swaps if version changed
  If new model validation_f1 < previous validation_f1 → rollback (log WARNING)
- Thread-safe: use threading.RLock() around model inference calls
```

**Potential Issues:**
1. Model hot-swap during active inference → Use `with self._lock:` around both the hot-swap AND inference calls
2. Kafka producer inside DecisionEngine creates tight coupling → Pass a callback for Kafka publishing instead

**Testing Gate 7:** `engine.analyze_session(sample_normal_session)` returns LEGITIMATE with confidence < 0.3. `engine.analyze_session(sample_ddos_session)` returns HACKER with confidence > 0.8.

---

## PHASE 8 — Feedback Engine & Retraining Service (NEW)
**Duration:** Week 5–6 | **Owner:** Backend Lead + ML/AI Lead

> **Source:** `docs/DOCKER_ARCHITECTURE_REFERENCE.pdf`:
> *"Continuous learning support: retraining service runs separately. Model update doesn't break system."*

### Subphase 8.1 — Feedback Engine (Antigravity)

**Antigravity Prompt:**
```
Write feedback-service/main.py — the ground-truth labeling engine for NeuroShield.

This service closes the continuous learning loop.

It:
1. Consumes completed sandbox sessions from PostgreSQL table sandbox_actions
   (polls every 30 seconds for sessions where sandbox_ended_at IS NOT NULL AND feedback_sent = FALSE)
2. For each completed sandbox session:
   a. Loads all actions logged: pages visited, requests made, payloads sent
   b. Assigns ground-truth attack-type label using rule-based labeling:
      - If any request contained SQL injection pattern → WEB_ATTACK
      - If request rate > 100/min → DDOS
      - If login attempts > 10 with different passwords → BRUTE_FORCE
      - If more than 5 unique port scans → RECONNAISSANCE
      - If honeypot endpoint was accessed → HACKER (generic)
      - Default: HACKER (they were sandboxed, so something was suspicious)
   c. Extracts the 80-feature vector from the session's first network flow
   d. Creates a labeled sample: {features: [80 floats], label: 'DDOS', session_id, timestamp}
3. Publishes labeled sample to Kafka topic 'feedback' as JSON
4. Updates sandbox_actions row: feedback_sent = TRUE, assigned_label = label
5. Logs: "Labeled session [id] as [label] → published to feedback topic"

Use kafka-python KafkaProducer. Use psycopg2 for PostgreSQL. 
Configuration from env: KAFKA_BOOTSTRAP, DATABASE_URL, POLL_INTERVAL_SECONDS=30
```

**Potential Issues:**
1. Rule-based labeling is imperfect — some sessions may be mislabeled → Add a `confidence` field to the feedback message; low-confidence samples get down-weighted in retraining
2. A single session may match multiple rules → Use priority order: SQL > DDoS > BruteForce > Recon > Generic

### Subphase 8.2 — Retraining Orchestrator (Antigravity)

**Antigravity Prompt:**
```
Write retraining-service/retrain.py — the continuous retraining orchestrator.

This service consumes labeled feedback samples and periodically retrains all three models.

1. Consumes from Kafka topic 'feedback' (group_id='retraining-service')
2. Accumulates samples in memory: {features: np.ndarray, label: str}
3. When accumulated samples >= RETRAIN_BATCH_SIZE (default: 500 from env):
   a. Save batch to /data/feedback_batch_{timestamp}.csv
   b. Load historical training data from datasets/processed/unified_train.csv
   c. Combine: historical_data + new_feedback_samples (weight new samples 3x via SMOTE oversampling)
   d. Run retraining functions (import from train_snn, train_lnn, train_xgboost):
      - new_snn_f1 = retrain_snn(combined_data, save_path='/models/snn_candidate.pt')
      - new_lnn_f1 = retrain_lnn(combined_data, save_path='/models/lnn_candidate.pt')
      - new_xgb_f1 = retrain_xgboost(combined_data, save_path='/models/xgb_candidate.json')
   e. Load current model_version.json to get previous F1 scores
   f. Decision: only deploy if ALL three new F1 scores >= previous scores - 0.02 (allow 2% slack)
   g. If deploying: 
      - Rename candidates to snn_best.pt, lnn_best.pt, xgboost_best.json
      - Increment version in model_version.json, update validation_f1 fields
      - Log: "Model v[N] deployed. SNN F1: [x], LNN F1: [y], XGB F1: [z]"
   h. If not deploying:
      - Keep old models, delete candidates
      - Log WARNING: "Retraining skipped: new model underperformed on [which model]"
   i. Clear in-memory batch
4. Runs as infinite loop: consume → accumulate → trigger when threshold reached

Use kafka-python KafkaConsumer. Add signal handling for graceful shutdown (SIGTERM).
```

**Potential Issues:**
1. Retraining takes 30–60 minutes for SNN on large data → In demo mode, use `RETRAIN_BATCH_SIZE=50` and small dataset subset for fast feedback loop demonstration
2. Concurrent retraining + inference on same volume → Use a file lock (`fcntl.flock`) when writing to /models/
3. Memory accumulation → Flush batch to CSV after each Kafka commit, reload from CSV for retraining

**Testing Gate 8:** Manually publish 50 fake labeled samples to `feedback` topic (with `RETRAIN_BATCH_SIZE=50`). Verify: retraining triggers, `model_version.json` version increments, inference service logs "Hot-swapping to model v2".

---

## PHASE 9 — FastAPI Backend
**Duration:** Week 5–6 | **Owner:** Backend Lead

**Antigravity Prompt:**
```
Create FastAPI application in inference-service/api/main.py:

ROUTES:
POST /api/analyze → receives {session_id, user_id, source_ip, flow_features: [80 floats], 
  behavioral_events: [{type,timestamp,key,x,y,page}]}
  → runs DecisionEngine.analyze_session() → returns ThreatVerdict JSON

GET /api/verdicts/{user_id} → last 50 verdicts for user
GET /api/alerts → last 100 non-LEGITIMATE verdicts
GET /api/stats → {total_sessions_today, hacker_count, fpr, uptime_seconds, model_version}
POST /api/behavioral → {user_id, events: List[dict]} → updates behavioral profile
GET /api/sandbox/{session_id}/replay → sandbox action log for session
GET /api/model/version → returns current model_version.json contents
POST /api/bank/login → validates against 3 hardcoded test accounts (see below)
POST /api/bank/transfer → validates transfer, checks honeypot field
GET /health → {"status": "ok", "timestamp": ..., "kafka_connected": bool}

WebSocket /ws/alerts → streams ThreatVerdict events to dashboard in real-time
  Format: {type: "verdict", data: ThreatVerdict}
  Reconnect: client handles, server just closes on disconnect

HARDCODED BANK ACCOUNTS:
test@novatrust.com / password123 → user_id: "alice"
normal2@novatrust.com / secure456 → user_id: "bob"
admin@novatrust.com / Admin@2024! → user_id: "carol"

MIDDLEWARE: CORS (all origins in dev), X-API-Key auth (skip for /health, /docs)
DATABASE: asyncpg connection pool to DATABASE_URL env var
Use Pydantic for all request/response models. Async throughout.
```

**Potential Issues:**
1. asyncpg vs psycopg2 mixing (API uses async, ML engine uses sync) → Keep them separate; use `asyncio.run_in_executor` to call sync ML code from async routes
2. WebSocket broadcast to multiple clients → Use a global `Set[WebSocket]` and wrap each send in try/except for disconnected clients

**Testing Gate 9:** `curl http://localhost:8000/health` returns `{"status": "ok", "kafka_connected": true}`. WebSocket client connects and receives events when a verdict is produced.

---

## PHASE 10 — Sandbox Service
**Duration:** Week 6 | **Owner:** Backend Lead

**Antigravity Prompt:**
```
Write sandbox-service/main.py — Docker-isolated attacker decoy application.

This service is the security-critical sandbox described in DOCKER_ARCHITECTURE_REFERENCE.pdf.
It MUST run as non-root (handled in Dockerfile) and have no network access to production services.

The sandbox is a FastAPI application that MIRRORS the bank portal behavior:
- POST /login → always returns success with fake token (attacker thinks they're logged in)
- GET /dashboard → returns fake account data with different balance ($0.00 — "frozen")
- POST /transfer → accepts any transfer, logs it, returns "Transfer pending review"
- GET /api/* → returns plausible but fake data for all API endpoints
- ALL OTHER routes → returns 200 with generic response (never 404, never expose real structure)

All requests are logged to PostgreSQL table sandbox_actions:
{action_id, session_id, sandbox_token, path, method, headers_json, body, response_sent, timestamp}

SandboxManager class:
- create_session(original_session_id, user_id, source_ip) -> sandbox_token: str
  Creates new sandbox session, logs to DB
- log_action(sandbox_token, request_data, response_data): saves to DB
- terminate_session(sandbox_token): marks session ended_at = now(), triggers feedback via Kafka
  Posts to 'feedback-trigger' Kafka topic: {session_id, sandbox_token, ended_at}
- Session auto-expires after SANDBOX_TIMEOUT_SEC (env var, default 300s)

The FastAPI app:
- Middleware: extracts sandbox_token from Authorization header or cookie
- All routes → if no valid sandbox_token → return 401 (this should never happen in normal flow)
- Background task: every 60s, terminate expired sessions

Configuration: DATABASE_URL, KAFKA_BOOTSTRAP, SANDBOX_TIMEOUT_SEC
```

**Potential Issues:**
1. Sandbox must NEVER reveal it's a sandbox → All responses must look authentic; never return error messages that real app wouldn't show
2. Session token from production must map to sandbox session → The inference service redirects by setting `X-Sandbox-Token` header; sandbox reads this

**Testing Gate 10:** Send a POST to sandbox `/login` → get fake success response. Check PostgreSQL: `SELECT * FROM sandbox_actions` shows the logged request. After 5 minutes, session auto-expires and `feedback-trigger` message appears in Kafka.

---

## PHASE 11 — Frontend (Dashboard + Bank Portal)
**Duration:** Week 7–8 | **Owner:** Frontend Lead

### Analyst Dashboard (Antigravity)

**Antigravity Prompt:**
```
Create React + TypeScript analyst dashboard in dashboard/src/.

THEME: Dark cyberpunk. Background: #0a0e1a navy. Accents: #00d4ff electric blue.
Threat: #ff3b5c red. Safe: #00ff88 green. Warn: #ffb800 amber.
Fonts: 'Space Mono' (Google Fonts) for code/numbers, 'Rajdhani' for labels.

COMPONENTS:
1. StatsBar: fetches GET /api/stats every 30s.
   Shows 4 metric cards: Total Sessions | Hackers Blocked | FPR | Model Version
   
2. AlertFeed: native WebSocket ws://[API_URL]/ws/alerts.
   Last 50 alerts in scrolling list. HACKER = red flash animation. Auto-reconnect (3s delay).
   Click alert → UserProfileModal.
   
3. VerdictTimeline: Recharts AreaChart, verdicts grouped by hour (last 24h).
   3 area series: HACKER (red), FORGETFUL_USER (amber), LEGITIMATE (green).
   
4. ModelStatusCard: fetches GET /api/model/version every 60s.
   Shows current model versions (SNN, LNN, XGBoost), validation F1 scores, last retrained timestamp.
   (This is new — reflects the continuous learning loop from DOCKER_ARCHITECTURE_REFERENCE.pdf)
   
5. ThreatMap: Leaflet.js world map. Pulsing red dots = HACKER verdicts (last 24h). 
   Use ip-api.com for geocoding. Cache results in a Map() ref.

6. UserProfileModal: radar chart (20 behavioral dimensions), last 10 verdict history.

Layout: top nav (logo + StatsBar + ModelStatusCard), main (70% timeline, 30% AlertFeed),
        floating ThreatMap in bottom-left.

Use axios (base URL from import.meta.env.VITE_API_URL). 
Do NOT use socket.io-client — use native WebSocket.
```

**Potential Issues:**
1. ModelStatusCard is new and may not have a backend route yet → Build the component with a loading state, implement the route in Phase 9 catch-up
2. Recharts may choke on 1000+ data points → Limit to last 96 hours, 1 point per 15 minutes

### Simulation Bank Portal (Antigravity)

**Antigravity Prompt:**
```
Create React + TypeScript NovaTrust Bank simulation portal in simulation_portal/src/.

DESIGN: Professional 2024 banking aesthetic. White + navy blue (#002147). 
Font: Playfair Display (headings), Inter (body). Must look like a real bank.

PAGES:
/ → Landing: NovaTrust logo, hero section, login CTA, fake footer with FDIC badge.
   Hidden: <meta name="session-token" content="[CANARY_TOKEN]">
   Hidden link in footer: href="/internal/staff-portal" style="display:none"

/login → Email + password form.
   Honeypot: <input name="confirm_email" style="opacity:0;position:absolute;top:-9999px">
   On submit:
   1. If confirm_email is filled → POST /api/bank/honeypot-hit (bot detected)
   2. POST /api/behavioral {user_id, session_id, events}
   3. POST /api/bank/login {email, password}
   4. If verdict from /api/verdicts/{user_id} is 'HACKER' → navigate to /security-alert
   5. Else → navigate to /dashboard

/dashboard → Fake account: balance, 10 fake transactions.
   Hidden HTML comment: <!-- ref: [CANARY_TOKEN] -->
   Hidden localStorage: localStorage.setItem('debug_session', '[CANARY_TOKEN]')

/transfer → Transfer form with hidden honeypot field "confirm_routing_number"
   SQL injection detection: if memo contains " OR " or "--" → POST /api/bank/web-attack-detected

/security-alert → "Unusual activity detected. Session suspended." (attacker in sandbox)

/verdict-display → Split screen: left iframe /login, right live NeuroShield analysis panel
   Right panel polls GET /api/verdicts/current every 2s
   Shows: SNN Score, LNN Class, XGBoost Class, Behavioral Δ, Confidence, Verdict
   Color transitions: green→amber→red based on confidence

BEHAVIORAL TRACKER HOOK (useBehavioralTracker):
- useRef for event buffer (never useState — avoid re-renders)
- Global listeners: keydown, keyup, mousemove (throttled 100ms), click, scroll
- For password fields: set key='[REDACTED]' (never capture actual passwords)
- Flush to /api/behavioral every 10 seconds
- Returns {sessionId, eventCount, startTracking, stopTracking}
```

**Potential Issues:**
1. Split-screen iframe CORS issue → Use same-origin or PostMessage API between panels
2. `useBehavioralTracker` must not cause ANY re-renders → All state in refs; verify with React DevTools profiler

**Testing Gate 11:** Load bank portal → login as test@novatrust.com → dashboard loads → `/verdict-display` shows live analysis. Run `redteam/attack_brute_force.py` → `/security-alert` shown within 10 seconds.

---

## PHASE 12 — Kubernetes Manifests
**Duration:** Week 9 | **Owner:** DevOps/Research Lead

**Antigravity Prompt:**
```
Create Kubernetes manifests in k8s/ for NeuroShield production deployment.

As described in DOCKER_ARCHITECTURE_REFERENCE.pdf:
"Docker = local/small scale. Kubernetes = real-world scale."

Create these YAML files:

k8s/namespace.yaml: namespace 'neuroshield'

k8s/inference-deployment.yaml: 
  Deployment: 3 replicas, image neuroshield/inference:latest, port 8000
  PVC volume mount at /models

k8s/inference-hpa.yaml:
  HPA: min 2, max 10 replicas, CPU target 70%
  (From DOCKER_ARCHITECTURE_REFERENCE.pdf example)

k8s/sandbox-networkpolicy.yaml:
  NetworkPolicy: sandbox pods can ONLY send egress to pods labeled app=feedback
  All other egress blocked. All ingress from inference only.

k8s/inference-service.yaml:
  Service: ClusterIP, port 8000 → pod port 8000

k8s/models-pvc.yaml:
  PersistentVolumeClaim: 10Gi ReadWriteMany (for shared model volume across inference pods)

k8s/kafka-deployment.yaml:
  Deployment: Confluent cp-kafka, 1 replica (use Strimzi operator comment if available)
  Note: for production, recommend Strimzi Kafka Operator instead

k8s/kustomization.yaml:
  Lists all resources, sets namespace: neuroshield for all

Add comments in each file explaining the architectural decision (reference the PDF where applicable).
```

**Testing Gate 12:** `kubectl apply -k k8s/` → all resources created. `kubectl get pods -n neuroshield` shows inference pods running. HPA active: `kubectl get hpa -n neuroshield`.

---

## PHASE 13 — Integration Testing & Red Team
**Duration:** Week 10 | **Owner:** All Members

### Integration Test Suite (Antigravity)

**Antigravity Prompt:**
```
Write tests/test_integration.py using pytest:

Fixtures: engine() (mocked models), profiler() (in-memory), 
sample_features() (80-float array of BENIGN traffic)

TEST FUNCTIONS:
test_legitimate_user(): 10 normal sessions → 11th → assert LEGITIMATE, conf < 0.35
test_forgetful_user(): 5 normal sessions + 1 slow-typing session → assert FORGETFUL_USER
test_hacker(): 5 normal sessions + 1 random-typing session → assert HACKER, conf > 0.7
test_snn_ddos(): 1000 SYN-flood-like feature vectors → assert snn_score > 0.8
test_xgboost_web_attack(): feature vector with SQL injection pattern → assert xgb_class='WEB_ATTACK'
test_tree_logic_override(): packet_rate=15000, syn_ratio=0.97 → assert class='DDOS' (overridden)
test_honeypot_hit(): request to '/api/admin' → assert CRITICAL alert created in DB
test_sandbox_isolation(): sandbox session → assert no route to production DB
test_feedback_labeling(): brute-force sandbox session → assert feedback label='BRUTE_FORCE'
test_model_hot_swap(): write new model_version.json → assert engine reloads within 70s
test_report_generation(): mock 10 verdicts → assert CSV exists with all columns including xgb_class
```

### Red Team Scripts (Manual — External)

Prepare these for judge demo:
```bash
python redteam/attack_brute_force.py --target http://localhost:3001 --attempts 100
sudo python redteam/attack_ddos.py --target localhost --packets 5000
python redteam/attack_normal_user.py --user test@novatrust.com
python redteam/attack_honeypot.py --target http://localhost:3001
python redteam/reset_demo.py   # Run between judge scenarios
```

**Testing Gate 13:** All 11 pytest tests pass. All 4 red team scripts produce correct verdicts within 10 seconds of running.

---

## PHASE 14 — Reporting & Demo Preparation
**Duration:** Week 11–12 | **Owner:** All

### Morning Report Generator (Antigravity)

**Antigravity Prompt:**
```
Write reports/generator.py:
1. Query PostgreSQL for last 24h verdicts (including snn_score, lnn_class, xgb_class, 
   feedback_labeled, model_version fields)
2. Generate CSV: timestamp, session_id, user_id, source_ip, attack_category, 
   confidence_score, behavioral_delta, snn_score, lnn_class, xgb_class, verdict,
   sandbox_triggered, sandbox_duration_sec, feedback_labeled, model_version,
   packets_captured, features_extracted, analyst_notes
3. Generate HTML email with:
   - Summary stats (total sessions, hacker_count, fpr, current model version)
   - Top 5 threat IPs
   - Bar chart of verdicts by type (embedded base64 PNG via matplotlib)
   - Table of CRITICAL/BREACH alerts
   - Note: "X new samples labeled and queued for retraining" (from feedback count)
4. Send via SMTP from env vars
5. Save CSV to reports/daily/report_{YYYY-MM-DD}.csv
```

---

## External Tasks Summary

| Task | Reason External | Who |
|---|---|---|
| Dataset registration + download | UNB portal requires human account | DevOps Lead |
| Intel Loihi DevCloud application | Intel approval process | ML Lead |
| SMTP credentials | Email service account needed | Backend Lead |
| Docker Hub account for K8s images | Registry account | DevOps Lead |
| Cloud VM for training | GPU access for SNN/LNN | DevOps Lead |
| Red team scripts (root required) | Network socket privileges | All |
| Domain + SSL for public demo | DNS management | DevOps Lead |

## What This Document Still Needs

| Gap | Priority |
|---|---|
| **Antigravity prompts for monitoring/Prometheus config** | 🔴 High |
| **Database schema SQL** — complete DDL for all tables including sandbox_actions, feedback | 🔴 High |
| **Model version JSON schema** — exact format and hot-swap trigger logic | 🔴 High |
| **XGBoost feature importance output** — which CIC features matter most (inform TreeLogicOverride tuning) | 🟡 Medium |
| **Load testing plan** — how to verify `docker-compose up --scale ingestion=3` actually helps | 🟡 Medium |
| **Feedback Engine labeling accuracy** — how to validate the rule-based labels are correct | 🟡 Medium |
| **K8s deployment to cloud** — step-by-step GKE or EKS setup instructions | 🟢 Low |
