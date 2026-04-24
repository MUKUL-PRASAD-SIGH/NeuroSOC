# ANTIGRAVITY PROMPTS — Quick Reference Card

> Copy-paste ready prompts for every major component. Use in order. Each prompt is self-contained.

---

## HOW TO USE THIS FILE

1. Open Antigravity
2. Start a new session for each major component
3. Copy the prompt block exactly
4. Paste into Antigravity
5. Copy generated code to the correct file path
6. Run the verification command shown
7. Commit to git

---

## PROMPT 01 — Docker Compose

**File to create:** `docker-compose.yml`

> Architecture follows the microservices plan: Ingestion → Kafka → Feature → Inference → Sandbox → Feedback → Retraining, with Dashboard and Monitoring running in parallel.

```
Create a Docker Compose v3.8 file for a cybersecurity platform called NeuroShield.
Use network neuroshield-net (bridge driver) for all services.

INFRASTRUCTURE:
1. postgres: image postgres:15-alpine, POSTGRES_DB=neuroshield, POSTGRES_USER=ns_user,
   POSTGRES_PASSWORD=ns_pass, port 5432, volume postgres_data:/var/lib/postgresql/data,
   healthcheck: pg_isready -U ns_user -d neuroshield every 10s

2. redis: image redis:7-alpine, port 6379,
   healthcheck: redis-cli ping every 10s

3. zookeeper: image confluentinc/cp-zookeeper:7.5.0, port 2181,
   ZOOKEEPER_CLIENT_PORT=2181

4. kafka: image confluentinc/cp-kafka:7.5.0, port 9092, depends_on zookeeper,
   KAFKA_BROKER_ID=1, KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181,
   KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092,
   KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1

PIPELINE SERVICES (data flows left to right through Kafka topics):
5. feature-service: build ./feature_service, depends_on kafka (healthy),
   environment: KAFKA_BOOTSTRAP_SERVERS=kafka:9092,
   KAFKA_INPUT_TOPIC=raw-traffic, KAFKA_OUTPUT_TOPIC=extracted-features
   Command: python main.py
   (Consumes raw packets from Kafka, emits CIC-style feature vectors)

6. inference-service: build ./inference_service, depends_on kafka (healthy) + postgres (healthy),
   environment from .env file, 
   volumes: ./weights:/weights (read-only: true)
   KAFKA_INPUT_TOPIC=extracted-features, KAFKA_OUTPUT_TOPIC=verdicts
   Command: python main.py
   (Runs SNN + LNN + XGBoost ensemble; emits ThreatVerdict to Kafka)

7. feedback-service: build ./feedback_service, depends_on kafka (healthy) + postgres (healthy),
   KAFKA_INPUT_TOPIC=verdicts, KAFKA_OUTPUT_TOPIC=feedback-labels
   Command: python main.py
   (Labels sandbox sessions, writes labeled data to postgres for retraining)

8. retraining-service: build ./retraining_service, depends_on postgres (healthy),
   volumes: ./weights:/weights, ./datasets/processed:/data (read-only: true)
   RETRAIN_TRIGGER=scheduled, RETRAIN_INTERVAL_HOURS=24
   Command: python retrain.py
   (Batch retraining on new labeled data; overwrites weights/*.pt and weights/*.pkl)

GATEWAY & DECEPTION:
9. api: build ./api, port 8000, depends_on postgres+redis+kafka+inference-service (healthy),
   environment from .env file, volumes ./:/app
   (FastAPI orchestrator: exposes REST + WebSocket; NOT the inference logic itself)

10. sandbox-service: build ./sandbox_service, depends_on api,
    network_mode: none (NO external network access — security isolation)
    volumes: ./sandbox_data:/sandbox_data
    (Isolated fake environment; attacker containers cannot reach real services)

FRONTENDS:
11. dashboard: build ./dashboard, port 3000, depends_on api

12. simulation_portal: build ./simulation_portal, port 3001, depends_on api

MONITORING:
13. prometheus: image prom/prometheus:latest, port 9090,
    volume ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

14. grafana: image grafana/grafana:latest, port 3002,
    environment GF_SECURITY_ADMIN_PASSWORD=neuroshield_admin,
    volume grafana_data:/var/lib/grafana

Named volumes: postgres_data, grafana_data
Output ONLY the docker-compose.yml content. No explanation.
```

**Verify with:** `docker-compose config` (no errors = correct YAML)

---

## PROMPT 02 — Preprocessing Pipeline

**File to create:** `datasets/preprocess.py`

```
Write a Python script datasets/preprocess.py. It must run standalone with: python datasets/preprocess.py

The script:
1. Finds all CSV files recursively in datasets/raw/ using glob
2. For each CSV file:
   a. Reads with pd.read_csv, handling common encoding issues (try utf-8, then latin-1)
   b. Strips whitespace from all column names
   c. Converts column names to snake_case (lowercase, spaces to underscores)
   d. Drops columns where more than 50% of values are null or inf
   e. Replaces remaining inf values with NaN, then fills NaN with column median
3. Identifies the label column (column named 'label' or 'Label' or ' Label')
4. Maps labels to unified taxonomy:
   - Contains 'DDoS' or 'DoS' (case-insensitive) → 'DDOS'
   - Contains 'Brute' → 'BRUTE_FORCE'  
   - Contains 'Scan' or 'Probe' or 'Recon' → 'RECONNAISSANCE'
   - Contains 'XSS' or 'SQL' or 'Web' or 'Injection' → 'WEB_ATTACK'
   - Contains 'Bot' → 'BOT'
   - 'BENIGN' or 'Normal' or 'Benign' → 'BENIGN'
   - All others → 'OTHER'
5. Combines all DataFrames into one, keeping only numeric columns + label
6. Prints class distribution
7. Applies MinMaxScaler to all numeric columns (save scaler to datasets/scaler.pkl using joblib)
8. Applies SMOTE with sampling_strategy='minority' to balance classes 
   (if any class has < 1000 samples, oversample it to 1000)
9. Performs 80/20 stratified train/test split
10. Saves: datasets/processed/unified_train.csv and datasets/processed/unified_test.csv
11. Prints final class distribution for both splits
12. Saves column list to datasets/feature_columns.txt (one column per line)

Requirements: pandas, scikit-learn, imbalanced-learn, joblib, numpy
Handle: FileNotFoundError if datasets/raw/ is empty (print helpful message and exit)
Add: if __name__ == '__main__': guard
```

**Verify with:**
```bash
python datasets/preprocess.py
wc -l datasets/processed/unified_train.csv  # Should be > 1000
head -1 datasets/processed/unified_train.csv  # Should show column names
```

---

## PROMPT 03 — SNN Spike Encoder

**File to create:** `core/snn/encoder.py`

```
Write a Python module core/snn/encoder.py using PyTorch (version 2.x) and the Norse library.

Implement class SpikeEncoder:
- __init__(self, n_features: int = 80, n_neurons_per_feature: int = 5, T: int = 100)
  n_features: number of input features
  n_neurons_per_feature: receptive field neurons per feature
  T: simulation timesteps
  
- _create_gaussian_receptive_fields(self):
  For each feature, create n_neurons_per_feature Gaussian receptive fields
  evenly spaced between 0 and 1 (the normalized feature range)
  Each neuron i has center mu_i and sigma = 1/(2*n_neurons_per_feature)
  
- encode(self, features: np.ndarray) -> torch.Tensor:
  Input: features of shape [batch_size, n_features] (already normalized 0-1)
  For each feature, compute Gaussian activation for each receptive field neuron
  Convert activation to spike probability (higher activation = higher spike probability)
  Use Bernoulli sampling over T timesteps to generate spikes
  Output: tensor of shape [T, batch_size, n_features * n_neurons_per_feature]
  
- encode_deterministic(self, features: np.ndarray) -> torch.Tensor:
  Same as encode but uses rate coding: neuron fires every ceil(1/activation) timesteps
  (deterministic, useful for evaluation)

- decode(self, spike_train: torch.Tensor) -> np.ndarray:
  Reverses encoding: computes mean firing rate per neuron group, 
  returns array of shape [batch_size, n_features]

Include: from norse.torch.functional import lif_feed_forward_step (use for any LIF neuron operations)
Include complete type hints, docstrings, and an if __name__ == '__main__': test block that:
  creates encoder with defaults, encodes a batch of 4 random feature vectors, prints output shape
```

**Verify with:**
```bash
python core/snn/encoder.py
# Expected output: "Encoded shape: torch.Size([100, 4, 400])"
```

---

## PROMPT 04 — SNN Anomaly Detector

**File to create:** `core/snn/network.py`

> This module runs inside `inference-service`. Its anomaly score feeds into the XGBoost ensemble alongside the LNN classifier output.

```
Write a Python module core/snn/network.py using PyTorch 2.x and Norse.

Implement class SNNAnomalyDetector(torch.nn.Module):
- __init__(self, input_size: int = 400, hidden_sizes: list = [256, 128], n_classes: int = 7)
  Uses norse.torch.LIFRecurrentCell for recurrent hidden layers
  Final layer: standard linear layer (no LIF, just linear readout)
  
- forward(self, spike_train: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
  Input: spike_train of shape [T, batch, input_size]
  Process through LIF layers sequentially for each timestep T
  Average the hidden state across last 10 timesteps for final representation
  Output: (logits of shape [batch, n_classes], anomaly_score of shape [batch])
  anomaly_score = 1.0 - softmax(logits)[:, 0]  (index 0 = BENIGN class)
  
- save(self, path: str): saves state_dict to path
- load(self, path: str): loads state_dict from path (classmethod)

Class variables: CLASS_NAMES = ['BENIGN', 'DDOS', 'BRUTE_FORCE', 'RECONNAISSANCE', 'WEB_ATTACK', 'BOT', 'OTHER']

Add if __name__ == '__main__': test:
  model = SNNAnomalyDetector()
  dummy = torch.zeros(100, 4, 400)
  logits, score = model(dummy)
  print(f"Logits: {logits.shape}, Score: {score.shape}")  # [4, 7], [4]
```

**Verify with:**
```bash
python core/snn/network.py
# Expected: "Logits: torch.Size([4, 7]), Score: torch.Size([4])"
```

---

## PROMPT 05 — LNN Reservoir

**File to create:** `core/lnn/reservoir.py`

> The LNN reservoir's final hidden state is concatenated with the SNN anomaly score and passed to the XGBoost classifier (PROMPT 05b) for the final verdict.

```
Write core/lnn/reservoir.py implementing a Liquid State Machine using PyTorch 2.x.

Class LiquidReservoir(torch.nn.Module):
- __init__(self, input_size: int = 80, reservoir_size: int = 500, 
           spectral_radius: float = 0.9, leak_rate: float = 0.3, sparsity: float = 0.1)
  
- _init_reservoir_weights(self):
  Create W_reservoir: sparse random matrix (size x size), sparsity = fraction of nonzero connections
  Create W_input: dense random matrix (size x input_size)  
  Scale W_reservoir so its largest eigenvalue magnitude = spectral_radius
  Register both as buffers (not parameters): self.register_buffer('W_res', W_reservoir)
  Register as buffers means they move with .to(device) but are NOT updated by optimizer
  
- forward(self, x: torch.Tensor, initial_state: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
  Input x: [seq_len, batch, input_size]
  initial_state: [batch, reservoir_size] (zeros if None)
  For each timestep t:
    state_t = (1 - leak_rate) * state_{t-1} + leak_rate * tanh(W_res @ state_{t-1} + W_input @ x_t)
  Returns: (all_states: [seq_len, batch, reservoir_size], final_state: [batch, reservoir_size])
  
- compute_spectral_radius(self) -> float: utility method for verification

if __name__ == '__main__':
  res = LiquidReservoir()
  print(f"Spectral radius: {res.compute_spectral_radius():.3f}")  # Should be ~0.9
  x = torch.randn(20, 4, 80)
  states, final = res(x)
  print(f"States shape: {states.shape}")  # [20, 4, 500]
```

---

## PROMPT 05b — XGBoost Ensemble Classifier

**File to create:** `core/inference/xgboost_classifier.py`

> This is the final decision layer of the inference pipeline. It takes a fused feature vector (SNN score + LNN reservoir state + behavioral delta) and outputs the ThreatVerdict.

```
Write a Python module core/inference/xgboost_classifier.py.

Class XGBoostThreatClassifier:
- __init__(self, model_path: str = 'weights/xgb_classifier.pkl')
  Loads an XGBoost XGBClassifier from model_path using joblib.
  If model_path does not exist, self.model = None (training mode).

- build_feature_vector(self,
      snn_score: float,
      lnn_reservoir_state: np.ndarray,
      behavioral_delta: float,
      lnn_class_probs: np.ndarray) -> np.ndarray:
  Concatenates all inputs into a single 1D feature vector:
  [snn_score (1), lnn_reservoir_state (500), behavioral_delta (1), lnn_class_probs (7)]
  Returns: np.ndarray of shape (509,)

- predict(self, feature_vector: np.ndarray) -> dict:
  Input: shape (509,) from build_feature_vector
  Returns: {
    'verdict': str,           # One of CLASS_NAMES
    'confidence': float,      # max class probability
    'class_probs': dict       # {class_name: prob} for all 7 classes
  }
  Raises RuntimeError if self.model is None.

- train(self,
        X_train: np.ndarray, y_train: np.ndarray,
        X_val: np.ndarray, y_val: np.ndarray,
        save_path: str = 'weights/xgb_classifier.pkl') -> dict:
  Trains XGBClassifier with:
    n_estimators=300, max_depth=6, learning_rate=0.05,
    use_label_encoder=False, eval_metric='mlogloss',
    early_stopping_rounds=20
  Evaluates on val set; prints classification_report.
  Saves to save_path using joblib.
  Returns: {'f1_macro': float, 'accuracy': float}

CLASS_NAMES = ['BENIGN', 'DDOS', 'BRUTE_FORCE', 'RECONNAISSANCE', 'WEB_ATTACK', 'BOT', 'OTHER']

if __name__ == '__main__':
  clf = XGBoostThreatClassifier(model_path='weights/xgb_classifier.pkl')
  dummy_vec = np.zeros(509)
  dummy_vec[0] = 0.85  # high SNN score
  dummy_vec[501] = 0.9  # high behavioral delta
  if clf.model:
    result = clf.predict(dummy_vec)
    print(f"Verdict: {result['verdict']}, Confidence: {result['confidence']:.2f}")
  else:
    print("No model loaded — run training first.")
```

**Verify with:**
```bash
python core/inference/xgboost_classifier.py
# Expected: "No model loaded — run training first." (before weights exist)
```

---

## PROMPT 05c — Feature Engine (CIC Extraction Service)

**File to create:** `feature_service/main.py` + `feature_service/extractor.py`

> Runs as `feature-service` container. Consumes raw packet dicts from Kafka topic `raw-traffic`, extracts CIC-style 80-feature vectors, publishes to `extracted-features`.

```
Write two Python files for the NeuroShield feature extraction microservice.

FILE: feature_service/extractor.py
Class CICFeatureExtractor:
- extract(self, packet_batch: list[dict]) -> np.ndarray:
  Input: list of packet dicts with keys:
    src_port, dst_port, protocol, packet_length, flags (SYN/ACK/RST/PSH/FIN as bools),
    inter_arrival_time_ms, fwd_packets, bwd_packets, flow_duration_ms
  
  Compute these CIC-style features per flow (group packet_batch by src_ip+dst_ip+dst_port):
  - Flow duration, total fwd/bwd packets, total fwd/bwd bytes
  - Fwd/bwd packet length mean, std, min, max
  - Inter-arrival time mean, std, min, max (both fwd and bwd)
  - Packet length mean, std, variance, skewness, kurtosis
  - SYN/ACK/RST/PSH/FIN flag counts
  - Bytes per second, packets per second
  - Fwd/bwd header length mean
  - Active/idle mean, std, min, max
  
  Pad/truncate to exactly 80 features.
  Normalize using MinMaxScaler loaded from datasets/scaler.pkl (load once in __init__).
  Returns: np.ndarray of shape (n_flows, 80)

FILE: feature_service/main.py
- Connects to Kafka consumer: group_id='feature-service', topic='raw-traffic',
  bootstrap_servers from env KAFKA_BOOTSTRAP_SERVERS
- Connects to Kafka producer: topic='extracted-features'
- Main loop: poll messages (batch up to 50 packets per flow window),
  call extractor.extract(), serialize output as JSON with keys:
    {session_id, user_id, source_ip, features: list[list[float]], timestamp}
  Publish to extracted-features topic.
- Log: "Feature service started. Listening on raw-traffic..."
- Handle KeyboardInterrupt cleanly (commit offsets, close connections).
```

**Verify with:**
```bash
docker-compose up feature-service  # Should log "Feature service started..."
# Send a test message to raw-traffic topic and confirm extracted-features has output
```

---

## PROMPT 06 — FastAPI Backend (Orchestrator Gateway)

**File to create:** `api/main.py` + `api/routes/analysis.py`

> The `api` container is a gateway only. It does NOT run inference — it reads verdicts written to PostgreSQL by `inference-service` and exposes them via REST + WebSocket. Do NOT import torch, norse, or xgboost here.

```
Create a FastAPI application for NeuroShield cybersecurity platform.
Role: Orchestrator gateway. Reads from DB. No ML imports.

FILE: api/main.py
- FastAPI app with title="NeuroShield API", version="1.0.0"
- CORS middleware: allow_origins=["http://localhost:3000", "http://localhost:3001"],
  allow_methods=["*"], allow_headers=["*"]
- API key middleware: reads X-API-Key header, validates against API_KEY env var
  Exception: skip auth for /health, /docs, /openapi.json
- Include router from api/routes/analysis.py with prefix="/api"
- Include router from api/routes/bank.py with prefix="/api/bank"
- WebSocket endpoint at /ws/alerts:
  Accepts connections, adds to a global Set of active connections
  On each new DB verdict (poll every 2s): broadcast to all connections
  Handles disconnect gracefully
- GET /health: returns {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
- On startup: initialize asyncpg connection pool, log "NeuroShield API gateway started"
- On shutdown: close database pool

FILE: api/routes/analysis.py
Pydantic models:
- BehavioralEventRequest: session_id (str), user_id (str), events (List[dict])
- VerdictResponse: session_id, user_id, source_ip, verdict, confidence, snn_score,
  lnn_class, xgb_confidence, behavioral_delta, timestamp

Routes (all async def, asyncpg queries, tagged "Security Analysis"):
- GET /verdicts/{user_id}: query DB for last 50 verdicts for user_id, return list
- GET /verdicts/current-session: query DB for the most recent verdict, return VerdictResponse
- GET /alerts: query DB for last 100 rows where verdict in ('HACKER','FORGETFUL_USER')
- GET /stats: return {total_sessions_today, hacker_count, fpr, uptime_seconds}
- POST /behavioral: receives BehavioralEventRequest,
  publishes events as JSON to Kafka topic 'raw-traffic' (behavioral events treated as
  lightweight packet proxies for demo purposes); returns {"queued": true}
  Use aiokafka AIOKafkaProducer (async).

NOTE: There is NO POST /analyze route here. The pipeline is:
  simulation_portal → POST /api/behavioral → Kafka raw-traffic → feature-service →
  extracted-features → inference-service → DB → this API reads and exposes verdicts.
```

---

## PROMPT 07 — Analyst Dashboard

**File to create:** `dashboard/src/App.tsx` + component files

```
Create a React + TypeScript analyst dashboard for NeuroShield.

GLOBAL SETUP:
- TailwindCSS config with custom colors: 
  navy: '#0a0e1a', electric: '#00d4ff', threat: '#ff3b5c', safe: '#00ff88', warn: '#ffb800'
- Use Google Fonts: 'Space Mono' for code/numbers, 'Rajdhani' for UI labels

COMPONENT 1: src/components/StatsBar.tsx
- Fetches GET /api/stats every 30 seconds
- Shows 4 metric cards in a row: Total Sessions | Hackers Blocked | False Positive Rate | Uptime
- Each card: large number in electric blue, label in gray below
- Animate number changes with a brief scale pulse

COMPONENT 2: src/components/AlertFeed.tsx  
- Connects to WebSocket ws://localhost:8000/ws/alerts using useEffect + useRef
- Stores last 50 alerts in useState
- Renders each alert as a card: timestamp | user_id | source_ip | verdict badge | confidence %
- Verdict badge colors: HACKER=threat red with flash animation, FORGETFUL_USER=warn yellow, LEGITIMATE=safe green
- Auto-reconnect on disconnect (retry after 3 seconds)
- Scrollable list with newest at top

COMPONENT 3: src/components/VerdictTimeline.tsx
- Fetches GET /api/alerts on mount and every 60 seconds
- Groups verdicts by hour for last 24 hours
- Renders Recharts AreaChart with 3 area series (HACKER/FORGETFUL/LEGITIMATE), each in respective color
- X-axis: hours (0-23), Y-axis: session count

COMPONENT 4: src/App.tsx
- Layout: full-height dark navy background
- Top: NeuroShield logo (text-based, using Space Mono, electric blue) + StatsBar
- Main area: left 70% = VerdictTimeline chart, right 30% = AlertFeed
- NeuroShield logo text: "NEURO" in electric blue + "SHIELD" in white, with a subtle shield SVG icon

Do NOT use socket.io-client. Use native WebSocket API.
Use axios for all HTTP requests with base URL from import.meta.env.VITE_API_URL.
Export each component as default export.
```

---

## PROMPT 08 — Bank Portal Behavioral Tracker

**File to create:** `simulation_portal/src/hooks/useBehavioralTracker.ts`

```
Write a React TypeScript custom hook: useBehavioralTracker.ts

The hook tracks user behavioral signals for cybersecurity analysis.

Types:
type BehavioralEvent = {
  type: 'keydown' | 'keyup' | 'mousemove' | 'click' | 'scroll' | 'pagevisit'
  timestamp: number  // Date.now()
  key?: string       // for keydown/keyup (do NOT include actual key value for passwords)
  x?: number         // for mouse events
  y?: number
  page?: string      // for pagevisit
  element?: string   // 'password' | 'email' | 'other' (not the actual value)
}

Hook: useBehavioralTracker(userId: string, sessionId: string)
- Uses useRef for the events buffer (NOT useState — avoid re-renders)
- On mount: attach document-level event listeners for keydown, keyup, mousemove, click, scroll
  IMPORTANT: for keydown/keyup on password fields, set key='[REDACTED]' (never capture actual password)
  For mousemove: only record every 100ms (throttle to prevent flooding)
- Set up interval to flush events to API every 10 seconds:
  POST ${import.meta.env.VITE_NEUROSHIELD_URL}/api/behavioral 
  with body {user_id, session_id, events: lastNEvents}
  After flush: clear the buffer
- On unmount: remove all event listeners, clear interval, do final flush
- Returns: { sessionId, eventCount: number, lastVerdict: string | null, startTracking, stopTracking }
- lastVerdict: poll GET /api/verdicts/{userId} every 5 seconds, store latest verdict string

IMPORTANT: This hook MUST NOT cause any re-renders when events are captured. All event state is in refs.
Add JSDoc comment explaining the security purpose of this hook.
```

---

## PROMPT 09 — Integration Tests

**File to create:** `tests/test_integration.py`

```
Write a pytest integration test file tests/test_integration.py for NeuroShield.

Use pytest fixtures for setup/teardown. 
Mock external services (PostgreSQL, Kafka) using unittest.mock where needed.
Import from: core.engine, core.snn.encoder, core.snn.network, core.lnn.reservoir,
             core.behavioral.profiler, core.deception.honeypot

FIXTURES:
- engine(): creates DecisionEngine with mocked model loading
- profiler(): creates BehavioralProfiler with in-memory storage (no DB)
- sample_packets(): returns list of 100 dicts representing normal BENIGN traffic features

HELPER: make_session(typing_speed: str) -> dict
  typing_speed: 'normal' (80ms intervals), 'fast' (30ms), 'random' (10-500ms random)
  Returns: {session_id, user_id, source_ip, packets: sample_packets, behavioral_events: generated events}

TESTS:
def test_legitimate_user(profiler, engine):
  # Build profile with 10 normal sessions for user 'alice'
  # Analyze an 11th normal session
  # Assert verdict == 'LEGITIMATE' and confidence < 0.35

def test_forgetful_user(profiler, engine):
  # Build profile with 5 normal sessions for 'bob'
  # Analyze a session with 2x slower typing
  # Assert verdict in ['FORGETFUL_USER'] and 0.3 <= behavioral_delta <= 0.7

def test_hacker(profiler, engine):
  # Build profile with 5 normal sessions for 'charlie'
  # Analyze a session with random typing + rapid page visits
  # Assert verdict == 'HACKER' and confidence > 0.7

def test_honeypot_detection():
  # Create HoneypotManager
  # Assert is_honeypot_request('/api/admin') == True
  # Assert is_honeypot_request('/api/analyze') == False
  # Assert is_honeypot_request('/.env') == True

def test_snn_ddos_detection(engine):
  # Create 1000 packets with features typical of SYN flood (high packet rate, small size, SYN flag)
  # Run through SNN encoder + detector
  # Assert snn_score > 0.8

def test_session_vector_shape():
  # Create 200 behavioral events with typing + mouse data
  # Call extract_session_vector(events)
  # Assert output shape == (20,) and no NaN values

def test_report_generation(tmp_path):
  # Mock DB queries to return 10 fake verdicts
  # Call report generator with output_dir=tmp_path
  # Assert CSV file exists and has correct columns
  # Assert CSV has 10 rows (plus header)
```

---

## PROMPT 10 — Demo Reset Script

**File to create:** `redteam/reset_demo.py`

```
Write a Python script redteam/reset_demo.py that resets the NeuroShield demo environment:

1. Connects to PostgreSQL (connection from environment variables)
2. Truncates these tables (in correct FK order to avoid constraint errors):
   sandbox_actions, honeypot_hits, alerts, verdicts, sessions
   (DO NOT truncate: users, user_profiles — we want to keep behavioral profiles)
3. Resets all user_profiles back to their baseline (pre-seeded) state by:
   Calling seed_profiles.py logic as an importable function reset_profiles()
4. Clears Redis cache: redis.flushdb()
5. Prints confirmation: "Demo reset complete. Tables cleared: [list]. Profiles restored: [count] users."
6. Logs the reset event to a local file: logs/demo_resets.log with timestamp

Run with: python redteam/reset_demo.py
Should complete in under 10 seconds.
Import seed_profiles from redteam.seed_profiles (make sure that module is importable).
```

---

## PROMPT 11 — Inference Service (Pipeline Orchestrator)

**File to create:** `inference_service/main.py`

> Runs as `inference-service` container. Consumes from Kafka `extracted-features`, runs SNN → LNN → XGBoost ensemble, writes ThreatVerdict to PostgreSQL and publishes to Kafka `verdicts`.

```
Write inference_service/main.py — the core ML inference microservice for NeuroShield.

Imports:
  from core.snn.encoder import SpikeEncoder
  from core.snn.network import SNNAnomalyDetector
  from core.lnn.reservoir import LiquidReservoir
  from core.inference.xgboost_classifier import XGBoostThreatClassifier

On startup:
  Load SpikeEncoder(n_features=80)
  Load SNNAnomalyDetector from 'weights/snn_best.pt'
  Load LiquidReservoir from 'weights/lnn_reservoir.pt'
  Load XGBoostThreatClassifier from 'weights/xgb_classifier.pkl'
  Connect Kafka consumer: group_id='inference-service', topic='extracted-features'
  Connect Kafka producer: topic='verdicts'
  Connect asyncpg pool to PostgreSQL

Main loop — for each message from extracted-features:
  msg = {session_id, user_id, source_ip, features: [[80 floats], ...], behavioral_delta: float, timestamp}
  
  Step 1 (SNN): spike_train = encoder.encode(features)
               logits, snn_score = snn_model(spike_train)
  Step 2 (LNN): _, lnn_state = reservoir(feature_tensor)
               lnn_class_probs = softmax(linear_readout(lnn_state))
  Step 3 (XGBoost): fv = xgb.build_feature_vector(snn_score, lnn_state, behavioral_delta, lnn_class_probs)
                   result = xgb.predict(fv)
  
  Map verdict string to human label:
    'BENIGN' → 'LEGITIMATE', confidence < 0.5 → 'FORGETFUL_USER', else → 'HACKER'

  Write ThreatVerdict to postgres table 'verdicts':
    (session_id, user_id, source_ip, verdict, confidence,
     snn_score, lnn_class, xgb_confidence, behavioral_delta, created_at)
  
  Publish to Kafka 'verdicts' topic: same dict as above as JSON.

Log: each verdict at INFO level. Log inference latency (target < 100ms).
Handle: model loading failures → log CRITICAL and exit(1).
```

**Verify with:**
```bash
docker-compose up inference-service
# Should log: "Inference service ready. Listening on extracted-features..."
# Send a test message to extracted-features; check DB for a verdict row.
```

---

## PROMPT 12 — Feedback & Retraining Service

**File to create:** `feedback_service/main.py` + `retraining_service/retrain.py`

```
Write two Python files for the NeuroShield continuous learning loop.

FILE: feedback_service/main.py
- Kafka consumer: group_id='feedback-service', topic='verdicts'
- For each verdict message:
  If verdict == 'HACKER' or verdict == 'FORGETFUL_USER':
    Write to postgres table 'labeled_training_data':
      (session_id, features JSON, label: str, created_at)
    Publish to Kafka topic 'feedback-labels': {session_id, label, feature_count}
  Log: "Labeled session {session_id} as {label}"
- On startup log: "Feedback service started. Writing labels to labeled_training_data."

FILE: retraining_service/retrain.py
- Runs on schedule (RETRAIN_INTERVAL_HOURS from env, default 24)
- On each scheduled run:
  1. Query postgres: SELECT features, label FROM labeled_training_data
     WHERE created_at > NOW() - INTERVAL '48 hours'
     AND label != 'LEGITIMATE'
  2. If fewer than 500 new rows: log "Insufficient new data, skipping retraining" and sleep.
  3. Load existing datasets/processed/unified_train.csv
  4. Append new labeled rows to it (features must match column order from datasets/feature_columns.txt)
  5. Retrain XGBoostThreatClassifier on combined dataset (call .train())
  6. Save new model to weights/xgb_classifier.pkl (overwrites previous)
  7. Log: "Retraining complete. New F1: {f1:.3f}. Model saved to weights/xgb_classifier.pkl"
  8. Send Kafka message to topic 'model-updates': {timestamp, f1_macro, rows_added}
  Note: inference-service watches for weights/xgb_classifier.pkl mtime change and hot-reloads XGBoost.
  SNN and LNN weights are NOT retrained automatically (require full training run by @ml).
- Schedule with: schedule.every(RETRAIN_INTERVAL_HOURS).hours.do(run_retraining)
```

**Verify with:**
```bash
docker-compose up feedback-service retraining-service
# feedback-service: should log startup message
# retraining-service: should log "Insufficient new data, skipping retraining" on first run
```

---

## ITERATIVE DEBUGGING PROMPTS

### When you get an ImportError:
```
I got this ImportError when running [filename.py]:
[PASTE EXACT ERROR]

The installed packages are:
[PASTE: pip show norse torch scikit-learn]

Fix the import statement only. Do not change any other code.
```

### When tests fail:
```
This pytest test is failing:
[PASTE TEST NAME AND ASSERTION ERROR]

The relevant source code is:
[PASTE the function being tested]

Fix the source code (not the test) so the test passes. Maintain the same function signature.
```

### When Antigravity's code has wrong shapes:
```
The tensor shape is wrong. Expected [100, 4, 400] but got [4, 100, 400].
The relevant code is:
[PASTE the forward() method]
Fix ONLY the dimension ordering. All other logic stays the same.
```

### When Docker build fails:
```
docker build failed with this error:
[PASTE DOCKER BUILD ERROR]

The Dockerfile is:
[PASTE Dockerfile]

Fix the Dockerfile. Explain what was wrong in one sentence before showing the fix.
```
