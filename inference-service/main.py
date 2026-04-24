from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
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


@asynccontextmanager
async def lifespan(_: FastAPI):
    runtime.start()
    try:
        yield
    finally:
        runtime.stop()


app = FastAPI(title="NeuroShield Inference Service", version="0.8.0", lifespan=lifespan)


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


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
