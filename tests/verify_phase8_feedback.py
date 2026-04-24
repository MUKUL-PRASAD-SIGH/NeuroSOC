from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "feedback-service"))

import main as feedback_main


class FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict]] = []

    def send(self, topic: str, payload: dict) -> None:
        self.sent.append((topic, payload))

    def flush(self, timeout: float | None = None) -> None:
        return None

    def close(self, timeout: float | None = None) -> None:
        return None


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeRepository:
    def __init__(self) -> None:
        self.feature_names = [f"feature_{index}" for index in range(80)]
        self.marked: list[tuple[str, str]] = []
        self.saved: list[dict] = []

    def connect(self):
        return FakeConnection()

    def bootstrap(self, conn) -> None:
        return None

    def fetch_completed_sessions(self, conn):
        brute_force_actions = [
            {
                "session_id": "bf-1",
                "timestamp": 0.0,
                "path": "/login",
                "method": "POST",
                "body": {"username": "alice", "password": "guess-1", "flow_features": [0.1] * 80},
            }
        ]
        for index in range(1, 12):
            brute_force_actions.append(
                {
                    "session_id": "bf-1",
                    "timestamp": float(index),
                    "path": "/login",
                    "method": "POST",
                    "body": {"username": "alice", "password": f"guess-{index + 1}"},
                }
            )

        sql_actions = [
            {
                "session_id": "sql-1",
                "timestamp": 0.0,
                "path": "/transfer",
                "method": "POST",
                "body": {"memo": "' UNION SELECT password FROM users --"},
            }
        ]
        return [
            feedback_main.CompletedSession(session_id="bf-1", actions=brute_force_actions),
            feedback_main.CompletedSession(session_id="sql-1", actions=sql_actions),
        ]

    def lookup_verdict_features(self, conn, session_id: str):
        return None

    def store_label(self, conn, session_id: str, features, label, metadata) -> None:
        self.saved.append(
            {
                "session_id": session_id,
                "features": list(features),
                "label": label.label,
                "confidence": label.confidence,
                "attack_type": label.attack_type,
                "metadata": metadata,
            }
        )

    def mark_feedback_sent(self, conn, session_id: str, label: str) -> None:
        self.marked.append((session_id, label))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print("=========================================================")
    print("[TEST] PHASE 8 FEEDBACK SERVICE")
    print("=========================================================\n")

    producer = FakeProducer()
    service = feedback_main.FeedbackService(
        database_url="postgresql://unused",
        kafka_bootstrap="unused:9092",
        poll_interval_seconds=1,
        producer=producer,
    )
    service.repository = FakeRepository()
    service.feature_names = service.repository.feature_names

    processed = service.run_once()
    assert_true(processed == 2, "Feedback service should process both pending sandbox sessions.")
    assert_true(len(producer.sent) == 2, "Feedback service should publish one feedback message per labeled session.")

    labels = {payload["session_id"]: payload["label"] for _, payload in producer.sent}
    assert_true(labels["bf-1"] == "BRUTE_FORCE", "Repeated login attempts with multiple passwords should label BRUTE_FORCE.")
    assert_true(labels["sql-1"] == "WEB_ATTACK", "SQL injection indicators should label WEB_ATTACK.")

    feature_lengths = {payload["session_id"]: len(payload["features"]) for _, payload in producer.sent}
    assert_true(feature_lengths["bf-1"] == 80, "Feedback samples must always publish 80 features.")
    assert_true(feature_lengths["sql-1"] == 80, "Heuristic fallback features must still publish 80 values.")

    assert_true(
        ("bf-1", "BRUTE_FORCE") in service.repository.marked and ("sql-1", "WEB_ATTACK") in service.repository.marked,
        "Processed sessions should be marked as feedback_sent with their assigned labels.",
    )
    print("[PASS] Feedback service labels sandbox sessions, persists them, and publishes feedback events.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
