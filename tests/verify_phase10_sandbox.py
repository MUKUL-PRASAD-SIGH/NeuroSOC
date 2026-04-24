from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "sandbox-service"))

import main as sandbox_main


class FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict]] = []

    def send(self, topic: str, payload: dict) -> None:
        self.sent.append((topic, payload))

    def flush(self, timeout: float | None = None) -> None:
        return None

    def close(self, timeout: float | None = None) -> None:
        return None


class FakeRepository:
    def __init__(self) -> None:
        self.sessions: dict[str, dict] = {}
        self.actions: list[dict] = []
        self.hits: list[dict] = []
        self.expire_queue: list[str] = []

    def bootstrap(self) -> None:
        return None

    def create_session(self, session_id: str, user_id: str, source_ip: str) -> dict:
        token = f"sbx-{session_id}"
        session = {
            "session_id": session_id,
            "sandbox_token": token,
            "user_id": user_id,
            "source_ip": source_ip,
            "created_at": "now",
            "ended_at": None,
        }
        self.sessions[token] = session
        return session

    def get_session_by_token(self, sandbox_token: str) -> dict | None:
        return self.sessions.get(sandbox_token)

    def log_action(
        self,
        sandbox_token: str,
        path: str,
        method: str,
        headers_json: dict,
        body,
        response_sent,
        trigger_tags: list[str],
    ) -> None:
        session = self.sessions.get(sandbox_token)
        if session is None or session.get("ended_at") is not None:
            raise sandbox_main.HTTPException(status_code=401, detail="Invalid sandbox token")
        self.actions.append(
            {
                "session_id": session["session_id"],
                "sandbox_token": sandbox_token,
                "path": path,
                "method": method,
                "headers_json": headers_json,
                "body": body,
                "response_sent": response_sent,
                "trigger_tags": trigger_tags,
            }
        )

    def record_honeypot_hit(self, sandbox_token: str, path: str, trigger_type: str, severity: str, details: dict) -> None:
        session = self.sessions.get(sandbox_token)
        if session is None:
            return
        self.hits.append(
            {
                "session_id": session["session_id"],
                "sandbox_token": sandbox_token,
                "path": path,
                "trigger_type": trigger_type,
                "severity": severity,
                "details": details,
            }
        )

    def terminate_session(self, sandbox_token: str) -> dict | None:
        session = self.sessions.get(sandbox_token)
        if session is None or session.get("ended_at") is not None:
            return None
        session["ended_at"] = "ended"
        return session

    def expired_tokens(self, timeout_seconds: int) -> list[str]:
        tokens = list(self.expire_queue)
        self.expire_queue.clear()
        return tokens

    def list_session_actions(self, sandbox_token: str) -> list[dict]:
        return [action for action in self.actions if action["sandbox_token"] == sandbox_token]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print("=========================================================")
    print("[TEST] PHASE 10 SANDBOX SERVICE")
    print("=========================================================\n")

    fake_repository = FakeRepository()
    fake_producer = FakeProducer()

    original_repository = sandbox_main.manager.repository
    original_start = sandbox_main.manager.start
    original_stop = sandbox_main.manager.stop
    original_producer = sandbox_main.manager._producer

    sandbox_main.manager.repository = fake_repository
    sandbox_main.manager._producer = fake_producer
    sandbox_main.manager.start = lambda: None
    sandbox_main.manager.stop = lambda: None

    try:
        client = TestClient(sandbox_main.app)

        print(">>> CHECKPOINT 10A: Session creation and token enforcement <<<")
        session_payload = client.post(
            "/sessions",
            json={"session_id": "phase10-demo", "user_id": "eve", "source_ip": "198.51.100.33"},
        ).json()
        token = session_payload["sandbox_token"]
        unauthorized = client.get("/dashboard")
        assert_true(unauthorized.status_code == 401, "Dashboard must require a sandbox token.")
        print("[PASS] Sandbox sessions are created and protected by token enforcement.")

        print("\n>>> CHECKPOINT 10B: Core decoy routes <<<")
        login_response = client.post(
            "/login",
            json={"email": "eve@example.com", "password": "guess-1"},
            headers={"X-Sandbox-Token": token, "accept": "application/json"},
        )
        dashboard_response = client.get("/dashboard", headers={"X-Sandbox-Token": token, "accept": "text/html"})
        transfer_response = client.post(
            "/transfer",
            json={
                "amount": 9999.0,
                "destination": "acct-123",
                "memo": "review payment",
                "confirm_routing_number": "bot-filled",
                "flow_features": [0.1] * 80,
            },
            headers={"X-Sandbox-Token": token, "accept": "application/json"},
        )
        assert_true(login_response.status_code == 200, "Sandbox login should always return success.")
        assert_true(dashboard_response.status_code == 200, "Sandbox dashboard should render successfully.")
        assert_true(transfer_response.status_code == 200, "Sandbox transfer should accept and queue the request.")
        print("[PASS] Core decoy routes behave like a controlled banking mirror.")

        print("\n>>> CHECKPOINT 10C: Honeypot capture and replay <<<")
        admin_response = client.get("/api/admin", headers={"X-Sandbox-Token": token})
        replay_response = client.get(f"/sessions/{token}/replay")
        assert_true(admin_response.status_code == 200, "Honeypot API should stay reachable inside the sandbox.")
        assert_true(len(replay_response.json()["actions"]) >= 3, "Replay endpoint should expose captured sandbox actions.")
        assert_true(any(hit["trigger_type"] == "HONEYPOT_ENDPOINT" for hit in fake_repository.hits), "Honeypot endpoint access should be recorded.")
        assert_true(any(hit["trigger_type"] == "HONEYPOT_FIELD" for hit in fake_repository.hits), "Hidden honeypot field use should be recorded.")
        print("[PASS] Honeypot signals are captured and replay data is available.")

        print("\n>>> CHECKPOINT 10D: Termination and expiry <<<")
        terminated = client.post(f"/sessions/{token}/terminate")
        assert_true(terminated.status_code == 200, "Session termination endpoint should succeed.")
        assert_true(any(topic == sandbox_main.FEEDBACK_TRIGGER_TOPIC for topic, _ in fake_producer.sent), "Termination should publish to feedback-trigger.")

        second_session = client.post(
            "/sessions",
            json={"session_id": "expiring-demo", "user_id": "mallory", "source_ip": "203.0.113.9"},
        ).json()
        fake_repository.expire_queue.append(second_session["sandbox_token"])
        expired_count = sandbox_main.manager.expire_sessions()
        assert_true(expired_count == 1, "Expire loop should terminate queued expired sessions.")
        print("[PASS] Termination and background expiry both work.")

    finally:
        sandbox_main.manager.repository = original_repository
        sandbox_main.manager.start = original_start
        sandbox_main.manager.stop = original_stop
        sandbox_main.manager._producer = original_producer

    print("\n[SUCCESS] Phase 10 sandbox checkpoints passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
