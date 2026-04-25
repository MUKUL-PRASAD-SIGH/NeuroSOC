from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
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

EXEMPT_PATH_PREFIXES = ("/health", "/sessions")
HONEYPOT_PATH_RULES: dict[str, tuple[str, str]] = {
    "/api/admin": ("HONEYPOT_ENDPOINT", "CRITICAL"),
    "/api/debug": ("HONEYPOT_ENDPOINT", "CRITICAL"),
    "/.env": ("HONEYPOT_FILE", "BREACH"),
    "/wp-admin": ("HONEYPOT_ENDPOINT", "WARNING"),
    "/api/internal/user-export": ("HONEYPOT_ENDPOINT", "CRITICAL"),
    "/internal/staff-portal": ("HONEYPOT_LINK", "WARNING"),
}
HONEYPOT_FIELDS = {
    "username_confirm": "CRITICAL",
    "confirm_routing_number": "CRITICAL",
}
CANARY_KEYS = {
    "csrf-token",
    "canary_token",
    "debug_token",
}
SQLI_PATTERN = re.compile(
    r"(union\s+select|select\s+.+\s+from|drop\s+table|insert\s+into|delete\s+from|or\s+1\s*=\s*1|--|/\*)",
    re.IGNORECASE,
)


class CreateSessionRequest(BaseModel):
    session_id: str | None = None
    original_session_id: str | None = None
    user_id: str = "unknown-user"
    source_ip: str = "unknown"

    def resolved_session_id(self) -> str:
        return self.session_id or self.original_session_id or f"session-{uuid.uuid4().hex}"


class TransferRequest(BaseModel):
    amount: float
    destination: str
    memo: str | None = None
    confirm_routing_number: str | None = None
    flow_features: list[float] | None = Field(default=None, min_length=80, max_length=80)


@dataclass
class TriggerEvent:
    trigger_type: str
    severity: str
    details: str


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
                        trigger_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
                        sandbox_ended_at TIMESTAMPTZ NULL,
                        feedback_sent BOOLEAN NOT NULL DEFAULT FALSE,
                        assigned_label TEXT NULL
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS honeypot_hits (
                        hit_id BIGSERIAL PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        sandbox_token TEXT NOT NULL,
                        path TEXT NOT NULL,
                        trigger_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        details JSONB NOT NULL DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_sandbox_actions_session
                    ON sandbox_actions (session_id, timestamp)
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_honeypot_hits_session
                    ON honeypot_hits (session_id, created_at)
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE sandbox_actions
                    ADD COLUMN IF NOT EXISTS trigger_tags JSONB NOT NULL DEFAULT '[]'::jsonb
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
        trigger_tags: list[str],
    ) -> None:
        session = self.get_session_by_token(sandbox_token)
        if session is None or session.get("ended_at") is not None:
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
                        trigger_tags,
                        sandbox_ended_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
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
                        Json(trigger_tags),
                    ),
                )

    def record_honeypot_hit(
        self,
        sandbox_token: str,
        path: str,
        trigger_type: str,
        severity: str,
        details: dict[str, Any],
    ) -> None:
        session = self.get_session_by_token(sandbox_token)
        if session is None:
            return
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO honeypot_hits (
                        session_id,
                        sandbox_token,
                        path,
                        trigger_type,
                        severity,
                        details
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        session["session_id"],
                        sandbox_token,
                        path,
                        trigger_type,
                        severity,
                        Json(details),
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

    def list_session_actions(self, sandbox_token: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT action_id, session_id, sandbox_token, path, method, headers_json, body,
                           response_sent, timestamp, port, features, trigger_tags, sandbox_ended_at,
                           feedback_sent, assigned_label
                    FROM sandbox_actions
                    WHERE sandbox_token = %s
                    ORDER BY timestamp ASC
                    """,
                    (sandbox_token,),
                )
                rows = cur.fetchall()
        return [dict(row) for row in rows]


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
        return self.repository.create_session(payload.resolved_session_id(), payload.user_id, payload.source_ip)

    def log_action(
        self,
        sandbox_token: str,
        request_data: dict[str, Any],
        response_data: dict[str, Any],
        triggers: list[TriggerEvent],
    ) -> None:
        self.repository.log_action(
            sandbox_token=sandbox_token,
            path=str(request_data.get("path") or "/"),
            method=str(request_data.get("method") or "GET"),
            headers_json=dict(request_data.get("headers_json") or {}),
            body=request_data.get("body"),
            response_sent=response_data,
            trigger_tags=[trigger.trigger_type for trigger in triggers],
        )
        for trigger in triggers:
            self.repository.record_honeypot_hit(
                sandbox_token=sandbox_token,
                path=str(request_data.get("path") or "/"),
                trigger_type=trigger.trigger_type,
                severity=trigger.severity,
                details={
                    "details": trigger.details,
                    "method": str(request_data.get("method") or "GET"),
                },
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

    def replay(self, sandbox_token: str) -> list[dict[str, Any]]:
        return self.repository.list_session_actions(sandbox_token)


repository = SandboxRepository(DATABASE_URL)
manager = SandboxManager(repository)
_stop_event = threading.Event()
_expiry_thread: threading.Thread | None = None


def _token_from_request(request: Request) -> str | None:
    header_token = request.headers.get("X-Sandbox-Token") or request.headers.get("Authorization")
    if header_token and header_token.lower().startswith("bearer "):
        header_token = header_token[7:]
    return header_token or request.cookies.get("sandbox_token")


def _prefers_html(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "text/html" in accept or accept in {"", "*/*"}


async def _read_request_body(request: Request) -> Any:
    if request.method in {"GET", "HEAD"}:
        return None
    content_type = request.headers.get("content-type", "")
    try:
        if "application/json" in content_type:
            return await request.json()
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
            return dict(form)
        raw = await request.body()
        if not raw:
            return None
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return None


def _iter_texts(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        texts: list[str] = []
        for item in value.values():
            texts.extend(_iter_texts(item))
        return texts
    if isinstance(value, list):
        texts: list[str] = []
        for item in value:
            texts.extend(_iter_texts(item))
        return texts
    return [str(value)]


def _detect_triggers(path: str, body: Any, headers: dict[str, Any]) -> list[TriggerEvent]:
    triggers: list[TriggerEvent] = []
    lowered_path = path.lower()
    for prefix, (trigger_type, severity) in HONEYPOT_PATH_RULES.items():
        if lowered_path.startswith(prefix):
            triggers.append(
                TriggerEvent(
                    trigger_type=trigger_type,
                    severity=severity,
                    details=f"Honeypot path accessed: {path}",
                )
            )

    if isinstance(body, dict):
        for field, severity in HONEYPOT_FIELDS.items():
            value = body.get(field)
            if value not in (None, "", False):
                triggers.append(
                    TriggerEvent(
                        trigger_type="HONEYPOT_FIELD",
                        severity=severity,
                        details=f"Hidden field '{field}' was populated.",
                    )
                )

    body_text = " ".join(_iter_texts(body))
    if body_text and SQLI_PATTERN.search(body_text):
        triggers.append(
            TriggerEvent(
                trigger_type="SQL_INJECTION",
                severity="CRITICAL",
                details="SQL injection pattern detected in request body.",
            )
        )

    header_and_body_text = " ".join(_iter_texts(headers)) + " " + body_text
    lowered_text = header_and_body_text.lower()
    for token_key in CANARY_KEYS:
        if token_key in lowered_text:
            triggers.append(
                TriggerEvent(
                    trigger_type="CANARY_TOKEN",
                    severity="CRITICAL",
                    details=f"Canary token indicator '{token_key}' observed in request data.",
                )
            )
    return triggers


def _bank_shell(title: str, body_html: str, subtitle: str = "NovaTrust Bank Security Review") -> str:
    return f"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <meta name="csrf-token" content="CANARY_TOKEN" />
    <style>
      body {{
        margin: 0;
        font-family: 'Segoe UI', sans-serif;
        background: linear-gradient(180deg, #f4f7fb 0%, #edf2f7 100%);
        color: #13293d;
      }}
      .shell {{
        max-width: 960px;
        margin: 48px auto;
        padding: 32px;
        background: #ffffff;
        border-radius: 18px;
        box-shadow: 0 24px 80px rgba(19, 41, 61, 0.12);
      }}
      .brand {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
      }}
      .brand h1 {{
        margin: 0;
        font-size: 28px;
        color: #0f2740;
      }}
      .badge {{
        padding: 8px 14px;
        border-radius: 999px;
        background: #eef4ff;
        color: #2d5e9d;
        font-size: 13px;
      }}
      .panel {{
        padding: 24px;
        border: 1px solid #d7e1ec;
        border-radius: 14px;
        background: #fbfdff;
      }}
      .muted {{
        color: #5f7388;
      }}
      .cta {{
        display: inline-block;
        margin-top: 20px;
        padding: 12px 18px;
        border-radius: 12px;
        background: #174b7a;
        color: white;
        text-decoration: none;
      }}
      .list-row {{
        display: flex;
        justify-content: space-between;
        padding: 12px 0;
        border-bottom: 1px solid #e6edf5;
      }}
      .list-row:last-child {{
        border-bottom: none;
      }}
      .warning {{
        background: #fff8e7;
        border: 1px solid #f0d58d;
        color: #7b5a10;
        padding: 14px 16px;
        border-radius: 12px;
        margin-bottom: 16px;
      }}
    </style>
  </head>
  <body>
    <div class="shell">
      <div class="brand">
        <div>
          <h1>NovaTrust Bank</h1>
          <div class="muted">{subtitle}</div>
        </div>
        <div class="badge">Reference: NS-{uuid.uuid4().hex[:8].upper()}</div>
      </div>
      {body_html}
    </div>
  </body>
</html>
"""


def _login_page() -> str:
    return _bank_shell(
        "NovaTrust Sign In",
        """
        <div class="panel">
          <div class="warning">Your access was preserved while our automated security review is in progress.</div>
          <h2>Welcome back</h2>
          <p class="muted">Continue through the review session to keep access to your account tools.</p>
          <div class="list-row"><span>Email</span><span>Verified</span></div>
          <div class="list-row"><span>Password</span><span>Accepted</span></div>
          <div class="list-row"><span>Device trust</span><span>Pending refresh</span></div>
          <a class="cta" href="/dashboard">Continue to account overview</a>
        </div>
        """,
        subtitle="Secure sign-in continuation",
    )


def _dashboard_page() -> str:
    return _bank_shell(
        "NovaTrust Dashboard",
        """
        <div class="panel">
          <h2>Account overview</h2>
          <div class="warning">Some balances are temporarily frozen while overnight security checks complete.</div>
          <div class="list-row"><span>Primary Checking</span><span>$0.00</span></div>
          <div class="list-row"><span>Reserve Savings</span><span>$0.00</span></div>
          <div class="list-row"><span>Card Controls</span><span>Available</span></div>
          <div class="list-row"><span>Transfers</span><span>Queued for review</span></div>
        </div>
        """,
        subtitle="Temporary account review snapshot",
    )


def _transfer_page() -> str:
    return _bank_shell(
        "NovaTrust Transfers",
        """
        <div class="panel">
          <h2>Transfer funds</h2>
          <p class="muted">Outbound transfers remain available, but final settlement may take up to 24 hours.</p>
          <div class="list-row"><span>Review window</span><span>24 hours</span></div>
          <div class="list-row"><span>Destination verification</span><span>Queued</span></div>
          <div class="list-row"><span>Daily limit</span><span>$250,000</span></div>
        </div>
        """,
        subtitle="Wire and ACH review",
    )


def _security_alert_page() -> str:
    return _bank_shell(
        "NovaTrust Security Alert",
        """
        <div class="panel">
          <h2>We've detected unusual activity on your account.</h2>
          <p class="muted">
            Your session has been temporarily suspended while our security team reviews this activity.
          </p>
          <div class="list-row"><span>Estimated review time</span><span>24 hours</span></div>
          <div class="list-row"><span>Support line</span><span>1-800-NOVATRUST</span></div>
          <div class="list-row"><span>Status</span><span>Monitoring in progress</span></div>
          <a class="cta" href="/login">Return to Login</a>
        </div>
        """,
        subtitle="Automated fraud review",
    )


def _generic_page(path: str) -> str:
    safe_path = path or "/"
    return _bank_shell(
        "NovaTrust Request Review",
        f"""
        <div class="panel">
          <h2>Request received</h2>
          <p class="muted">The requested resource <strong>{safe_path}</strong> is being reviewed by our secure operations pipeline.</p>
          <div class="list-row"><span>Status</span><span>Accepted</span></div>
          <div class="list-row"><span>Review queue</span><span>Active</span></div>
          <div class="list-row"><span>Follow-up</span><span>Available after audit refresh</span></div>
        </div>
        """,
        subtitle="Secure operations queue",
    )


def _fake_json_response(path: str, method: str, body: Any = None) -> dict[str, Any]:
    lowered_path = path.lower()
    if lowered_path == "/login" and method == "POST":
        return {"status": "ok", "message": "Login successful", "token": "sandbox-session-active"}
    if lowered_path == "/dashboard":
        return {
            "accounts": [
                {"name": "Primary Checking", "balance": 0.0, "status": "frozen"},
                {"name": "Reserve Savings", "balance": 0.0, "status": "review"},
            ],
            "banner": "Account review in progress.",
        }
    if lowered_path == "/transfer" and method == "POST":
        amount = body.get("amount") if isinstance(body, dict) else None
        return {
            "status": "accepted",
            "message": "Transfer pending review",
            "reference": f"TRX-{uuid.uuid4().hex[:10].upper()}",
            "queued_amount": amount,
        }
    if lowered_path == "/api/internal/user-export":
        return {
            "status": "ok",
            "export_job": "queued",
            "records": 1824,
            "note": "Export package will be available after review completion.",
        }
    if lowered_path in {"/api/admin", "/api/debug"}:
        return {"status": "ok", "message": "Administrative review endpoint acknowledged."}
    if lowered_path == "/.env":
        return {"status": "ok", "APP_ENV": "production", "APP_REGION": "us-east-1"}
    if lowered_path.startswith("/api/"):
        return {"status": "ok", "data": {"path": path, "method": method, "message": "Request accepted for review."}}
    return {"status": "ok", "message": "Request received"}


def _html_or_json_response(request: Request, path: str, method: str, body: Any = None) -> Response:
    if _prefers_html(request) and method == "GET" and not path.startswith("/api/"):
        if path in {"/", "/login"}:
            return HTMLResponse(_login_page())
        if path == "/dashboard":
            return HTMLResponse(_dashboard_page())
        if path == "/transfer":
            return HTMLResponse(_transfer_page())
        if path == "/security-alert":
            return HTMLResponse(_security_alert_page())
        return HTMLResponse(_generic_page(path))
    return JSONResponse(_fake_json_response(path, method, body))


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


app = FastAPI(title="NeuroShield Sandbox", version="0.2.0", lifespan=lifespan)


@app.middleware("http")
async def sandbox_token_middleware(request: Request, call_next):
    if any(request.url.path.startswith(prefix) for prefix in EXEMPT_PATH_PREFIXES):
        return await call_next(request)

    sandbox_token = _token_from_request(request)
    if not sandbox_token:
        return JSONResponse(status_code=401, content={"detail": "Sandbox token required"})

    session = manager.repository.get_session_by_token(sandbox_token)
    if session is None or session.get("ended_at") is not None:
        return JSONResponse(status_code=401, content={"detail": "Invalid sandbox token"})

    request.state.sandbox_token = sandbox_token
    response = await call_next(request)
    if hasattr(response, "set_cookie"):
        response.set_cookie("sandbox_token", sandbox_token, httponly=True, samesite="lax")
    return response


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "timestamp": time.time(), "sandbox_timeout_sec": SANDBOX_TIMEOUT_SEC}


@app.post("/sessions")
def create_session(payload: CreateSessionRequest) -> dict[str, Any]:
    session = manager.create_session(payload)
    return {
        "session_id": session["session_id"],
        "sandbox_token": session["sandbox_token"],
        "status": "created",
        "security_alert_url": "/security-alert",
        "login_url": "/login",
    }


@app.post("/sessions/{sandbox_token}/terminate")
def terminate_session(sandbox_token: str) -> dict[str, Any]:
    session = manager.terminate_session(sandbox_token)
    if session is None:
        raise HTTPException(status_code=404, detail="Sandbox session not found")
    return {"status": "terminated", "session_id": session["session_id"], "sandbox_token": sandbox_token}


@app.get("/sessions/{sandbox_token}/replay")
def replay_session(sandbox_token: str) -> dict[str, Any]:
    return {"session_id": sandbox_token, "actions": manager.replay(sandbox_token)}


async def _handle_sandbox_request(request: Request, body: Any = None) -> Response:
    sandbox_token = getattr(request.state, "sandbox_token", None)
    if not sandbox_token:
        raise HTTPException(status_code=401, detail="Sandbox token required")

    headers = dict(request.headers)
    triggers = _detect_triggers(request.url.path, body, headers)
    response = _html_or_json_response(request, request.url.path, request.method, body)
    manager.log_action(
        sandbox_token=sandbox_token,
        request_data={
            "path": request.url.path,
            "method": request.method,
            "headers_json": headers,
            "body": body,
        },
        response_data={"status_code": response.status_code, "media_type": response.media_type},
        triggers=triggers,
    )
    return response


@app.get("/")
async def root(request: Request) -> Response:
    return await _handle_sandbox_request(request, None)


@app.get("/login")
async def login_page(request: Request) -> Response:
    return await _handle_sandbox_request(request, None)


@app.post("/login")
async def login(request: Request) -> Response:
    body = await _read_request_body(request)
    return await _handle_sandbox_request(request, body)


@app.get("/dashboard")
async def dashboard(request: Request) -> Response:
    return await _handle_sandbox_request(request, None)


@app.get("/transfer")
async def transfer_page(request: Request) -> Response:
    return await _handle_sandbox_request(request, None)


@app.post("/transfer")
async def transfer(request: Request, payload: TransferRequest) -> Response:
    return await _handle_sandbox_request(request, payload.model_dump())


@app.get("/security-alert")
async def security_alert(request: Request) -> Response:
    return await _handle_sandbox_request(request, None)


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def sandbox_api(path: str, request: Request) -> Response:
    body = await _read_request_body(request)
    return await _handle_sandbox_request(request, body)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def catch_all(path: str, request: Request) -> Response:
    body = await _read_request_body(request)
    return await _handle_sandbox_request(request, body)


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
