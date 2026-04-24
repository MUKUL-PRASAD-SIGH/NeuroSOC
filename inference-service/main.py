from __future__ import annotations

import json
import logging
import os
import asyncio
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
from pydantic import BaseModel, Field

try:
    import psycopg2
    from psycopg2.extras import Json, RealDictCursor
except ImportError:  # pragma: no cover - keeps importable in lightweight environments
    psycopg2 = None
    RealDictCursor = None

    def Json(value: Any) -> Any:  # type: ignore[misc]
        return value

from core.behavioral.signals import extract_session_vector
from core.engine import DecisionEngine, ThreatVerdict


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [inference] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
DATABASE_URL = os.getenv("DATABASE_URL", "")
INPUT_TOPIC = os.getenv("INFERENCE_INPUT_TOPIC", "extracted-features")
VERDICTS_TOPIC = os.getenv("VERDICTS_TOPIC", "verdicts")
ALERTS_TOPIC = os.getenv("ALERTS_TOPIC", "alerts")
GROUP_ID = os.getenv("INFERENCE_GROUP_ID", "inference-service")
MODEL_DIR = Path(os.getenv("MODEL_PATH", "/models"))
MODEL_VERSION_PATH = Path(os.getenv("MODEL_VERSION_FILE", str(MODEL_DIR / "model_version.json")))
MODEL_POLL_SECONDS = float(os.getenv("MODEL_POLL_SECONDS", "60"))
CONSUMER_RETRY_SECONDS = float(os.getenv("CONSUMER_RETRY_SECONDS", "5"))
LATEST_VERDICTS_LIMIT = int(os.getenv("LATEST_VERDICTS_LIMIT", "200"))
HOST = os.getenv("INFERENCE_HOST", "0.0.0.0")
PORT = int(os.getenv("INFERENCE_PORT", "8000"))


class SessionAnalyzeRequest(BaseModel):
    session_id: str
    user_id: str = "unknown-user"
    source_ip: str = "unknown"
    flow_features: list[float] = Field(..., min_length=80, max_length=80)
    behavioral_events: list[dict[str, Any]] = Field(default_factory=list)
    behavioral_vector: list[float] | None = None
    session_sequence: list[list[float]] | None = None
    unique_dst_ports: int | None = None
    login_attempts: int | None = None
    all_different_passwords: bool | None = None
    sql_injection_detected: bool | None = None
    timestamp: float | None = None


class BehavioralVectorRequest(BaseModel):
    events: list[dict[str, Any]] = Field(default_factory=list)


class BankLoginRequest(BaseModel):
    email: str = "anonymous@local"
    password: str = ""
    session_id: str | None = None


class BehavioralIngestRequest(BaseModel):
    user_id: str = "unknown-user"
    session_id: str = "session-unknown"
    events: list[dict[str, Any]] = Field(default_factory=list)


class BankTransferRequest(BaseModel):
    user_id: str = "unknown-user"
    session_id: str | None = None
    recipient: str = ""
    amount: float = 0.0
    memo: str = ""


class SecurityEventRequest(BaseModel):
    user_id: str = "unknown-user"
    session_id: str | None = None
    source: str | None = None
    attack_type: str | None = None
    payload: str | None = None


class VerdictRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self):
        if not self.database_url:
            return None
        if psycopg2 is None or RealDictCursor is None:
            raise RuntimeError("psycopg2 is required to persist inference verdicts.")
        return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)

    def bootstrap(self) -> None:
        conn = self._connect()
        if conn is None:
            log.info("DATABASE_URL not configured; inference DB persistence disabled.")
            return
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS verdicts (
                        id BIGSERIAL PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        source_ip TEXT NOT NULL,
                        verdict TEXT NOT NULL,
                        confidence DOUBLE PRECISION NOT NULL,
                        snn_score DOUBLE PRECISION NOT NULL,
                        lnn_class TEXT NOT NULL,
                        xgb_class TEXT NOT NULL,
                        behavioral_delta DOUBLE PRECISION NOT NULL,
                        model_version TEXT NOT NULL,
                        features JSONB NOT NULL,
                        features_dict JSONB NOT NULL DEFAULT '{}'::jsonb,
                        flow_features JSONB NOT NULL,
                        timestamp DOUBLE PRECISION NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS alerts (
                        id BIGSERIAL PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        source_ip TEXT NOT NULL,
                        verdict TEXT NOT NULL,
                        confidence DOUBLE PRECISION NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
        conn.close()

    def save_verdict(self, verdict: ThreatVerdict) -> None:
        conn = self._connect()
        if conn is None:
            return
        with conn:
            with conn.cursor() as cur:
                feature_vector = self._ordered_flow_features(verdict.features_dict)
                cur.execute(
                    """
                    INSERT INTO verdicts (
                        session_id,
                        user_id,
                        source_ip,
                        verdict,
                        confidence,
                        snn_score,
                        lnn_class,
                        xgb_class,
                        behavioral_delta,
                        model_version,
                        features,
                        features_dict,
                        flow_features,
                        timestamp
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        verdict.session_id,
                        verdict.user_id,
                        verdict.source_ip,
                        verdict.verdict,
                        verdict.confidence,
                        verdict.snn_score,
                        verdict.lnn_class,
                        verdict.xgb_class,
                        verdict.behavioral_delta,
                        verdict.model_version,
                        Json(feature_vector),
                        Json(verdict.features_dict),
                        Json(feature_vector),
                        verdict.timestamp,
                    ),
                )
                if verdict.verdict == "HACKER":
                    cur.execute(
                        """
                        INSERT INTO alerts (session_id, user_id, source_ip, verdict, confidence)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            verdict.session_id,
                            verdict.user_id,
                            verdict.source_ip,
                            verdict.verdict,
                            verdict.confidence,
                        ),
                    )
        conn.close()

    @staticmethod
    def _ordered_flow_features(features_dict: dict[str, Any]) -> list[float]:
        feature_keys = sorted(key for key in features_dict.keys() if not str(key).startswith("_"))
        vector = []
        for key in feature_keys:
            value = features_dict.get(key, 0.0)
            try:
                vector.append(float(value))
            except (TypeError, ValueError):
                vector.append(0.0)
        if len(vector) < 80:
            vector.extend([0.0] * (80 - len(vector)))
        return vector[:80]


class InferenceRuntime:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._consumer_thread: threading.Thread | None = None
        self._producer: KafkaProducer | None = None
        self._consumer_connected = False
        self._producer_connected = False
        self._processed_messages = 0
        self._latest_verdicts: deque[dict[str, Any]] = deque(maxlen=LATEST_VERDICTS_LIMIT)
        self._latest_alerts: deque[dict[str, Any]] = deque(maxlen=LATEST_VERDICTS_LIMIT)
        self.repository = VerdictRepository(DATABASE_URL)

        self.engine = DecisionEngine(
            model_version_path=MODEL_VERSION_PATH,
            kafka_bootstrap=None,
            publish_callback=self._publish,
            model_poll_interval_seconds=MODEL_POLL_SECONDS,
            start_model_monitor=False,
        )

    def start(self) -> None:
        self.repository.bootstrap()
        self._ensure_producer()
        self.engine.start_model_monitor()
        if self._consumer_thread is None or not self._consumer_thread.is_alive():
            self._stop_event.clear()
            self._consumer_thread = threading.Thread(
                target=self._consume_loop,
                name="inference-kafka-consumer",
                daemon=True,
            )
            self._consumer_thread.start()
        log.info("Inference runtime started.")

    def stop(self) -> None:
        self._stop_event.set()
        self.engine.stop_model_monitor()
        if self._consumer_thread is not None:
            self._consumer_thread.join(timeout=2.0)
        if self._producer is not None:
            self._producer.close(timeout=2)
        self._producer = None
        self._producer_connected = False
        self._consumer_connected = False
        log.info("Inference runtime stopped.")

    def _ensure_producer(self) -> None:
        if self._producer is not None:
            return
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
                acks="all",
                retries=3,
            )
            self._producer_connected = True
            log.info("Kafka producer connected for verdict publishing.")
        except Exception as exc:
            self._producer = None
            self._producer_connected = False
            log.warning("Kafka producer unavailable; service will stay live without broker publishing: %s", exc)

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        with self._lock:
            if topic == VERDICTS_TOPIC:
                self._latest_verdicts.appendleft(payload)
            elif topic == ALERTS_TOPIC:
                self._latest_alerts.appendleft(payload)

        if self._producer is None:
            self._ensure_producer()
        if self._producer is None:
            return

        try:
            self._producer.send(topic, payload)
        except KafkaError as exc:
            self._producer_connected = False
            log.warning("Kafka publish failed for topic %s: %s", topic, exc)

    def _consume_loop(self) -> None:
        while not self._stop_event.is_set():
            consumer = None
            try:
                consumer = KafkaConsumer(
                    INPUT_TOPIC,
                    bootstrap_servers=KAFKA_BOOTSTRAP,
                    group_id=GROUP_ID,
                    value_deserializer=lambda payload: json.loads(payload.decode("utf-8")),
                    auto_offset_reset="latest",
                    enable_auto_commit=True,
                    consumer_timeout_ms=1000,
                )
                self._consumer_connected = True
                log.info("Kafka consumer connected for topic '%s'.", INPUT_TOPIC)

                while not self._stop_event.is_set():
                    for message in consumer:
                        self._handle_feature_message(message.value)
                        if self._stop_event.is_set():
                            break
            except NoBrokersAvailable:
                self._consumer_connected = False
                log.warning("Kafka consumer waiting for broker at %s.", KAFKA_BOOTSTRAP)
                time.sleep(CONSUMER_RETRY_SECONDS)
            except Exception as exc:
                self._consumer_connected = False
                log.exception("Inference consumer loop error: %s", exc)
                time.sleep(CONSUMER_RETRY_SECONDS)
            finally:
                if consumer is not None:
                    consumer.close()

    def _build_session_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "session_id": payload.get("flow_id", f"flow-{int(time.time() * 1000)}"),
            "user_id": payload.get("user_id") or payload.get("src_ip", "unknown-user"),
            "source_ip": payload.get("src_ip", "unknown"),
            "flow_features": payload.get("features", []),
            "timestamp": payload.get("timestamp", time.time()),
            "protocol": payload.get("protocol"),
            "dst_ip": payload.get("dst_ip"),
            "src_port": payload.get("src_port"),
            "dst_port": payload.get("dst_port"),
            "n_packets": payload.get("n_packets"),
            "session_sequence": payload.get("session_sequence"),
            "behavioral_vector": payload.get("behavioral_vector"),
            "behavioral_events": payload.get("behavioral_events"),
            "unique_dst_ports": payload.get("unique_dst_ports"),
            "login_attempts": payload.get("login_attempts"),
            "all_different_passwords": payload.get("all_different_passwords"),
            "sql_injection_detected": payload.get("sql_injection_detected"),
        }

    def _persist_verdict(self, verdict: ThreatVerdict) -> None:
        try:
            self.repository.save_verdict(verdict)
        except Exception as exc:
            log.warning("Failed to persist verdict %s to PostgreSQL: %s", verdict.session_id, exc)

    def _handle_verdict(self, verdict: ThreatVerdict) -> ThreatVerdict:
        self._persist_verdict(verdict)
        if not self._latest_verdicts or self._latest_verdicts[0].get("session_id") != verdict.session_id:
            self._latest_verdicts.appendleft(verdict.to_dict())
        if verdict.verdict == "HACKER":
            self._latest_alerts.appendleft(
                {
                    "session_id": verdict.session_id,
                    "user_id": verdict.user_id,
                    "source_ip": verdict.source_ip,
                    "confidence": verdict.confidence,
                    "verdict": verdict.verdict,
                    "timestamp": verdict.timestamp,
                }
            )
        return verdict

    def _handle_feature_message(self, payload: dict[str, Any]) -> ThreatVerdict:
        session_data = self._build_session_data(payload)
        verdict = self.engine.analyze_session(session_data)
        self._handle_verdict(verdict)
        with self._lock:
            self._processed_messages += 1
        if self._processed_messages % 50 == 0:
            log.info(
                "Processed %d extracted feature messages. Latest verdict=%s confidence=%.3f",
                self._processed_messages,
                verdict.verdict,
                verdict.confidence,
            )
        return verdict

    def analyze_manual(self, session_data: dict[str, Any]) -> ThreatVerdict:
        verdict = self.engine.analyze_session(session_data)
        return self._handle_verdict(verdict)

    def health(self) -> dict[str, Any]:
        latest_verdict = self._latest_verdicts[0] if self._latest_verdicts else None
        return {
            "status": "ok",
            "timestamp": time.time(),
            "kafka_consumer_connected": self._consumer_connected,
            "kafka_producer_connected": self._producer_connected,
            "processed_messages": self._processed_messages,
            "model_version": self.engine.current_model_version,
            "latest_verdict": latest_verdict,
            "database_enabled": bool(DATABASE_URL),
        }

    def latest_verdicts(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._latest_verdicts)[:limit]

    def latest_alerts(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._latest_alerts)[:limit]


runtime = InferenceRuntime()
portal_state_lock = threading.RLock()
portal_behavioral_events: dict[str, list[dict[str, Any]]] = {}
portal_security_flags: dict[str, set[str]] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    runtime.start()
    try:
        yield
    finally:
        runtime.stop()


app = FastAPI(title="NeuroShield Inference Service", version="0.8.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _f1_entries(validation_f1: Any) -> list[dict[str, Any]]:
    if not isinstance(validation_f1, dict):
        return []
    return [
        {"label": "SNN", "value": _safe_float(validation_f1.get("snn"), 0.0)},
        {"label": "LNN", "value": _safe_float(validation_f1.get("lnn"), 0.0)},
        {"label": "XGBoost", "value": _safe_float(validation_f1.get("xgb"), 0.0)},
    ]


def _build_flow_features(risk: float) -> list[float]:
    bounded = max(0.0, min(1.0, risk))
    vector = [0.1] * 80
    vector[2] = 15000.0 if bounded >= 0.8 else 2500.0
    vector[31] = 75.0 if bounded >= 0.65 else 15.0
    vector[56] = bounded
    vector[76] = bounded
    return vector


def _user_label(user_id: str) -> str:
    token = (user_id or "unknown user").replace("@", " ").replace(".", " ").replace("_", " ").strip()
    if not token:
        return "Unknown User"
    return " ".join(part.capitalize() for part in token.split()[:2])


def _normalize_alert(alert: dict[str, Any]) -> dict[str, Any]:
    verdict = str(alert.get("verdict", "LEGITIMATE"))
    source_ip = str(alert.get("source_ip") or alert.get("sourceIp") or "unknown")
    user_id = str(alert.get("user_id") or alert.get("userId") or "unknown-user")
    confidence = _safe_float(alert.get("confidence"), 0.0)
    timestamp = _safe_float(alert.get("timestamp"), time.time())
    return {
        "id": alert.get("id") or f"{user_id}-{int(timestamp * 1000)}",
        "severity": "critical" if verdict == "HACKER" else "medium",
        "verdict": verdict,
        "message": f"{verdict} activity observed from {source_ip}",
        "timestamp": timestamp,
        "sourceIp": source_ip,
        "userId": user_id,
        "userName": _user_label(user_id),
        "locationLabel": "Unknown location",
        "score": confidence,
        "dimensions": [],
        "recentVerdicts": [],
        "modelVersion": runtime.engine.current_model_version,
    }


def _normalize_verdict_payload(verdict: dict[str, Any]) -> dict[str, Any]:
    confidence = _safe_float(verdict.get("confidence"), 0.0)
    verdict_label = str(verdict.get("verdict") or "LEGITIMATE")
    return {
        "sessionId": verdict.get("session_id") or "session-unknown",
        "userId": verdict.get("user_id") or "unknown-user",
        "sourceIp": verdict.get("source_ip") or "unknown",
        "snnScore": _safe_float(verdict.get("snn_score"), confidence),
        "lnnClass": verdict.get("lnn_class") or verdict_label,
        "xgBoostClass": verdict.get("xgb_class") or verdict_label,
        "behavioralDelta": _safe_float(verdict.get("behavioral_delta"), 0.0),
        "confidence": confidence,
        "verdict": verdict_label,
        "modelVersion": verdict.get("model_version") or runtime.engine.current_model_version,
        "timestamp": verdict.get("timestamp") or time.time(),
    }


def _latest_verdict_for_user(user_id: str) -> dict[str, Any] | None:
    for verdict in runtime.latest_verdicts(limit=LATEST_VERDICTS_LIMIT):
        if verdict.get("user_id") == user_id:
            return verdict
    return None


def _calculate_portal_risk(user_id: str, session_id: str | None, payload_text: str = "") -> float:
    with portal_state_lock:
        flags = portal_security_flags.get(user_id, set()).copy()
        events = portal_behavioral_events.get(session_id or "", [])

    risk = 0.15
    lowered_id = user_id.lower()
    lowered_payload = payload_text.lower()

    if "honeypot" in flags:
        risk += 0.7
    if "web_attack" in flags:
        risk += 0.7
    if "hacker" in lowered_id:
        risk += 0.5
    if any(token in lowered_payload for token in ["drop", "union", "--", " or ", "script"]):
        risk += 0.7
    if len(events) > 80:
        risk += 0.2

    return max(0.0, min(0.99, risk))


def _analyze_portal_action(user_id: str, source_ip: str, risk: float, session_id: str | None = None) -> dict[str, Any]:
    verdict = runtime.analyze_manual(
        {
            "session_id": session_id or f"portal-{int(time.time() * 1000)}",
            "user_id": user_id,
            "source_ip": source_ip,
            "flow_features": _build_flow_features(risk),
            "behavioral_events": [],
            "timestamp": time.time(),
        }
    )
    payload = verdict.to_dict()
    return _normalize_verdict_payload(payload)


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "neuroshield-inference",
        "phase": 8,
        "status": "live",
        "input_topic": INPUT_TOPIC,
        "verdicts_topic": VERDICTS_TOPIC,
        "alerts_topic": ALERTS_TOPIC,
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return runtime.health()


@app.get("/verdicts/latest")
def get_latest_verdicts(limit: int = 20) -> dict[str, Any]:
    return {"count": min(limit, LATEST_VERDICTS_LIMIT), "items": runtime.latest_verdicts(limit)}


@app.get("/alerts/latest")
def get_latest_alerts(limit: int = 20) -> dict[str, Any]:
    return {"count": min(limit, LATEST_VERDICTS_LIMIT), "items": runtime.latest_alerts(limit)}


@app.post("/analyze")
def analyze(request: SessionAnalyzeRequest) -> dict[str, Any]:
    verdict = runtime.analyze_manual(request.model_dump())
    return verdict.to_dict()


@app.post("/behavioral/vectorize")
def behavioral_vectorize(request: BehavioralVectorRequest) -> dict[str, Any]:
    return {"vector": extract_session_vector(request.events).astype(float).tolist()}


@app.post("/models/reload")
def reload_models() -> dict[str, Any]:
    swapped = runtime.engine.check_model_version()
    return {
        "reloaded": swapped,
        "active_model_version": runtime.engine.current_model_version,
    }


@app.get("/profiles/{user_id}")
def get_profile(user_id: str) -> dict[str, Any]:
    profile = runtime.engine.behavioral_profiler.load_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.to_payload()


@app.get("/api/stats")
def api_stats() -> dict[str, Any]:
    verdicts = runtime.latest_verdicts(limit=LATEST_VERDICTS_LIMIT)
    if verdicts:
        avg_risk = sum(_safe_float(item.get("confidence"), 0.0) for item in verdicts) / len(verdicts)
    else:
        avg_risk = 0.0

    hacker_detections = sum(1 for item in verdicts if item.get("verdict") == "HACKER")
    return {
        "totalTransactions": runtime.health().get("processed_messages", 0),
        "hackerDetections": hacker_detections,
        "avgRiskScore": round(avg_risk, 3),
        "liveAlerts": len(runtime.latest_alerts(limit=LATEST_VERDICTS_LIMIT)),
    }


@app.get("/api/model/version")
def api_model_version() -> dict[str, Any]:
    validation_f1 = getattr(runtime.engine, "current_validation_f1", {})
    return {
        "versions": [
            {"label": "Active Model", "value": runtime.engine.current_model_version},
            {"label": "Inference Topic", "value": INPUT_TOPIC},
            {"label": "Verdicts Topic", "value": VERDICTS_TOPIC},
        ],
        "validationF1": _f1_entries(validation_f1),
        "lastRetrainedAt": None,
    }


@app.get("/api/alerts")
def api_alerts(limit: int = 50) -> list[dict[str, Any]]:
    alerts = runtime.latest_alerts(limit=min(max(limit, 1), 200))
    return [_normalize_alert(alert) for alert in alerts]


@app.get("/api/verdicts/current")
def api_verdict_current() -> dict[str, Any]:
    verdicts = runtime.latest_verdicts(limit=1)
    if not verdicts:
        return {
            "sessionId": "none",
            "userId": "unknown-user",
            "sourceIp": "unknown",
            "snnScore": 0.0,
            "lnnClass": "LEGITIMATE",
            "xgBoostClass": "LEGITIMATE",
            "behavioralDelta": 0.0,
            "confidence": 0.0,
            "verdict": "LEGITIMATE",
            "modelVersion": runtime.engine.current_model_version,
            "timestamp": time.time(),
        }
    return _normalize_verdict_payload(verdicts[0])


@app.get("/api/verdicts/{user_id}")
def api_verdict_by_user(user_id: str) -> dict[str, Any]:
    verdict = _latest_verdict_for_user(user_id)
    if verdict is None:
        return api_verdict_current()
    return _normalize_verdict_payload(verdict)


@app.post("/api/behavioral")
def api_behavioral_ingest(request: BehavioralIngestRequest) -> dict[str, Any]:
    with portal_state_lock:
        events = portal_behavioral_events.setdefault(request.session_id, [])
        events.extend(request.events)
        if len(events) > 500:
            portal_behavioral_events[request.session_id] = events[-500:]
    return {"status": "received", "count": len(request.events)}


@app.post("/api/bank/honeypot-hit")
def api_honeypot_hit(request: SecurityEventRequest) -> dict[str, Any]:
    with portal_state_lock:
        flags = portal_security_flags.setdefault(request.user_id, set())
        flags.add("honeypot")
    return {"status": "flagged"}


@app.post("/api/bank/web-attack-detected")
def api_web_attack_detected(request: SecurityEventRequest) -> dict[str, Any]:
    with portal_state_lock:
        flags = portal_security_flags.setdefault(request.user_id, set())
        flags.add("web_attack")
    return {"status": "blocked"}


@app.post("/api/bank/login")
def api_bank_login(request: BankLoginRequest) -> dict[str, Any]:
    user_id = request.email or "anonymous"
    risk = _calculate_portal_risk(user_id=user_id, session_id=request.session_id, payload_text=request.email)
    verdict = _analyze_portal_action(
        user_id=user_id,
        source_ip="portal-login",
        risk=risk,
        session_id=request.session_id,
    )
    return {
        "success": True,
        "user_id": user_id,
        "session_id": verdict.get("sessionId"),
        "verdict": verdict.get("verdict"),
        "confidence": verdict.get("confidence"),
    }


@app.post("/api/bank/transfer")
def api_bank_transfer(request: BankTransferRequest) -> dict[str, Any]:
    payload_text = f"{request.memo} {request.recipient}"
    risk = _calculate_portal_risk(
        user_id=request.user_id,
        session_id=request.session_id,
        payload_text=payload_text,
    )
    if request.amount >= 10000:
        risk = min(0.99, risk + 0.2)

    verdict = _analyze_portal_action(
        user_id=request.user_id,
        source_ip="portal-transfer",
        risk=risk,
        session_id=request.session_id,
    )
    return {
        "status": "accepted",
        "user_id": request.user_id,
        "session_id": verdict.get("sessionId"),
        "verdict": verdict.get("verdict"),
        "confidence": verdict.get("confidence"),
    }


@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    await websocket.accept()
    seen_ids: set[str] = set()
    try:
        bootstrap = [_normalize_alert(item) for item in runtime.latest_alerts(limit=10)]
        if bootstrap:
            for alert in bootstrap:
                seen_ids.add(str(alert.get("id")))
            await websocket.send_json(bootstrap)

        while True:
            await asyncio.sleep(1.0)
            latest = [_normalize_alert(item) for item in runtime.latest_alerts(limit=20)]
            fresh = [item for item in latest if str(item.get("id")) not in seen_ids]
            if fresh:
                for item in fresh:
                    seen_ids.add(str(item.get("id")))
                    await websocket.send_json(item)
            if websocket.client_state.name != "CONNECTED":
                break
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
