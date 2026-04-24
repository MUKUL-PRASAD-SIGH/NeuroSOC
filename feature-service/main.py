"""
main.py — NeuroShield Feature Engine Service
Phase 2 per MASTER_PLAN.md

Consumes 'raw-packets' Kafka topic.
Groups packets into bidirectional flows.
Extracts exactly 80 CICFlowMeter-style features per completed flow.
Publishes to 'extracted-features' Kafka topic.

CHECKPOINT (Testing Gate 2):
  docker-compose exec kafka kafka-console-consumer \\
    --topic extracted-features --bootstrap-server kafka:9092 --max-messages 3
  → Each message must have:
    - 'features' array of exactly 80 floats
    - No NaN values
    - 'flow_id', 'src_ip', 'dst_ip', 'n_packets' keys

IMPORTANT: The EXACT same 80-feature order used here must be replicated at
inference time. Column order is saved to /data/feature_columns.txt.

Flow completion triggers:
  1. FLOW_TIMEOUT_SECONDS of inactivity (default 3s)
  2. TCP FIN or RST flag seen

LRU eviction: flow table capped at MAX_FLOWS (100k) to prevent OOM under DDoS.
"""

from __future__ import annotations

import json
import logging
import math
import os
import statistics
import threading
import time
import uuid
import joblib
from collections import OrderedDict
from typing import Any

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [feature] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

# ─── config ───────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP       = os.getenv("KAFKA_BOOTSTRAP",        "kafka:9092")
FLOW_TIMEOUT_SECONDS  = float(os.getenv("FLOW_TIMEOUT_SECONDS", "3.0"))
MAX_FLOWS             = int(os.getenv("MAX_FLOWS",          "100000"))
IN_TOPIC              = "raw-packets"
OUT_TOPIC             = "extracted-features"
LOG_EVERY             = 100    # log every N flows

def _resolve_data_dir() -> str:
    configured = os.getenv("DATA_DIR")
    if configured:
        return configured

    container_data_dir = "/data"
    if os.name != "nt" and os.path.isdir(container_data_dir) and os.access(container_data_dir, os.W_OK):
        return container_data_dir

    # Local imports on Windows/macOS/Linux should fall back to the repo data dir.
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


DATA_DIR              = _resolve_data_dir()
FEATURE_COLUMNS_FILE  = os.path.join(DATA_DIR, "feature_columns.txt")

os.makedirs(DATA_DIR, exist_ok=True)

# ─── Feature names (exactly 80) ───────────────────────────────────────────────
# CRITICAL: this list defines the column order expected by all downstream models.
FEATURE_NAMES: list[str] = [
    # 1-4: basic flow timing
    "flow_duration",
    "flow_bytes_per_s",
    "flow_packets_per_s",
    "flow_iat_mean",
    "flow_iat_total",
    # 5-8: flow IAT
    "flow_iat_std",
    "flow_iat_max",
    "flow_iat_min",
    # 9-14: fwd packet lengths
    "fwd_packets_total",
    "fwd_bytes_total",
    "fwd_pkt_len_max",
    "fwd_pkt_len_min",
    "fwd_pkt_len_mean",
    "fwd_pkt_len_std",
    # 15-20: bwd packet lengths
    "bwd_packets_total",
    "bwd_bytes_total",
    "bwd_pkt_len_max",
    "bwd_pkt_len_min",
    "bwd_pkt_len_mean",
    "bwd_pkt_len_std",
    # 21-30: fwd IAT
    "fwd_iat_total",
    "fwd_iat_mean",
    "fwd_iat_std",
    "fwd_iat_max",
    "fwd_iat_min",
    # 26-30: bwd IAT
    "bwd_iat_total",
    "bwd_iat_mean",
    "bwd_iat_std",
    "bwd_iat_max",
    "bwd_iat_min",
    # 31-38: TCP flags (count over flow)
    "fin_flag_count",
    "syn_flag_count",
    "rst_flag_count",
    "psh_flag_count",
    "ack_flag_count",
    "urg_flag_count",
    "cwe_flag_count",
    "ece_flag_count",
    # 39-44: header lengths
    "fwd_header_length",
    "bwd_header_length",
    "fwd_header_length_again",   # CICFlowMeter has duplicate, kept for compat
    "fwd_packets_per_s",
    "bwd_packets_per_s",
    "down_up_ratio",
    # 45-52: packet size stats (both dirs)
    "pkt_len_min",
    "pkt_len_max",
    "pkt_len_mean",
    "pkt_len_std",
    "pkt_len_variance",
    "avg_packet_size",
    "avg_fwd_segment_size",
    "avg_bwd_segment_size",
    # 53-60: subflows
    "subflow_fwd_packets",
    "subflow_fwd_bytes",
    "subflow_bwd_packets",
    "subflow_bwd_bytes",
    # 57-60: init window bytes
    "init_win_bytes_fwd",
    "init_win_bytes_bwd",
    "act_data_pkt_fwd",
    "min_seg_size_fwd",
    # 61-68: active/idle stats
    "active_mean",
    "active_std",
    "active_max",
    "active_min",
    "idle_mean",
    "idle_std",
    "idle_max",
    "idle_min",
    # 69-72: PSH / URG flags direction
    "fwd_psh_flags",
    "bwd_psh_flags",
    "fwd_urg_flags",
    "bwd_urg_flags",
    # 73-76: percentile features
    "fwd_pkt_len_p25",
    "fwd_pkt_len_p75",
    "bwd_pkt_len_p25",
    "bwd_pkt_len_p75",
    # 77-80: flow-level ratios
    "syn_ratio",
    "ack_ratio",
    "bytes_per_packet",
    "packet_size_variance",
]

assert len(FEATURE_NAMES) == 80, f"Feature list must be exactly 80, got {len(FEATURE_NAMES)}"

# Save column order so inference service uses the same layout
with open(FEATURE_COLUMNS_FILE, "w") as _f:
    _f.write("\n".join(FEATURE_NAMES) + "\n")
log.info("Feature columns written to %s", FEATURE_COLUMNS_FILE)


# ─── Flow accumulation ────────────────────────────────────────────────────────
class FlowRecord:
    """Accumulates raw packet data for one bidirectional network flow."""

    __slots__ = (
        "key", "start_ts", "last_ts",
        "fwd_pkts", "bwd_pkts",
        "fwd_lens", "bwd_lens",
        "all_iats", "fwd_iats", "bwd_iats",
        "flags",
        "last_fwd_ts", "last_bwd_ts",
        "active_periods", "idle_periods",
        "_prev_ts",
    )

    def __init__(self, key: tuple, ts: float) -> None:
        self.key        = key
        self.start_ts   = ts
        self.last_ts    = ts
        self._prev_ts   = ts
        self.fwd_pkts:  list[int]   = []
        self.bwd_pkts:  list[int]   = []
        self.fwd_lens:  list[int]   = []
        self.bwd_lens:  list[int]   = []
        self.all_iats:  list[float] = []
        self.fwd_iats:  list[float] = []
        self.bwd_iats:  list[float] = []
        self.flags:     dict[str, int] = {
            "SYN": 0, "ACK": 0, "FIN": 0, "RST": 0,
            "PSH": 0, "URG": 0, "CWE": 0, "ECE": 0,
        }
        self.last_fwd_ts: float | None  = None
        self.last_bwd_ts: float | None  = None
        self.active_periods: list[float] = []
        self.idle_periods:   list[float] = []

    def add_packet(self, pkt: dict, direction: str) -> None:
        ts  = float(pkt.get("timestamp", time.time()))
        ln  = int(pkt.get("length", 0))
        iat = ts - self._prev_ts
        self._prev_ts = ts
        self.last_ts  = ts

        if iat > 0:
            self.all_iats.append(iat)
        if iat > 1.0:
            self.idle_periods.append(iat)
        else:
            self.active_periods.append(iat)

        flags = pkt.get("flags", {})
        for k in ("SYN", "ACK", "FIN", "RST", "PSH", "URG", "CWE", "ECE"):
            if flags.get(k):
                self.flags[k] += 1

        if direction == "fwd":
            self.fwd_pkts.append(ln)
            self.fwd_lens.append(ln)
            if self.last_fwd_ts is not None:
                self.fwd_iats.append(ts - self.last_fwd_ts)
            self.last_fwd_ts = ts
        else:
            self.bwd_pkts.append(ln)
            self.bwd_lens.append(ln)
            if self.last_bwd_ts is not None:
                self.bwd_iats.append(ts - self.last_bwd_ts)
            self.last_bwd_ts = ts

    def is_complete(self) -> bool:
        return (
            self.flags["FIN"] > 0
            or self.flags["RST"] > 0
            or (time.time() - self.last_ts) > FLOW_TIMEOUT_SECONDS
        )


# ─── safe stat helpers ────────────────────────────────────────────────────────
def _safe(fn, seq, default: float = 0.0) -> float:
    try:
        return float(fn(seq)) if seq else default
    except Exception:
        return default


def _percentile(seq: list[float], p: float) -> float:
    if not seq:
        return 0.0
    s = sorted(seq)
    k = (len(s) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _safe_div(n: float, d: float) -> float:
    return float(n) / float(d) if float(d) > 1e-6 else 0.0


# ─── Scaler ───────────────────────────────────────────────────────────────────
SCALER_PATH = os.path.join(DATA_DIR, "scaler.pkl")
_scaler = None
_scaler_loaded = False

def _get_scaler():
    global _scaler, _scaler_loaded
    if not _scaler_loaded:
        _scaler_loaded = True
        try:
            if os.path.exists(SCALER_PATH):
                _scaler = joblib.load(SCALER_PATH)
                log.info("✅ MinMaxScaler loaded from %s", SCALER_PATH)
            else:
                log.warning("⚠️ No scaler found at %s. Returning raw features.", SCALER_PATH)
        except Exception as exc:
            log.error("Failed to load scaler: %s", exc)
    return _scaler


# ─── Feature extraction ───────────────────────────────────────────────────────
def extract_features(flow: FlowRecord) -> list[float]:
    """Extract exactly 80 CICFlowMeter-style features from a FlowRecord."""
    # Enforce minimum 1 millisecond duration to prevent rate explosions
    duration  = max(flow.last_ts - flow.start_ts, 0.001)
    all_lens  = flow.fwd_lens + flow.bwd_lens
    n_pkts    = len(all_lens)
    total_bytes = sum(all_lens)

    fwd_bytes = sum(flow.fwd_lens)
    bwd_bytes = sum(flow.bwd_lens)

    # --- flow IAT ---
    flow_iat_mean = _safe(statistics.mean, flow.all_iats)
    flow_iat_std  = _safe(statistics.pstdev, flow.all_iats)
    flow_iat_max  = _safe(max, flow.all_iats)
    flow_iat_min  = _safe(min, flow.all_iats)

    # --- fwd/bwd pkt len ---
    fwd_len_max  = _safe(max, flow.fwd_lens)
    fwd_len_min  = _safe(min, flow.fwd_lens)
    fwd_len_mean = _safe(statistics.mean, flow.fwd_lens)
    fwd_len_std  = _safe(statistics.pstdev, flow.fwd_lens)

    bwd_len_max  = _safe(max, flow.bwd_lens)
    bwd_len_min  = _safe(min, flow.bwd_lens)
    bwd_len_mean = _safe(statistics.mean, flow.bwd_lens)
    bwd_len_std  = _safe(statistics.pstdev, flow.bwd_lens)

    # --- fwd IAT ---
    fwd_iat_total = sum(flow.fwd_iats)
    fwd_iat_mean  = _safe(statistics.mean, flow.fwd_iats)
    fwd_iat_std   = _safe(statistics.pstdev, flow.fwd_iats)
    fwd_iat_max   = _safe(max, flow.fwd_iats)
    fwd_iat_min   = _safe(min, flow.fwd_iats)

    # --- bwd IAT ---
    bwd_iat_total = sum(flow.bwd_iats)
    bwd_iat_mean  = _safe(statistics.mean, flow.bwd_iats)
    bwd_iat_std   = _safe(statistics.pstdev, flow.bwd_iats)
    bwd_iat_max   = _safe(max, flow.bwd_iats)
    bwd_iat_min   = _safe(min, flow.bwd_iats)

    # --- packet size stats (all dirs) ---
    pkt_len_min  = _safe(min, all_lens)
    pkt_len_max  = _safe(max, all_lens)
    pkt_len_mean = _safe(statistics.mean, all_lens)
    pkt_len_std  = _safe(statistics.pstdev, all_lens)
    pkt_len_var  = pkt_len_std ** 2

    # --- active / idle ---
    active_mean = _safe(statistics.mean, flow.active_periods)
    active_std  = _safe(statistics.pstdev, flow.active_periods)
    active_max  = _safe(max, flow.active_periods)
    active_min  = _safe(min, flow.active_periods)
    idle_mean   = _safe(statistics.mean, flow.idle_periods)
    idle_std    = _safe(statistics.pstdev, flow.idle_periods)
    idle_max    = _safe(max, flow.idle_periods)
    idle_min    = _safe(min, flow.idle_periods)

    n_fwd = len(flow.fwd_pkts)
    n_bwd = len(flow.bwd_pkts)
    down_up_ratio = _safe_div(bwd_bytes, fwd_bytes)
    bytes_per_pkt = _safe_div(total_bytes, n_pkts)

    syn_total = flow.flags["SYN"]
    ack_total = flow.flags["ACK"]
    syn_ratio = _safe_div(syn_total, n_pkts)
    ack_ratio = _safe_div(ack_total, n_pkts)

    features = [
        # 1-5
        duration,
        _safe_div(total_bytes, duration),
        _safe_div(n_pkts, duration),
        flow_iat_mean,
        sum(flow.all_iats),
        # 5-8
        flow_iat_std,
        flow_iat_max,
        flow_iat_min,
        # 9-14
        float(n_fwd),
        float(fwd_bytes),
        fwd_len_max,
        fwd_len_min,
        fwd_len_mean,
        fwd_len_std,
        # 15-20
        float(n_bwd),
        float(bwd_bytes),
        bwd_len_max,
        bwd_len_min,
        bwd_len_mean,
        bwd_len_std,
        # 21-30 (fwd+bwd IAT)
        fwd_iat_total,
        fwd_iat_mean,
        fwd_iat_std,
        fwd_iat_max,
        fwd_iat_min,
        bwd_iat_total,
        bwd_iat_mean,
        bwd_iat_std,
        bwd_iat_max,
        bwd_iat_min,
        # 31-38 TCP flags
        float(flow.flags["FIN"]),
        float(flow.flags["SYN"]),
        float(flow.flags["RST"]),
        float(flow.flags["PSH"]),
        float(flow.flags["ACK"]),
        float(flow.flags["URG"]),
        float(flow.flags["CWE"]),
        float(flow.flags["ECE"]),
        # 39-44 headers / rates
        float(n_fwd * 20),      # approx fwd header bytes (IP+TCP = 40 typical, 20 min)
        float(n_bwd * 20),
        float(n_fwd * 20),      # duplicate per CICFlowMeter convention
        _safe_div(n_fwd, duration),
        _safe_div(n_bwd, duration),
        down_up_ratio,
        # 45-52 packet size
        pkt_len_min,
        pkt_len_max,
        pkt_len_mean,
        pkt_len_std,
        pkt_len_var,
        bytes_per_pkt,
        fwd_len_mean,           # avg_fwd_segment_size ≈ mean fwd len
        bwd_len_mean,           # avg_bwd_segment_size ≈ mean bwd len
        # 53-60 subflows + init window
        float(n_fwd),           # subflow_fwd_packets (1 subflow)
        float(fwd_bytes),
        float(n_bwd),
        float(bwd_bytes),
        float(fwd_len_max),     # init_win_bytes_fwd proxy
        float(bwd_len_max),     # init_win_bytes_bwd proxy
        float(n_fwd),           # act_data_pkt_fwd
        fwd_len_min,            # min_seg_size_fwd
        # 61-68 active/idle
        active_mean,
        active_std,
        active_max,
        active_min,
        idle_mean,
        idle_std,
        idle_max,
        idle_min,
        # 69-72 PSH/URG directional
        float(flow.flags["PSH"]),
        0.0,                    # bwd_psh_flags (not tracked separately from TCP layer)
        float(flow.flags["URG"]),
        0.0,                    # bwd_urg_flags
        # 73-76 percentiles
        _percentile(flow.fwd_lens, 25),
        _percentile(flow.fwd_lens, 75),
        _percentile(flow.bwd_lens, 25),
        _percentile(flow.bwd_lens, 75),
        # 77-80 ratios
        syn_ratio,
        ack_ratio,
        bytes_per_pkt,
        pkt_len_var,
    ]

    # Sanitize: replace NaN / Inf with 0.0
    features = [0.0 if (math.isnan(v) or math.isinf(v)) else round(v, 6) for v in features]

    # Normalize values to 0.0 -> 1.0 using trained scaler from Phase 3
    scaler = _get_scaler()
    if scaler is not None:
        try:
            scaled = scaler.transform([features])[0]
            features = [float(v) for v in scaled]
        except Exception as exc:
            log.error("Scaling error: %s", exc)

    log.info("Extracted Feature Length: %d", len(features))
    assert len(features) == 80, f"BUG: feature count is {len(features)}, expected 80"
    return features


# ─── Kafka helpers ────────────────────────────────────────────────────────────
def _build_consumer() -> KafkaConsumer:
    for attempt in range(10):
        try:
            c = KafkaConsumer(
                IN_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP,
                group_id="feature-engine",
                auto_offset_reset="latest",
                enable_auto_commit=True,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            )
            log.info("✅ Kafka consumer connected (attempt %d/10).", attempt + 1)
            return c
        except NoBrokersAvailable:
            log.warning("Kafka not ready (%d/10). Waiting 15s…", attempt + 1)
            time.sleep(15)
    raise RuntimeError("Could not connect Kafka consumer.")


def _build_producer() -> KafkaProducer:
    for attempt in range(10):
        try:
            p = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                retries=5,
                linger_ms=10,
                compression_type="gzip",
            )
            log.info("✅ Kafka producer connected (attempt %d/10).", attempt + 1)
            return p
        except NoBrokersAvailable:
            log.warning("Kafka not ready (%d/10). Waiting 15s…", attempt + 1)
            time.sleep(15)
    raise RuntimeError("Could not connect Kafka producer.")


# ─── Flow table (LRU capped at MAX_FLOWS) ────────────────────────────────────
_flow_table: OrderedDict[tuple, FlowRecord] = OrderedDict()
_table_lock = threading.Lock()


def _get_or_create_flow(key: tuple, ts: float) -> FlowRecord:
    with _table_lock:
        if key in _flow_table:
            _flow_table.move_to_end(key)    # LRU touch
            return _flow_table[key]
        if len(_flow_table) >= MAX_FLOWS:
            oldest_key, _ = next(iter(_flow_table.items()))
            del _flow_table[oldest_key]
            log.debug("LRU evicted flow %s", oldest_key)
        flow = FlowRecord(key, ts)
        _flow_table[key] = flow
        return flow


def _flow_key(pkt: dict) -> tuple:
    """Canonical bidirectional flow key — (smaller_ip, larger_ip, …)."""
    src = pkt.get("src_ip", ""), int(pkt.get("src_port", 0))
    dst = pkt.get("dst_ip", ""), int(pkt.get("dst_port", 0))
    proto = pkt.get("protocol", "OTHER")
    if src <= dst:
        return (src[0], dst[0], src[1], dst[1], proto)
    return (dst[0], src[0], dst[1], src[1], proto)


def _direction(pkt: dict, key: tuple) -> str:
    return "fwd" if pkt.get("src_ip", "") == key[0] else "bwd"


# ─── Stale-flow janitor ───────────────────────────────────────────────────────
def _janitor(producer: KafkaProducer) -> None:
    """Background thread: flush completed/stale flows every 1s."""
    flow_count = 0
    while True:
        time.sleep(1.0)
        completed: list[tuple] = []
        with _table_lock:
            for key, flow in list(_flow_table.items()):
                if flow.is_complete():
                    completed.append(key)

        for key in completed:
            with _table_lock:
                flow = _flow_table.pop(key, None)
            if flow is None:
                continue
            try:
                feats = extract_features(flow)
                msg = {
                    "flow_id":   str(uuid.uuid4()),
                    "src_ip":    key[0],
                    "dst_ip":    key[1],
                    "src_port":  key[2],
                    "dst_port":  key[3],
                    "protocol":  key[4],
                    "features":  feats,
                    "timestamp": flow.last_ts,
                    "n_packets": len(flow.fwd_pkts) + len(flow.bwd_pkts),
                }
                producer.send(OUT_TOPIC, value=msg)
                flow_count += 1
                if flow_count % LOG_EVERY == 0:
                    log.info("📊 Extracted %d flows → '%s'.", flow_count, OUT_TOPIC)
            except Exception as exc:
                log.error("Feature extraction error: %s", exc)


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main() -> None:
    log.info("Feature Engine starting. Flow timeout: %.1fs  Max flows: %d",
             FLOW_TIMEOUT_SECONDS, MAX_FLOWS)

    consumer = _build_consumer()
    producer = _build_producer()

    # Start stale-flow janitor thread
    t = threading.Thread(target=_janitor, args=(producer,), daemon=True, name="janitor")
    t.start()

    log.info("✅ Feature Engine ready. Consuming '%s' → publishing '%s'.",
             IN_TOPIC, OUT_TOPIC)

    for msg in consumer:
        try:
            pkt = msg.value
            ts  = float(pkt.get("timestamp", time.time()))
            key = _flow_key(pkt)
            flow = _get_or_create_flow(key, ts)
            direction = _direction(pkt, key)
            flow.add_packet(pkt, direction)
        except Exception as exc:
            log.debug("Packet processing error: %s", exc)


if __name__ == "__main__":
    main()
