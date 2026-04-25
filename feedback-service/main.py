from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Protocol, Sequence

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor, Json
except ImportError:  # pragma: no cover - exercised in environments without the DB driver installed
    psycopg2 = None
    RealDictCursor = None

    def Json(value: Any) -> Any:  # type: ignore[misc]
        return value

from kafka import KafkaProducer


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [feedback] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
DATABASE_URL = os.getenv("DATABASE_URL", "")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
FEEDBACK_TOPIC = os.getenv("FEEDBACK_TOPIC", "feedback")
FEATURE_COLUMNS_PATH = os.getenv("FEATURE_COLUMNS_PATH", "")

SQLI_PATTERN = re.compile(
    r"(union\s+select|select\s+.+\s+from|drop\s+table|insert\s+into|delete\s+from|or\s+1\s*=\s*1|--|/\*)",
    re.IGNORECASE,
)
HONEYPOT_PATH_PATTERNS = (
    "/api/admin",
    "/api/debug",
    "/.env",
    "/wp-admin",
    "/api/internal/user-export",
    "/internal/staff-portal",
)
CANARY_KEYS = (
    "csrf-token",
    "canary_token",
    "debug_token",
)


class ProducerLike(Protocol):
    def send(self, topic: str, payload: dict[str, Any]) -> Any:
        ...

    def flush(self, timeout: float | None = None) -> Any:
        ...

    def close(self, timeout: float | None = None) -> Any:
        ...


@dataclass
class SessionLabel:
    label: str
    confidence: float
    attack_type: str
    reason: str


@dataclass
class CompletedSession:
    session_id: str
    actions: list[dict[str, Any]]


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_feature_names() -> list[str]:
    candidates = [
        Path(FEATURE_COLUMNS_PATH).expanduser() if FEATURE_COLUMNS_PATH else None,
        Path("/data/feature_columns.txt"),
        Path(__file__).resolve().parents[1] / "data" / "feature_columns.txt",
        Path(__file__).resolve().parents[1] / "datasets" / "feature_columns.txt",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return [line.strip() for line in candidate.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [f"feature_{index}" for index in range(80)]


def parse_jsonish(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if value in (None, ""):
        return None
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return value
    return value


def ensure_float_list(raw_values: Any, expected_length: int = 80) -> list[float] | None:
    if not isinstance(raw_values, Sequence) or isinstance(raw_values, (str, bytes, bytearray)):
        return None
    values = list(raw_values)
    if not values:
        return [0.0] * expected_length
    try:
        floats = [float(value) for value in values[:expected_length]]
    except (TypeError, ValueError):
        return None
    if len(floats) < expected_length:
        floats.extend([0.0] * (expected_length - len(floats)))
    return floats


def flatten_text_fields(action: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("path", "method", "body", "response_sent", "payload"):
        value = action.get(key)
        parsed = parse_jsonish(value)
        if isinstance(parsed, dict):
            parts.append(json.dumps(parsed, sort_keys=True))
        elif isinstance(parsed, list):
            parts.append(json.dumps(parsed))
        elif parsed is not None:
            parts.append(str(parsed))
    return " ".join(parts).lower()


def iter_texts(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        texts: list[str] = []
        for item in value.values():
            texts.extend(iter_texts(item))
        return texts
    if isinstance(value, list):
        texts: list[str] = []
        for item in value:
            texts.extend(iter_texts(item))
        return texts
    return [str(value)]


def count_login_attempts(actions: Sequence[dict[str, Any]]) -> tuple[int, int]:
    attempts = 0
    distinct_passwords: set[str] = set()
    for action in actions:
        text = flatten_text_fields(action)
        if "login" not in text:
            continue
        attempts += 1
        body = parse_jsonish(action.get("body"))
        if isinstance(body, dict):
            for key in ("password", "pass", "pwd"):
                if body.get(key):
                    distinct_passwords.add(str(body[key]))
    return attempts, len(distinct_passwords)


def detect_label(actions: Sequence[dict[str, Any]]) -> SessionLabel:
    if not actions:
        return SessionLabel(
            label="HACKER",
            confidence=0.55,
            attack_type="UNKNOWN",
            reason="Empty sandbox session still indicates suspicious diversion.",
        )

    texts = [flatten_text_fields(action) for action in actions]
    combined_text = "\n".join(texts)
    if SQLI_PATTERN.search(combined_text):
        return SessionLabel("WEB_ATTACK", 0.95, "SQL_INJECTION", "SQL injection pattern detected in sandbox traffic.")

    for action in actions:
        body = parse_jsonish(action.get("body"))
        if isinstance(body, dict):
            if body.get("username_confirm") not in (None, "", False) or body.get("confirm_routing_number") not in (
                None,
                "",
                False,
            ):
                return SessionLabel(
                    "HACKER",
                    0.91,
                    "HONEYPOT_ACCESS",
                    "A hidden honeypot field was populated during the sandbox session.",
                )
            flattened_body = " ".join(iter_texts(body)).lower()
            if any(token_key in flattened_body for token_key in CANARY_KEYS):
                return SessionLabel(
                    "HACKER",
                    0.9,
                    "CANARY_TOKEN",
                    "A canary token indicator appeared in the sandbox request payload.",
                )

    duration_seconds = max(
        float(actions[-1].get("timestamp", 0.0) or 0.0) - float(actions[0].get("timestamp", 0.0) or 0.0),
        0.0,
    )
    duration_minutes = max(duration_seconds / 60.0, 1.0)
    request_rate = len(actions) / duration_minutes
    if request_rate > 100.0:
        return SessionLabel("DDOS", 0.88, "TRAFFIC_FLOOD", "Request rate exceeded 100 actions per minute.")

    login_attempts, distinct_passwords = count_login_attempts(actions)
    if login_attempts > 10 and distinct_passwords > 1:
        return SessionLabel(
            "BRUTE_FORCE",
            0.92,
            "CREDENTIAL_ATTACK",
            "Repeated login attempts with multiple passwords were observed.",
        )

    unique_ports = {
        int(action["port"])
        for action in actions
        if action.get("port") not in (None, "")
        and str(action.get("port")).isdigit()
    }
    if len(unique_ports) > 5:
        return SessionLabel("RECONNAISSANCE", 0.81, "PORT_SCAN", "Multiple destination ports were targeted.")

    for action in actions:
        path = str(action.get("path") or "").lower()
        if any(path.startswith(pattern) for pattern in HONEYPOT_PATH_PATTERNS):
            return SessionLabel("HACKER", 0.90, "HONEYPOT_ACCESS", f"Honeypot endpoint accessed: {path}")

    return SessionLabel("HACKER", 0.62, "UNKNOWN", "Session was sandboxed and remained suspicious after review.")


class FeedbackRepository:
    def __init__(self, database_url: str, feature_names: Sequence[str]) -> None:
        if not database_url:
            raise ValueError("DATABASE_URL is required for the feedback service.")
        self.database_url = database_url
        self.feature_names = list(feature_names)

    def connect(self):
        if psycopg2 is None or RealDictCursor is None:
            raise RuntimeError(
                "psycopg2 is required to connect to PostgreSQL. Install feedback-service requirements first."
            )
        return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)

    def bootstrap(self, conn) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS labeled_training_data (
                    id BIGSERIAL PRIMARY KEY,
                    session_id TEXT UNIQUE NOT NULL,
                    features JSONB NOT NULL,
                    label TEXT NOT NULL,
                    confidence DOUBLE PRECISION NOT NULL,
                    attack_type TEXT,
                    trigger_reason TEXT,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            conn.commit()

    def fetch_completed_sessions(self, conn) -> list[CompletedSession]:
        columns = self._get_table_columns(conn, "sandbox_actions")
        if not columns:
            log.warning("Table sandbox_actions is missing; feedback service has nothing to process yet.")
            return []
        if "session_id" not in columns:
            log.warning("sandbox_actions does not include session_id; cannot build feedback labels.")
            return []

        if "actions" in columns:
            return self._fetch_aggregated_sessions(conn)
        return self._fetch_action_rows_by_session(conn, columns)

    def _get_table_columns(self, conn, table_name: str) -> set[str]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                """,
                (table_name,),
            )
            return {row["column_name"] for row in cur.fetchall()}

    def _fetch_aggregated_sessions(self, conn) -> list[CompletedSession]:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT session_id, actions
                FROM sandbox_actions
                WHERE sandbox_ended_at IS NOT NULL
                  AND COALESCE(feedback_sent, FALSE) = FALSE
                ORDER BY sandbox_ended_at ASC
                """
            )
            rows = cur.fetchall()
        sessions: list[CompletedSession] = []
        for row in rows:
            raw_actions = parse_jsonish(row.get("actions")) or []
            actions = [self._normalize_action_record(item, fallback_session_id=row["session_id"]) for item in raw_actions]
            sessions.append(CompletedSession(session_id=str(row["session_id"]), actions=actions))
        return sessions

    def _fetch_action_rows_by_session(self, conn, columns: set[str]) -> list[CompletedSession]:
        filters = ["session_id IS NOT NULL"]
        if "sandbox_ended_at" in columns:
            filters.append("sandbox_ended_at IS NOT NULL")
        if "feedback_sent" in columns:
            filters.append("COALESCE(feedback_sent, FALSE) = FALSE")

        query = f"""
            SELECT DISTINCT session_id
            FROM sandbox_actions
            WHERE {' AND '.join(filters)}
            ORDER BY session_id
        """
        with conn.cursor() as cur:
            cur.execute(query)
            session_rows = cur.fetchall()

        sessions: list[CompletedSession] = []
        for row in session_rows:
            session_id = str(row["session_id"])
            actions = self._fetch_session_actions(conn, session_id, columns)
            if actions:
                sessions.append(CompletedSession(session_id=session_id, actions=actions))
        return sessions

    def _fetch_session_actions(self, conn, session_id: str, columns: set[str]) -> list[dict[str, Any]]:
        select_parts = ["session_id"]
        for candidate in (
            "action_id",
            "sandbox_token",
            "path",
            "method",
            "headers_json",
            "body",
            "response_sent",
            "timestamp",
            "port",
            "flow_features",
            "features",
            "metadata",
            "payload",
            "request_json",
        ):
            if candidate in columns:
                select_parts.append(candidate)
        order_by = "timestamp ASC" if "timestamp" in columns else "session_id ASC"
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {', '.join(select_parts)}
                FROM sandbox_actions
                WHERE session_id = %s
                ORDER BY {order_by}
                """,
                (session_id,),
            )
            rows = cur.fetchall()
        return [self._normalize_action_record(row, fallback_session_id=session_id) for row in rows]

    def _normalize_action_record(self, row: dict[str, Any], fallback_session_id: str) -> dict[str, Any]:
        action = dict(row)
        action["session_id"] = str(action.get("session_id") or fallback_session_id)
        for key in ("headers_json", "body", "response_sent", "metadata", "payload", "request_json"):
            if key in action:
                action[key] = parse_jsonish(action[key])
        if action.get("timestamp") in (None, ""):
            action["timestamp"] = 0.0
        return action

    def lookup_verdict_features(self, conn, session_id: str) -> list[float] | None:
        columns = self._get_table_columns(conn, "verdicts")
        if not columns or "session_id" not in columns:
            return None
        select_candidates = [candidate for candidate in ("features", "features_dict", "flow_features") if candidate in columns]
        if not select_candidates:
            return None
        order_parts: list[str] = []
        if "created_at" in columns:
            order_parts.append("created_at DESC NULLS LAST")
        if "timestamp" in columns:
            order_parts.append("timestamp DESC NULLS LAST")
        if not order_parts:
            order_parts.append("session_id DESC")
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {', '.join(select_candidates)}
                FROM verdicts
                WHERE session_id = %s
                ORDER BY {', '.join(order_parts)}
                LIMIT 1
                """,
                (session_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        for candidate in select_candidates:
            feature_vector = self._coerce_verdict_feature_column(row.get(candidate))
            if feature_vector is not None:
                return feature_vector
        return None

    def _coerce_verdict_feature_column(self, raw_value: Any) -> list[float] | None:
        parsed = parse_jsonish(raw_value)
        as_list = ensure_float_list(parsed, expected_length=80)
        if as_list is not None:
            return as_list
        if isinstance(parsed, dict):
            vector = [float(parsed.get(name, 0.0) or 0.0) for name in self.feature_names[:80]]
            if len(vector) < 80:
                vector.extend([0.0] * (80 - len(vector)))
            return vector[:80]
        return None

    def store_label(self, conn, session_id: str, features: Sequence[float], label: SessionLabel, metadata: dict[str, Any]) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO labeled_training_data (
                    session_id,
                    features,
                    label,
                    confidence,
                    attack_type,
                    trigger_reason,
                    metadata,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (session_id) DO UPDATE
                SET features = EXCLUDED.features,
                    label = EXCLUDED.label,
                    confidence = EXCLUDED.confidence,
                    attack_type = EXCLUDED.attack_type,
                    trigger_reason = EXCLUDED.trigger_reason,
                    metadata = EXCLUDED.metadata,
                    created_at = NOW()
                """,
                (
                    session_id,
                    Json(list(features)),
                    label.label,
                    label.confidence,
                    label.attack_type,
                    label.reason,
                    Json(metadata),
                ),
            )
            conn.commit()

    def mark_feedback_sent(self, conn, session_id: str, label: str) -> None:
        columns = self._get_table_columns(conn, "sandbox_actions")
        assignments: list[str] = []
        params: list[Any] = []
        if "feedback_sent" in columns:
            assignments.append("feedback_sent = TRUE")
        if "assigned_label" in columns:
            assignments.append("assigned_label = %s")
            params.append(label)
        if not assignments:
            conn.rollback()
            return
        params.append(session_id)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE sandbox_actions
                SET {', '.join(assignments)}
                WHERE session_id = %s
                """,
                params,
            )
            conn.commit()


def build_feedback_metadata(actions: Sequence[dict[str, Any]], label: SessionLabel) -> dict[str, Any]:
    login_attempts, distinct_passwords = count_login_attempts(actions)
    unique_ports = sorted(
        {
            int(action["port"])
            for action in actions
            if action.get("port") not in (None, "")
            and str(action.get("port")).isdigit()
        }
    )
    timestamps = [float(action.get("timestamp", 0.0) or 0.0) for action in actions]
    duration_seconds = max((max(timestamps) - min(timestamps)) if timestamps else 0.0, 0.0)
    duration_minutes = max(duration_seconds / 60.0, 1.0)
    request_rate = len(actions) / duration_minutes
    honeypot_hits = [
        str(action.get("path") or "")
        for action in actions
        if any(str(action.get("path") or "").lower().startswith(pattern) for pattern in HONEYPOT_PATH_PATTERNS)
    ]
    return {
        "session_length": len(actions),
        "duration_seconds": duration_seconds,
        "request_rate_per_minute": round(request_rate, 3),
        "login_attempts": login_attempts,
        "distinct_passwords": distinct_passwords,
        "unique_ports": unique_ports,
        "honeypot_hits": honeypot_hits,
        "attack_type": label.attack_type,
    }


def extract_feature_vector(
    actions: Sequence[dict[str, Any]],
    repository: FeedbackRepository | None = None,
    conn: Any | None = None,
    session_id: str | None = None,
) -> list[float]:
    for action in actions:
        for candidate_key in ("features", "flow_features"):
            if candidate_key not in action:
                continue
            vector = ensure_float_list(parse_jsonish(action.get(candidate_key)), expected_length=80)
            if vector is not None:
                return vector

        for nested_key in ("body", "metadata", "payload", "request_json", "response_sent"):
            nested = parse_jsonish(action.get(nested_key))
            if not isinstance(nested, dict):
                continue
            for candidate_key in ("features", "flow_features"):
                vector = ensure_float_list(parse_jsonish(nested.get(candidate_key)), expected_length=80)
                if vector is not None:
                    return vector

    if repository is not None and conn is not None and session_id:
        verdict_features = repository.lookup_verdict_features(conn, session_id)
        if verdict_features is not None:
            return verdict_features

    return heuristic_feature_vector(actions)


def heuristic_feature_vector(actions: Sequence[dict[str, Any]]) -> list[float]:
    vector = [0.0] * 80
    if not actions:
        return vector

    timestamps = [float(action.get("timestamp", 0.0) or 0.0) for action in actions]
    duration_seconds = max((max(timestamps) - min(timestamps)) if timestamps else 0.0, 0.0)
    duration_minutes = max(duration_seconds / 60.0, 1.0)
    request_rate = len(actions) / duration_minutes
    login_attempts, distinct_passwords = count_login_attempts(actions)
    unique_ports = {
        int(action["port"])
        for action in actions
        if action.get("port") not in (None, "")
        and str(action.get("port")).isdigit()
    }
    average_body_size = 0.0
    if actions:
        average_body_size = sum(len(json.dumps(parse_jsonish(action.get("body")) or "")) for action in actions) / len(actions)

    vector[0] = duration_seconds
    vector[1] = float(len(actions))
    vector[2] = float(request_rate)
    vector[3] = float(login_attempts)
    vector[4] = float(distinct_passwords)
    vector[5] = float(len(unique_ports))
    vector[6] = float(len([action for action in actions if SQLI_PATTERN.search(flatten_text_fields(action))]))
    vector[7] = float(len([action for action in actions if any(str(action.get("path") or "").lower().startswith(pattern) for pattern in HONEYPOT_PATH_PATTERNS)]))
    vector[8] = float(average_body_size)
    vector[9] = float(len([action for action in actions if str(action.get("method") or "").upper() == "POST"]))
    return vector


class FeedbackService:
    def __init__(
        self,
        database_url: str = DATABASE_URL,
        kafka_bootstrap: str = KAFKA_BOOTSTRAP,
        poll_interval_seconds: int = POLL_INTERVAL_SECONDS,
        feedback_topic: str = FEEDBACK_TOPIC,
        producer: ProducerLike | None = None,
    ) -> None:
        self.feature_names = load_feature_names()
        self.repository = FeedbackRepository(database_url=database_url, feature_names=self.feature_names)
        self.kafka_bootstrap = kafka_bootstrap
        self.poll_interval_seconds = poll_interval_seconds
        self.feedback_topic = feedback_topic
        self._producer = producer

    @property
    def producer(self) -> ProducerLike:
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap,
                value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
                acks="all",
                retries=3,
            )
        return self._producer

    def run_once(self) -> int:
        processed = 0
        with self.repository.connect() as conn:
            self.repository.bootstrap(conn)
            sessions = self.repository.fetch_completed_sessions(conn)
            for session in sessions:
                self._process_session(conn, session)
                processed += 1
        if processed == 0:
            log.info("No completed sandbox sessions pending feedback.")
        return processed

    def _process_session(self, conn, session: CompletedSession) -> None:
        label = detect_label(session.actions)
        features = extract_feature_vector(
            session.actions,
            repository=self.repository,
            conn=conn,
            session_id=session.session_id,
        )
        metadata = build_feedback_metadata(session.actions, label)
        sample = {
            "session_id": session.session_id,
            "timestamp": _utcnow_iso(),
            "label": label.label,
            "confidence": label.confidence,
            "attack_type": label.attack_type,
            "trigger_reason": label.reason,
            "features": features,
            "feature_count": len(features),
            "metadata": metadata,
        }

        self.repository.store_label(conn, session.session_id, features, label, metadata)
        self.producer.send(self.feedback_topic, sample)
        self.producer.flush(timeout=5)
        self.repository.mark_feedback_sent(conn, session.session_id, label.label)

        log.info(
            "Labeled session %s as %s -> published to %s topic.",
            session.session_id,
            label.label,
            self.feedback_topic,
        )

    def run_forever(self) -> None:
        log.info("Feedback service started. Writing labels to labeled_training_data.")
        while True:
            try:
                self.run_once()
            except Exception as exc:
                log.exception("Feedback service iteration failed: %s", exc)
            time.sleep(self.poll_interval_seconds)

    def close(self) -> None:
        if self._producer is not None:
            try:
                self._producer.close(timeout=5)
            finally:
                self._producer = None


def main() -> None:
    service = FeedbackService()
    try:
        service.run_forever()
    finally:
        service.close()


if __name__ == "__main__":
    main()
