from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, status
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
from pydantic import BaseModel, Field
import asyncio
from fastapi.middleware.cors import CORSMiddleware

try:
    import psycopg2
    from psycopg2.extras import Json, RealDictCursor
except ImportError:  # pragma: no cover - keeps importable in lightweight environments
    psycopg2 = None
    RealDictCursor = None

    def Json(value: Any) -> Any:  # type: ignore[misc]
        return value

REPO_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("BEHAVIOR_PROFILE_DIR", str(REPO_ROOT / "data" / "behavioral_profiles"))

from core.behavioral.signals import extract_session_vector
from core.engine import DecisionEngine, ThreatVerdict


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [inference] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def _resolve_model_dir() -> Path:
    configured = os.getenv("MODEL_PATH")
    if configured:
        return Path(configured).expanduser()
    container_models = Path("/models")
    if os.name != "nt" and container_models.exists():
        return container_models
    return REPO_ROOT / "models"


KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
DATABASE_URL = os.getenv("DATABASE_URL", "")
INPUT_TOPIC = os.getenv("INFERENCE_INPUT_TOPIC", "extracted-features")
VERDICTS_TOPIC = os.getenv("VERDICTS_TOPIC", "verdicts")
ALERTS_TOPIC = os.getenv("ALERTS_TOPIC", "alerts")
GROUP_ID = os.getenv("INFERENCE_GROUP_ID", "inference-service")
MODEL_DIR = _resolve_model_dir()
MODEL_VERSION_PATH = Path(os.getenv("MODEL_VERSION_FILE", str(MODEL_DIR / "model_version.json")))
MODEL_POLL_SECONDS = float(os.getenv("MODEL_POLL_SECONDS", "60"))
CONSUMER_RETRY_SECONDS = float(os.getenv("CONSUMER_RETRY_SECONDS", "5"))
LATEST_VERDICTS_LIMIT = int(os.getenv("LATEST_VERDICTS_LIMIT", "200"))
HOST = os.getenv("INFERENCE_HOST", "0.0.0.0")
PORT = int(os.getenv("INFERENCE_PORT", "8000"))
API_KEY = os.getenv("API_KEY", "")
SANDBOX_BASE_URL = os.getenv("SANDBOX_BASE_URL", "").rstrip("/")
SANDBOX_TIMEOUT_SECONDS = int(os.getenv("SANDBOX_TIMEOUT_SEC", "300"))
PORTAL_SESSION_TTL_SECONDS = int(os.getenv("PORTAL_SESSION_TTL_SECONDS", "1800"))
APP_STARTED_AT = time.time()

SQLI_PATTERN = re.compile(r"(union\s+select|or\s+1\s*=\s*1|--|/\*|drop\s+table|insert\s+into)", re.IGNORECASE)
BEHAVIOR_DIMENSIONS = [
    "Velocity",
    "Session Drift",
    "Bot Pressure",
    "Credential Risk",
    "Geo Variance",
    "Device Novelty",
    "Typing Rhythm",
    "Mouse Entropy",
    "Route Depth",
    "Auth Friction",
    "Token Churn",
    "Transfer Heat",
    "Time Deviation",
    "Privilege Lift",
    "IP Reputation",
    "Cashout Risk",
    "Login Burst",
    "Browser Trust",
    "Peer Similarity",
    "Recovery Abuse",
]

BANK_ACCOUNTS = {
    "normal1@novatrust.com": {
        "email": "normal1@novatrust.com",
        "password": "password123",
        "user_id": "alice",
        "display_name": "Alice Johnson",
        "account_masked": "****4521",
        "balance": 12450.00,
    },
    "normal2@novatrust.com": {
        "email": "normal2@novatrust.com",
        "password": "secure456",
        "user_id": "bob",
        "display_name": "Bob Carter",
        "account_masked": "****8314",
        "balance": 9820.42,
    },
    "admin@novatrust.com": {
        "email": "admin@novatrust.com",
        "password": "Admin@2024!",
        "user_id": "carol",
        "display_name": "Carol Admin",
        "account_masked": "****1108",
        "balance": 50124.77,
    },
}


class SessionAnalyzeRequest(BaseModel):
    session_id: str
    user_id: str = "unknown-user"
    source_ip: str = "unknown"
    flow_features: list[float] = Field(..., min_length=80, max_length=80)
    raw_flow_features: list[float] | None = Field(default=None, min_length=80, max_length=80)
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


class BehavioralIngestRequest(BaseModel):
    user_id: str = "anonymous"
    session_id: str | None = None
    events: list[dict[str, Any]] = Field(default_factory=list)
    source_ip: str = "unknown"
    page: str | None = None


class BankLoginRequest(BaseModel):
    email: str
    password: str
    session_id: str | None = None
    source_ip: str = "unknown"


class BankTransferRequest(BaseModel):
    user_id: str = "unknown-user"
    session_id: str | None = None
    source_ip: str = "unknown"
    destination: str
    amount: float = Field(..., ge=0)
    memo: str | None = None
    confirm_routing_number: str | None = None


class HoneypotHitRequest(BaseModel):
    source: str = "unknown"
    user_id: str = "anonymous"
    session_id: str | None = None
    source_ip: str = "unknown"


class WebAttackDetectedRequest(BaseModel):
    attack_type: str = "WEB_ATTACK"
    payload: str = ""
    user_id: str = "anonymous"
    session_id: str | None = None
    source_ip: str = "unknown"


@dataclass
class PortalSession:
    session_id: str
    user_key: str
    source_ip: str
    created_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    behavioral_events: list[dict[str, Any]] = field(default_factory=list)
    behavioral_vector: list[float] = field(default_factory=lambda: [0.0] * 20)
    known_aliases: set[str] = field(default_factory=set)
    login_passwords: set[str] = field(default_factory=set)
    login_attempts: int = 0
    failed_logins: int = 0
    honeypot_hits: list[dict[str, Any]] = field(default_factory=list)
    web_attacks: list[dict[str, Any]] = field(default_factory=list)
    transfer_attempts: list[dict[str, Any]] = field(default_factory=list)
    latest_verdict: dict[str, Any] | None = None
    sandbox_token: str | None = None
    sandbox_mode: str | None = None

    def touch(self) -> None:
        self.last_seen = time.time()


class PortalState:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, PortalSession] = {}
        self._alias_to_session: dict[str, str] = {}
        self._user_current_session: dict[str, str] = {}
        self._current_session_id: str | None = None

    def cleanup(self) -> None:
        cutoff = time.time() - PORTAL_SESSION_TTL_SECONDS
        with self._lock:
            expired = [session_id for session_id, session in self._sessions.items() if session.last_seen < cutoff]
            for session_id in expired:
                session = self._sessions.pop(session_id, None)
                if session is None:
                    continue
                for alias in session.known_aliases:
                    if self._alias_to_session.get(alias) == session_id:
                        self._alias_to_session.pop(alias, None)
                for alias in list(self._user_current_session):
                    if self._user_current_session.get(alias) == session_id:
                        self._user_current_session.pop(alias, None)
                if self._current_session_id == session_id:
                    self._current_session_id = None

    def _normalize_alias(self, value: str | None) -> str:
        return (value or "anonymous").strip().lower() or "anonymous"

    def _ensure_session(self, user_key: str, session_id: str | None = None, source_ip: str = "unknown") -> PortalSession:
        self.cleanup()
        normalized_key = self._normalize_alias(user_key)
        resolved_session_id = session_id or self._alias_to_session.get(normalized_key) or f"portal-{uuid.uuid4().hex}"
        session = self._sessions.get(resolved_session_id)
        if session is None:
            session = PortalSession(session_id=resolved_session_id, user_key=normalized_key, source_ip=source_ip)
            self._sessions[resolved_session_id] = session
        session.source_ip = source_ip or session.source_ip
        session.known_aliases.add(normalized_key)
        self._alias_to_session[normalized_key] = resolved_session_id
        self._user_current_session[normalized_key] = resolved_session_id
        self._current_session_id = resolved_session_id
        session.touch()
        return session

    def bind_aliases(self, canonical_user_id: str, session_id: str | None, aliases: list[str]) -> PortalSession:
        with self._lock:
            base_alias = aliases[0] if aliases else canonical_user_id
            session = self._ensure_session(base_alias, session_id=session_id)
            for alias in aliases + [canonical_user_id]:
                normalized = self._normalize_alias(alias)
                session.known_aliases.add(normalized)
                self._alias_to_session[normalized] = session.session_id
                self._user_current_session[normalized] = session.session_id
            session.touch()
            return session

    def record_behavioral(self, request: BehavioralIngestRequest) -> PortalSession:
        with self._lock:
            session = self._ensure_session(request.user_id, request.session_id, request.source_ip)
            session.behavioral_events.extend(request.events)
            if request.page:
                session.behavioral_events.append(
                    {"type": "pagevisit", "timestamp": time.time(), "page": request.page}
                )
            session.behavioral_events = session.behavioral_events[-500:]
            session.behavioral_vector = extract_session_vector(session.behavioral_events).astype(float).tolist()
            return session

    def record_login_attempt(
        self,
        identifier: str,
        password: str,
        session_id: str | None,
        source_ip: str,
        authenticated: bool,
    ) -> PortalSession:
        with self._lock:
            session = self._ensure_session(identifier, session_id, source_ip)
            session.login_attempts += 1
            if password:
                session.login_passwords.add(password)
            if not authenticated:
                session.failed_logins += 1
            return session

    def record_honeypot(
        self,
        identifier: str,
        session_id: str | None,
        source_ip: str,
        source: str,
    ) -> PortalSession:
        with self._lock:
            session = self._ensure_session(identifier, session_id, source_ip)
            session.honeypot_hits.append({"source": source, "timestamp": time.time()})
            return session

    def record_web_attack(
        self,
        identifier: str,
        session_id: str | None,
        source_ip: str,
        attack_type: str,
        payload: str,
    ) -> PortalSession:
        with self._lock:
            session = self._ensure_session(identifier, session_id, source_ip)
            session.web_attacks.append({"attack_type": attack_type, "payload": payload, "timestamp": time.time()})
            return session

    def record_transfer(
        self,
        identifier: str,
        session_id: str | None,
        source_ip: str,
        amount: float,
        destination: str,
        memo: str | None,
    ) -> PortalSession:
        with self._lock:
            session = self._ensure_session(identifier, session_id, source_ip)
            session.transfer_attempts.append(
                {
                    "amount": amount,
                    "destination": destination,
                    "memo": memo,
                    "timestamp": time.time(),
                }
            )
            session.transfer_attempts = session.transfer_attempts[-25:]
            return session

    def set_verdict(self, session_id: str, verdict: dict[str, Any]) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            session.latest_verdict = verdict
            self._current_session_id = session_id
            session.touch()

    def attach_sandbox(self, session_id: str, sandbox_token: str, mode: str) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            session.sandbox_token = sandbox_token
            session.sandbox_mode = mode
            session.touch()

    def get_session(self, identifier: str | None = None, session_id: str | None = None) -> PortalSession | None:
        with self._lock:
            self.cleanup()
            resolved_session_id = session_id
            if resolved_session_id is None and identifier is not None:
                normalized = self._normalize_alias(identifier)
                resolved_session_id = self._alias_to_session.get(normalized) or self._user_current_session.get(normalized)
            if resolved_session_id is None:
                return None
            return self._sessions.get(resolved_session_id)

    def current_verdict(self) -> dict[str, Any] | None:
        with self._lock:
            if self._current_session_id is None:
                return None
            session = self._sessions.get(self._current_session_id)
            return None if session is None else session.latest_verdict

    def replay_stub(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            actions: list[dict[str, Any]] = []
            for hit in session.honeypot_hits:
                actions.append(
                    {
                        "path": "/api/bank/honeypot-hit",
                        "method": "POST",
                        "timestamp": hit["timestamp"],
                        "body": hit,
                    }
                )
            for attack in session.web_attacks:
                actions.append(
                    {
                        "path": "/api/bank/web-attack-detected",
                        "method": "POST",
                        "timestamp": attack["timestamp"],
                        "body": attack,
                    }
                )
            for transfer in session.transfer_attempts:
                actions.append(
                    {
                        "path": "/api/bank/transfer",
                        "method": "POST",
                        "timestamp": transfer["timestamp"],
                        "body": transfer,
                    }
                )
            return sorted(actions, key=lambda item: float(item["timestamp"]))


class SandboxGateway:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _request(self, path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.base_url:
            raise RuntimeError("SANDBOX_BASE_URL is not configured.")
        body = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        request = urllib_request.Request(f"{self.base_url}{path}", method=method, data=body, headers=headers)
        with urllib_request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def create_session(self, session_id: str, user_id: str, source_ip: str) -> dict[str, Any]:
        try:
            return self._request(
                "/sessions",
                method="POST",
                payload={"session_id": session_id, "user_id": user_id, "source_ip": source_ip},
            )
        except (RuntimeError, urllib_error.URLError, urllib_error.HTTPError, TimeoutError) as exc:
            raise RuntimeError(f"Sandbox session creation failed: {exc}") from exc

    def replay(self, sandbox_token: str) -> dict[str, Any]:
        try:
            return self._request(f"/sessions/{sandbox_token}/replay")
        except (RuntimeError, urllib_error.URLError, urllib_error.HTTPError, TimeoutError) as exc:
            raise RuntimeError(f"Sandbox replay lookup failed: {exc}") from exc

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

    def latest_verdicts_for_user(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        conn = self._connect()
        if conn is None:
            return []
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT session_id, user_id, source_ip, verdict, confidence, snn_score,
                               lnn_class, xgb_class, behavioral_delta, model_version, timestamp,
                               created_at
                        FROM verdicts
                        WHERE user_id = %s
                        ORDER BY created_at DESC, id DESC
                        LIMIT %s
                        """,
                        (user_id, limit),
                    )
                    rows = cur.fetchall() or []
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def latest_alert_rows(self, limit: int = 50) -> list[dict[str, Any]]:
        conn = self._connect()
        if conn is None:
            return []
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT session_id, user_id, source_ip, verdict, confidence, created_at
                        FROM alerts
                        ORDER BY created_at DESC, id DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                    rows = cur.fetchall() or []
            return [dict(row) for row in rows]
        finally:
            conn.close()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()
portal_state = PortalState()
sandbox_gateway = SandboxGateway(SANDBOX_BASE_URL) if SANDBOX_BASE_URL else None


def _account_for_user(user_id: str) -> dict[str, Any] | None:
    normalized = user_id.strip().lower()
    for account in BANK_ACCOUNTS.values():
        if normalized in {account["email"].lower(), account["user_id"].lower()}:
            return account
    return None


def _display_name_for_user(user_id: str) -> str:
    account = _account_for_user(user_id)
    return account["display_name"] if account else user_id.replace("_", " ").title()


def _severity_for_verdict(verdict: str, confidence: float) -> str:
    if verdict == "HACKER" or confidence >= 0.8:
        return "high"
    if verdict == "FORGETFUL_USER" or confidence >= 0.5:
        return "medium"
    return "low"


def _message_for_verdict(verdict: dict[str, Any]) -> str:
    if verdict.get("verdict") == "HACKER":
        return f"{verdict.get('xgb_class', 'Threat')} indicators triggered a sandbox-worthy decision."
    if verdict.get("verdict") == "FORGETFUL_USER":
        return "Behavior drift exceeded the normal-user baseline but stayed below hard attacker thresholds."
    return "Session aligned with the stored user profile and passed ensemble checks."


def _dimensions_from_profile(user_id: str) -> list[dict[str, Any]]:
    profile = runtime.engine.behavioral_profiler.load_profile(user_id) if "runtime" in globals() else None
    vector = profile.profile_vector.astype(float).tolist() if profile is not None else [0.0] * len(BEHAVIOR_DIMENSIONS)
    return [
        {"subject": label, "value": round(float(vector[index]) * 100, 2)}
        for index, label in enumerate(BEHAVIOR_DIMENSIONS)
    ]


def _recent_verdicts_for_user(user_id: str) -> list[dict[str, Any]]:
    verdicts = runtime.find_verdicts_for_user(user_id, limit=10) if "runtime" in globals() else []
    return [
        {
            "id": f"{item.get('session_id', 'session')}-{index}",
            "verdict": item.get("verdict", "INCONCLUSIVE"),
            "score": float(item.get("confidence", 0.0)),
            "timestamp": item.get("created_at") or item.get("timestamp") or time.time(),
        }
        for index, item in enumerate(verdicts)
    ]


def _format_alert_payload(verdict: dict[str, Any]) -> dict[str, Any]:
    user_id = str(verdict.get("user_id", "unknown-user"))
    return {
        "id": verdict.get("session_id", f"alert-{uuid.uuid4().hex[:8]}"),
        "severity": _severity_for_verdict(str(verdict.get("verdict", "")), float(verdict.get("confidence", 0.0))),
        "verdict": verdict.get("verdict", "INCONCLUSIVE"),
        "message": _message_for_verdict(verdict),
        "timestamp": verdict.get("created_at") or verdict.get("timestamp") or time.time(),
        "sourceIp": verdict.get("source_ip", "unknown"),
        "userId": user_id,
        "userName": _display_name_for_user(user_id),
        "locationLabel": verdict.get("location_label", "Unknown location"),
        "score": float(verdict.get("confidence", 0.0)),
        "dimensions": _dimensions_from_profile(user_id),
        "recentVerdicts": _recent_verdicts_for_user(user_id),
        "modelVersion": verdict.get("model_version", runtime.engine.current_model_version if "runtime" in globals() else "0.0.0"),
    }


def _camelize_verdict(verdict: dict[str, Any]) -> dict[str, Any]:
    session = portal_state.get_session(session_id=str(verdict.get("session_id"))) if verdict.get("session_id") else None
    return {
        **verdict,
        "sessionId": verdict.get("session_id"),
        "userId": verdict.get("user_id"),
        "sourceIp": verdict.get("source_ip"),
        "snnScore": float(verdict.get("snn_score", 0.0)),
        "lnnClass": verdict.get("lnn_class"),
        "xgbClass": verdict.get("xgb_class"),
        "behavioralDelta": float(verdict.get("behavioral_delta", 0.0)),
        "modelVersion": verdict.get("model_version"),
        "sandbox": (
            {
                "active": bool(session and session.sandbox_token),
                "mode": session.sandbox_mode if session else None,
                "sandboxToken": session.sandbox_token if session else None,
                "sandboxPath": "/security-alert" if session and session.sandbox_token else None,
            }
            if session is not None
            else None
        ),
    }


def _build_flow_features(feature_names: list[str], signals: dict[str, float]) -> list[float]:
    vector = [0.05] * len(feature_names)
    index_lookup = {name: index for index, name in enumerate(feature_names)}
    for name, value in signals.items():
        index = index_lookup.get(name)
        if index is None:
            continue
        vector[index] = float(value)
    return vector[:80] + ([0.0] * max(0, 80 - len(vector)))


def _build_portal_session_data(session: PortalSession, user_id: str) -> dict[str, Any]:
    feature_signals = {
        "packet_rate": min(15000.0, 250.0 * max(session.failed_logins, 1)),
        "ack_ratio": 0.05 * min(session.login_attempts, 10),
        "rst_flag_count": float(len(session.web_attacks)),
    }
    if session.transfer_attempts:
        latest_transfer = session.transfer_attempts[-1]
        feature_signals["packet_rate"] = max(feature_signals["packet_rate"], float(latest_transfer["amount"]) / 3.0)
    return {
        "session_id": session.session_id,
        "user_id": user_id,
        "source_ip": session.source_ip,
        "flow_features": _build_flow_features(runtime.engine.feature_names, feature_signals),
        "behavioral_events": list(session.behavioral_events),
        "behavioral_vector": list(session.behavioral_vector),
        "login_attempts": session.login_attempts,
        "all_different_passwords": len(session.login_passwords) > 1,
        "sql_injection_detected": any(SQLI_PATTERN.search(attack.get("payload", "")) for attack in session.web_attacks),
        "timestamp": time.time(),
    }


def _promote_verdict(
    verdict: ThreatVerdict,
    *,
    xgb_class: str,
    confidence: float,
    reason: str,
) -> ThreatVerdict:
    verdict.xgb_class = xgb_class
    verdict.confidence = max(float(verdict.confidence), confidence)
    verdict.snn_score = max(float(verdict.snn_score), min(confidence, 0.99))
    verdict.behavioral_delta = max(float(verdict.behavioral_delta), min(confidence, 0.99))
    verdict.lnn_class = xgb_class if verdict.lnn_class in {"BENIGN", "INCONCLUSIVE"} else verdict.lnn_class
    verdict.verdict = "HACKER" if verdict.confidence >= 0.8 else "FORGETFUL_USER"
    verdict.features_dict["_api_override"] = reason
    return verdict


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
        self._loop = asyncio.get_event_loop()

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
            "raw_flow_features": payload.get("raw_features"),
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
            alert_payload = {
                "session_id": verdict.session_id,
                "user_id": verdict.user_id,
                "source_ip": verdict.source_ip,
                "confidence": verdict.confidence,
                "verdict": verdict.verdict,
                "timestamp": verdict.timestamp,
                "model_version": verdict.model_version,
                "xgb_class": verdict.xgb_class,
            }
            self._latest_alerts.appendleft(alert_payload)
            # Broadcast to UI
            try:
                if self._loop and self._loop.is_running():
                    self._loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(manager.broadcast(_format_alert_payload(alert_payload)))
                    )
            except Exception as e:
                log.warning("WebSocket broadcast failed: %s", e)
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

    def find_verdicts_for_user(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        database_rows = self.repository.latest_verdicts_for_user(user_id, limit=limit)
        if database_rows:
            return database_rows
        with self._lock:
            return [item for item in self._latest_verdicts if item.get("user_id") == user_id][:limit]

    def latest_verdict_for_user(self, user_id: str) -> dict[str, Any] | None:
        verdicts = self.find_verdicts_for_user(user_id, limit=1)
        return verdicts[0] if verdicts else None

    def list_alert_payloads(self, limit: int = 50) -> list[dict[str, Any]]:
        database_rows = self.repository.latest_alert_rows(limit=limit)
        if database_rows:
            return database_rows
        return self.latest_alerts(limit)


runtime = InferenceRuntime()


@asynccontextmanager
async def lifespan(_: FastAPI):
    runtime.start()
    try:
        yield
    finally:
        runtime.stop()


app = FastAPI(title="NeuroShield Inference Service", version="0.9.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. In production, restrict to dashboard URL.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _api_key_exempt(path: str) -> bool:
    return path in {"/", "/health", "/openapi.json"} or path.startswith("/docs") or path.startswith("/redoc")


def _current_model_payload() -> dict[str, Any]:
    payload = runtime.engine._read_model_version()
    validation = payload.get("validation_f1", {}) or {}
    version = payload.get("version", runtime.engine.current_model_version)
    return {
        "version": version,
        "versions": [
            {"label": "Primary", "value": str(version)},
            {"label": "SNN", "value": str(payload.get("snn") or "not-loaded")},
            {"label": "LNN", "value": str(payload.get("lnn") or "not-loaded")},
            {"label": "XGBoost", "value": str(payload.get("xgb") or "not-loaded")},
        ],
        "validationF1": [
            {"label": "SNN", "value": float(validation.get("snn") or 0.0)},
            {"label": "LNN", "value": float(validation.get("lnn") or 0.0)},
            {"label": "XGBoost", "value": float(validation.get("xgb") or 0.0)},
        ],
        "lastRetrainedAt": payload.get("timestamp"),
        "activeModels": ["SNN", "LNN", "XGBoost"],
    }


def _session_snapshot(identifier: str, session_id: str | None, source_ip: str) -> PortalSession:
    session = portal_state.get_session(identifier=identifier, session_id=session_id)
    if session is not None:
        return session
    return portal_state.bind_aliases(identifier, session_id, [identifier])


def _activate_sandbox(response: Response, session: PortalSession, user_id: str, source_ip: str) -> dict[str, Any]:
    mode = "placeholder"
    sandbox_token = f"sbx-placeholder-{uuid.uuid4().hex[:12]}"
    if sandbox_gateway is not None:
        try:
            payload = sandbox_gateway.create_session(session.session_id, user_id, source_ip)
            sandbox_token = str(payload.get("sandbox_token", sandbox_token))
            mode = "live"
        except RuntimeError as exc:
            log.warning("%s", exc)
    portal_state.attach_sandbox(session.session_id, sandbox_token, mode)
    response.set_cookie(
        "sandbox_token",
        sandbox_token,
        httponly=True,
        samesite="lax",
        max_age=SANDBOX_TIMEOUT_SECONDS,
    )
    response.headers["X-Sandbox-Token"] = sandbox_token
    return {
        "active": True,
        "mode": mode,
        "sandboxToken": sandbox_token,
        "sandboxPath": "/security-alert",
    }


def _run_portal_analysis(session: PortalSession, user_id: str) -> ThreatVerdict:
    verdict = runtime.engine.analyze_session(_build_portal_session_data(session, user_id))
    if session.honeypot_hits:
        verdict = _promote_verdict(verdict, xgb_class="BOT", confidence=0.99, reason="HONEYPOT_TRIGGER")
    elif session.web_attacks:
        verdict = _promote_verdict(verdict, xgb_class="WEB_ATTACK", confidence=0.97, reason="WEB_ATTACK_REPORT")
    elif session.failed_logins >= 5 and len(session.login_passwords) > 1:
        verdict = _promote_verdict(verdict, xgb_class="BRUTE_FORCE", confidence=0.93, reason="BRUTE_FORCE_PATTERN")
    elif session.transfer_attempts and float(session.transfer_attempts[-1]["amount"]) >= 10000:
        verdict = _promote_verdict(verdict, xgb_class="OTHER", confidence=0.65, reason="TRANSFER_HEAT")

    final_verdict = runtime._handle_verdict(verdict)
    portal_state.set_verdict(session.session_id, final_verdict.to_dict())
    return final_verdict


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if API_KEY and not _api_key_exempt(request.url.path):
        if request.headers.get("x-api-key") != API_KEY:
            return Response(status_code=status.HTTP_401_UNAUTHORIZED, content="Missing or invalid X-API-Key.")
    return await call_next(request)


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "neuroshield-inference",
        "phase": 9,
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


# --- Analyst API (Frontend Compatibility) ---

@app.get("/api/stats")
def get_api_stats() -> dict[str, Any]:
    with runtime._lock:
        hacker_count = sum(1 for v in runtime._latest_verdicts if v.get("verdict") == "HACKER")
        legit_count = sum(1 for v in runtime._latest_verdicts if v.get("verdict") == "LEGITIMATE")
        avg_risk = sum(v.get("confidence", 0) for v in runtime._latest_verdicts) / max(len(runtime._latest_verdicts), 1)

    return {
        "totalTransactions": runtime._processed_messages,
        "hackerDetections": hacker_count,
        "avgRiskScore": round(avg_risk * 100, 2),
        "liveAlerts": len(runtime._latest_alerts),
        "legitimateCount": legit_count,
        "uptimeSeconds": int(time.time() - APP_STARTED_AT),
    }


@app.get("/api/model/version")
def get_api_model_version() -> dict[str, Any]:
    return _current_model_payload()


@app.get("/api/alerts")
def get_api_alerts() -> list[dict[str, Any]]:
    return [_format_alert_payload(item) for item in runtime.list_alert_payloads(50)]


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send current backlog first
        backlog = [_format_alert_payload(item) for item in runtime.list_alert_payloads(10)]
        if backlog:
            await websocket.send_json(backlog)
        
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        log.error("WebSocket error: %s", e)
        manager.disconnect(websocket)


@app.post("/analyze")
@app.post("/api/analyze")
def analyze(request: SessionAnalyzeRequest) -> dict[str, Any]:
    verdict = runtime.analyze_manual(request.model_dump())
    return verdict.to_dict()


@app.post("/behavioral/vectorize")
def behavioral_vectorize(request: BehavioralVectorRequest) -> dict[str, Any]:
    return {"vector": extract_session_vector(request.events).astype(float).tolist()}


@app.post("/api/behavioral")
def behavioral_ingest(request: BehavioralIngestRequest) -> dict[str, Any]:
    session = portal_state.record_behavioral(request)
    return {
        "status": "captured",
        "userId": request.user_id,
        "sessionId": session.session_id,
        "eventCount": len(session.behavioral_events),
        "vector": session.behavioral_vector,
    }


@app.get("/api/verdicts/current")
@app.get("/api/verdicts/current-session")
def get_current_portal_verdict() -> dict[str, Any]:
    current = portal_state.current_verdict()
    if current is None:
        latest = runtime.latest_verdicts(1)
        if not latest:
            return {
                "sessionId": None,
                "verdict": "INCONCLUSIVE",
                "confidence": 0.0,
                "snnScore": 0.0,
                "lnnClass": "INCONCLUSIVE",
                "xgbClass": "INCONCLUSIVE",
                "behavioralDelta": 0.0,
            }
        current = latest[0]
    return _camelize_verdict(current)


@app.get("/api/verdicts/{user_id}")
def get_user_verdict(user_id: str) -> dict[str, Any]:
    verdict = runtime.latest_verdict_for_user(user_id)
    if verdict is None:
        raise HTTPException(status_code=404, detail="No verdicts found for user.")
    recent = runtime.find_verdicts_for_user(user_id, limit=10)
    return {
        **_camelize_verdict(verdict),
        "recentVerdicts": _recent_verdicts_for_user(user_id),
        "history": [_camelize_verdict(item) for item in recent],
    }


@app.post("/api/bank/login")
def bank_login(request: BankLoginRequest, response: Response) -> dict[str, Any]:
    account = BANK_ACCOUNTS.get(request.email.strip().lower())
    authenticated = bool(account and account["password"] == request.password)
    session = portal_state.record_login_attempt(request.email, request.password, request.session_id, request.source_ip, authenticated)

    user_id = account["user_id"] if account else request.email.strip().lower() or "unknown-user"
    aliases = [request.email, user_id]
    session = portal_state.bind_aliases(user_id, session.session_id, aliases)
    verdict = _run_portal_analysis(session, user_id)

    sandbox = None
    if verdict.verdict == "HACKER":
        sandbox = _activate_sandbox(response, session, user_id, request.source_ip)

    payload = {
        "authenticated": authenticated,
        "user_id": user_id,
        "displayName": _display_name_for_user(user_id),
        "sessionId": session.session_id,
        "verdict": verdict.verdict,
        "confidence": verdict.confidence,
        "sandbox": sandbox,
        "next": "/security-alert" if sandbox else ("/dashboard" if authenticated else "/login"),
    }
    if account:
        payload["account"] = {
            "balance": account["balance"],
            "accountMasked": account["account_masked"],
        }
    if not authenticated:
        payload["error"] = "Invalid credentials."
    return payload


@app.post("/api/bank/transfer")
def bank_transfer(request: BankTransferRequest, response: Response) -> dict[str, Any]:
    session = portal_state.record_transfer(request.user_id, request.session_id, request.source_ip, request.amount, request.destination, request.memo)
    if request.confirm_routing_number:
        session = portal_state.record_honeypot(request.user_id, session.session_id, request.source_ip, "confirm_routing_number")

    if request.memo and SQLI_PATTERN.search(request.memo):
        session = portal_state.record_web_attack(request.user_id, session.session_id, request.source_ip, "SQLI", request.memo)

    verdict = _run_portal_analysis(session, request.user_id)
    sandbox = None
    if verdict.verdict == "HACKER":
        sandbox = _activate_sandbox(response, session, request.user_id, request.source_ip)

    return {
        "status": "sandboxed" if sandbox else "accepted",
        "sessionId": session.session_id,
        "verdict": verdict.verdict,
        "confidence": verdict.confidence,
        "sandbox": sandbox,
        "message": "Transfer pending review" if sandbox else "Transfer authorized",
    }


@app.post("/api/bank/honeypot-hit")
def honeypot_hit(request: HoneypotHitRequest, response: Response) -> dict[str, Any]:
    session = portal_state.record_honeypot(request.user_id, request.session_id, request.source_ip, request.source)
    verdict = _run_portal_analysis(session, request.user_id)
    sandbox = _activate_sandbox(response, session, request.user_id, request.source_ip)
    return {
        "status": "captured",
        "sessionId": session.session_id,
        "verdict": verdict.verdict,
        "sandbox": sandbox,
    }


@app.post("/api/bank/web-attack-detected")
def web_attack_detected(request: WebAttackDetectedRequest, response: Response) -> dict[str, Any]:
    session = portal_state.record_web_attack(request.user_id, request.session_id, request.source_ip, request.attack_type, request.payload)
    verdict = _run_portal_analysis(session, request.user_id)
    sandbox = _activate_sandbox(response, session, request.user_id, request.source_ip)
    return {
        "status": "captured",
        "sessionId": session.session_id,
        "verdict": verdict.verdict,
        "sandbox": sandbox,
    }


@app.get("/api/sandbox/{session_id}/replay")
def get_sandbox_replay(session_id: str) -> dict[str, Any]:
    session = portal_state.get_session(session_id=session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Sandbox session not found.")
    if session.sandbox_token and sandbox_gateway is not None and session.sandbox_mode == "live":
        try:
            return sandbox_gateway.replay(session.sandbox_token)
        except RuntimeError as exc:
            log.warning("%s", exc)
    return {
        "session_id": session_id,
        "sandbox_token": session.sandbox_token,
        "mode": session.sandbox_mode or "placeholder",
        "actions": portal_state.replay_stub(session_id),
    }


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
