from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from kafka import KafkaProducer
from pydantic import BaseModel, Field

try:
    import psycopg2
    from psycopg2.extras import Json, RealDictCursor
except ImportError:  # pragma: no cover - import-safe for lightweight environments
    psycopg2 = None
    RealDictCursor = None

    def Json(value: Any) -> Any:  # type: ignore[misc]
        return value


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [sandbox] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


DATABASE_URL = os.getenv("DATABASE_URL", "")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
SANDBOX_TIMEOUT_SEC = int(os.getenv("SANDBOX_TIMEOUT_SEC", "300"))
HOST = os.getenv("SANDBOX_HOST", "0.0.0.0")
PORT = int(os.getenv("SANDBOX_PORT", "8001"))
FEEDBACK_TRIGGER_TOPIC = os.getenv("FEEDBACK_TRIGGER_TOPIC", "feedback-trigger")


class CreateSessionRequest(BaseModel):
    session_id: str
    user_id: str = "unknown-user"
    source_ip: str = "unknown"


class TransferRequest(BaseModel):
    amount: float
    destination: str
    memo: str | None = None
    confirm_routing_number: str | None = None
    flow_features: list[float] | None = Field(default=None, min_length=80, max_length=80)


class SandboxRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self):
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for the sandbox service.")
        if psycopg2 is None or RealDictCursor is None:
            raise RuntimeError("psycopg2 is required to persist sandbox activity.")
        return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)

    def bootstrap(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sandbox_sessions (
                        session_id TEXT PRIMARY KEY,
                        sandbox_token TEXT UNIQUE NOT NULL,
                        user_id TEXT NOT NULL,
                        source_ip TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        ended_at TIMESTAMPTZ NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sandbox_actions (
                        action_id BIGSERIAL PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        sandbox_token TEXT NOT NULL,
                        path TEXT NOT NULL,
                        method TEXT NOT NULL,
                        headers_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                        body JSONB NULL,
                        response_sent JSONB NULL,
                        timestamp DOUBLE PRECISION NOT NULL,
                        port INTEGER NULL,
                        features JSONB NULL,
                        sandbox_ended_at TIMESTAMPTZ NULL,
                        feedback_sent BOOLEAN NOT NULL DEFAULT FALSE,
                        assigned_label TEXT NULL
                    )
                    """
                )

    def create_session(self, session_id: str, user_id: str, source_ip: str) -> dict[str, Any]:
        sandbox_token = f"sbx-{uuid.uuid4().hex}"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sandbox_sessions (session_id, sandbox_token, user_id, source_ip)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (session_id) DO UPDATE
                    SET sandbox_token = EXCLUDED.sandbox_token,
                        user_id = EXCLUDED.user_id,
                        source_ip = EXCLUDED.source_ip,
                        created_at = NOW(),
                        ended_at = NULL
                    RETURNING session_id, sandbox_token, user_id, source_ip, created_at
                    """,
                    (session_id, sandbox_token, user_id, source_ip),
                )
                row = cur.fetchone()
        return dict(row)

    def get_session_by_token(self, sandbox_token: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT session_id, sandbox_token, user_id, source_ip, created_at, ended_at
                    FROM sandbox_sessions
                    WHERE sandbox_token = %s
                    """,
                    (sandbox_token,),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def log_action(
        self,
        sandbox_token: str,
        path: str,
        method: str,
        headers_json: dict[str, Any],
        body: Any,
        response_sent: Any,
    ) -> None:
        session = self.get_session_by_token(sandbox_token)
        if session is None:
            raise HTTPException(status_code=401, detail="Invalid sandbox token")
        port = None
        features = None
        if isinstance(body, dict):
            port_value = body.get("port") or body.get("dst_port")
            if port_value is not None:
                try:
                    port = int(port_value)
                except (TypeError, ValueError):
                    port = None
            feature_candidate = body.get("flow_features") or body.get("features")
            if isinstance(feature_candidate, list):
                features = feature_candidate[:80]
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sandbox_actions (
                        session_id,
                        sandbox_token,
                        path,
                        method,
                        headers_json,
                        body,
                        response_sent,
                        timestamp,
                        port,
                        features,
                        sandbox_ended_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
                    """,
                    (
                        session["session_id"],
                        sandbox_token,
                        path,
                        method,
                        Json(headers_json),
                        Json(body) if body is not None else None,
                        Json(response_sent) if response_sent is not None else None,
                        time.time(),
                        port,
                        Json(features) if features is not None else None,
                    ),
                )

    def terminate_session(self, sandbox_token: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE sandbox_sessions
                    SET ended_at = NOW()
                    WHERE sandbox_token = %s AND ended_at IS NULL
                    RETURNING session_id, sandbox_token, user_id, source_ip, ended_at
                    """,
                    (sandbox_token,),
                )
                session = cur.fetchone()
                if session is None:
                    return None
                cur.execute(
                    """
                    UPDATE sandbox_actions
                    SET sandbox_ended_at = NOW()
                    WHERE sandbox_token = %s
                      AND sandbox_ended_at IS NULL
                    """,
                    (sandbox_token,),
                )
        return dict(session)

    def expired_tokens(self, timeout_seconds: int) -> list[str]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT sandbox_token
                    FROM sandbox_sessions
                    WHERE ended_at IS NULL
                      AND created_at < NOW() - (%s * INTERVAL '1 second')
                    """,
                    (timeout_seconds,),
                )
                rows = cur.fetchall()
        return [str(row["sandbox_token"]) for row in rows]


class SandboxManager:
    def __init__(self, repository: SandboxRepository) -> None:
        self.repository = repository
        self._producer: KafkaProducer | None = None

    def start(self) -> None:
        self.repository.bootstrap()
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
                acks="all",
                retries=3,
            )
        except Exception as exc:
            self._producer = None
            log.warning("Kafka producer unavailable for feedback-trigger publishing: %s", exc)

    def stop(self) -> None:
        if self._producer is not None:
            self._producer.close(timeout=3)
            self._producer = None

    def create_session(self, payload: CreateSessionRequest) -> dict[str, Any]:
        return self.repository.create_session(payload.session_id, payload.user_id, payload.source_ip)

    def log_action(self, sandbox_token: str, request_data: dict[str, Any], response_data: dict[str, Any]) -> None:
        self.repository.log_action(
            sandbox_token=sandbox_token,
            path=str(request_data.get("path") or "/"),
            method=str(request_data.get("method") or "GET"),
            headers_json=dict(request_data.get("headers_json") or {}),
            body=request_data.get("body"),
            response_sent=response_data,
        )

    def terminate_session(self, sandbox_token: str) -> dict[str, Any] | None:
        session = self.repository.terminate_session(sandbox_token)
        if session and self._producer is not None:
            self._producer.send(
                FEEDBACK_TRIGGER_TOPIC,
                {
                    "session_id": session["session_id"],
                    "sandbox_token": session["sandbox_token"],
                    "ended_at": str(session["ended_at"]),
                },
            )
            self._producer.flush(timeout=3)
        return session

    def expire_sessions(self) -> int:
        expired = self.repository.expired_tokens(SANDBOX_TIMEOUT_SEC)
        for token in expired:
            self.terminate_session(token)
        return len(expired)


repository = SandboxRepository(DATABASE_URL)
manager = SandboxManager(repository)
_stop_event = threading.Event()
_expiry_thread: threading.Thread | None = None


def _token_from_request(request: Request) -> str | None:
    header_token = request.headers.get("X-Sandbox-Token") or request.headers.get("Authorization")
    if header_token and header_token.lower().startswith("bearer "):
        header_token = header_token[7:]
    return header_token or request.cookies.get("sandbox_token")


def _fake_response_for_path(path: str, method: str) -> dict[str, Any]:
    if path == "/login" and method == "POST":
        return {"status": "ok", "message": "Login successful", "token": "sandbox-session-active"}
    if path == "/dashboard":
        return {
            "accounts": [{"name": "Primary Checking", "balance": 0.0, "status": "frozen"}],
            "banner": "Account review in progress.",
        }
    if path == "/transfer" and method == "POST":
        return {"status": "accepted", "message": "Transfer pending review"}
    if path.startswith("/api/"):
        return {"status": "ok", "data": {"path": path, "message": "Request accepted for review."}}
    return {"status": "ok", "message": "Request received"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _expiry_thread
    manager.start()
    _stop_event.clear()

    def _expiry_loop() -> None:
        while not _stop_event.wait(60):
            try:
                expired = manager.expire_sessions()
                if expired:
                    log.info("Expired %d sandbox sessions.", expired)
            except Exception as exc:
                log.warning("Failed to expire sandbox sessions: %s", exc)

    _expiry_thread = threading.Thread(target=_expiry_loop, name="sandbox-expirer", daemon=True)
    _expiry_thread.start()
    try:
        yield
    finally:
        _stop_event.set()
        if _expiry_thread is not None:
            _expiry_thread.join(timeout=2)
        manager.stop()


app = FastAPI(title="NeuroShield Sandbox", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "timestamp": time.time(), "sandbox_timeout_sec": SANDBOX_TIMEOUT_SEC}


@app.post("/sessions")
def create_session(payload: CreateSessionRequest) -> dict[str, Any]:
    session = manager.create_session(payload)
    return {"session_id": session["session_id"], "sandbox_token": session["sandbox_token"], "status": "created"}


@app.post("/sessions/{sandbox_token}/terminate")
def terminate_session(sandbox_token: str) -> dict[str, Any]:
    session = manager.terminate_session(sandbox_token)
    if session is None:
        raise HTTPException(status_code=404, detail="Sandbox session not found")
    return {"status": "terminated", "session_id": session["session_id"], "sandbox_token": sandbox_token}


async def _handle_sandbox_request(request: Request, body: Any = None) -> dict[str, Any]:
    sandbox_token = _token_from_request(request)
    if not sandbox_token:
        raise HTTPException(status_code=401, detail="Sandbox token required")
    response = _fake_response_for_path(request.url.path, request.method)
    manager.log_action(
        sandbox_token=sandbox_token,
        request_data={
            "path": request.url.path,
            "method": request.method,
            "headers_json": dict(request.headers),
            "body": body,
        },
        response_data=response,
    )
    return response


@app.post("/login")
async def login(request: Request) -> dict[str, Any]:
    body = await request.json()
    return await _handle_sandbox_request(request, body)


@app.get("/dashboard")
async def dashboard(request: Request) -> dict[str, Any]:
    return await _handle_sandbox_request(request, None)


@app.post("/transfer")
async def transfer(request: Request, payload: TransferRequest) -> dict[str, Any]:
    return await _handle_sandbox_request(request, payload.model_dump())


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def sandbox_api(path: str, request: Request) -> dict[str, Any]:
    body = None
    if request.method != "GET":
        try:
            body = await request.json()
        except Exception:
            body = None
    return await _handle_sandbox_request(request, body)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def catch_all(path: str, request: Request) -> dict[str, Any]:
    body = None
    if request.method != "GET":
        try:
            body = await request.json()
        except Exception:
            body = None
    return await _handle_sandbox_request(request, body)


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
