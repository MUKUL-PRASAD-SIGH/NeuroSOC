from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "models"

os.environ.setdefault("MODEL_PATH", str(MODELS_DIR))
os.environ.setdefault("MODEL_VERSION_FILE", str(MODELS_DIR / "model_version.json"))
os.environ.setdefault("FEATURE_COLUMNS_PATH", str(REPO_ROOT / "data" / "feature_columns.txt"))

sys.path.insert(0, str(REPO_ROOT / "inference-service"))

import main as inference_main
from core.behavioral.profiler import BehavioralProfiler


class FakeSandboxGateway:
    def __init__(self) -> None:
        self.created: dict[str, str] = {}

    def create_session(self, session_id: str, user_id: str, source_ip: str) -> dict[str, str]:
        token = f"sbx-{session_id}"
        self.created[session_id] = token
        return {
            "session_id": session_id,
            "sandbox_token": token,
            "user_id": user_id,
            "source_ip": source_ip,
        }

    def replay(self, sandbox_token: str) -> dict[str, object]:
        return {
            "sandbox_token": sandbox_token,
            "actions": [
                {
                    "path": "/login",
                    "method": "POST",
                    "timestamp": 1.0,
                    "body": {"email": "bot@example.com"},
                }
            ],
        }


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def reset_runtime() -> None:
    inference_main.runtime._latest_verdicts.clear()
    inference_main.runtime._latest_alerts.clear()
    inference_main.runtime._processed_messages = 0
    inference_main.portal_state = inference_main.PortalState()
    inference_main.sandbox_gateway = FakeSandboxGateway()
    inference_main.API_KEY = ""


def main() -> int:
    print("=========================================================")
    print("[TEST] PHASE 9 FASTAPI GATEWAY")
    print("=========================================================\n")

    inference_main.runtime.start = lambda: None
    inference_main.runtime.stop = lambda: None
    inference_main.runtime._ensure_producer = lambda: None
    inference_main.runtime._producer = None

    with tempfile.TemporaryDirectory(prefix="neuroshield-phase9-") as temp_dir:
        version_path = Path(temp_dir) / "model_version.json"
        behavior_dir = Path(temp_dir) / "behavioral"
        behavior_dir.mkdir(parents=True, exist_ok=True)

        version_path.write_text(
            json.dumps(
                {
                    "version": "0.9.0",
                    "snn": None,
                    "lnn": None,
                    "xgb": None,
                    "timestamp": "2026-04-25T00:00:00Z",
                    "validation_f1": {"snn": 0.91, "lnn": 0.89, "xgb": 0.94},
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        inference_main.runtime.engine.model_version_path = version_path
        inference_main.runtime.engine.current_model_version = "0.9.0"
        inference_main.runtime.engine.current_validation_f1 = {"snn": 0.91, "lnn": 0.89, "xgb": 0.94}
        inference_main.runtime.engine.behavioral_profiler = BehavioralProfiler(storage_dir=behavior_dir, database_url=None)

        reset_runtime()
        client = TestClient(inference_main.app)

        print(">>> CHECKPOINT 9A: Health and model metadata <<<")
        health_response = client.get("/health")
        model_response = client.get("/api/model/version")
        assert_true(health_response.status_code == 200, "Health endpoint should stay live.")
        assert_true(model_response.status_code == 200, "Model version endpoint should return HTTP 200.")
        assert_true(len(model_response.json()["versions"]) >= 3, "Model version payload should expose dashboard-friendly version rows.")
        print("[PASS] Health and model metadata routes respond with the Phase 9 contract.")

        print("\n>>> CHECKPOINT 9B: Behavioral intake and legitimate login <<<")
        behavior_response = client.post(
            "/api/behavioral",
            json={
                "user_id": "normal1@novatrust.com",
                "session_id": "portal-legit",
                "source_ip": "127.0.0.1",
                "events": [
                    {"type": "pagevisit", "timestamp": 1.0, "page": "/login"},
                    {"type": "mousemove", "timestamp": 1.1, "x": 20, "y": 30},
                    {"type": "keydown", "timestamp": 1.2, "key": "n"},
                ],
            },
        )
        login_response = client.post(
            "/api/bank/login",
            json={
                "email": "normal1@novatrust.com",
                "password": "password123",
                "session_id": "portal-legit",
                "source_ip": "127.0.0.1",
            },
        )
        login_payload = login_response.json()
        assert_true(behavior_response.status_code == 200, "Behavioral intake should return HTTP 200.")
        assert_true(login_response.status_code == 200, "Bank login endpoint should return HTTP 200.")
        assert_true(login_payload["authenticated"] is True, "Known demo credentials should authenticate successfully.")
        assert_true(login_payload["next"] == "/dashboard", "Legitimate login should route to the dashboard.")
        print("[PASS] Behavioral intake and legitimate login flow work end-to-end.")

        print("\n>>> CHECKPOINT 9C: User verdict lookup and current-session view <<<")
        user_verdict = client.get("/api/verdicts/alice")
        current_verdict = client.get("/api/verdicts/current")
        assert_true(user_verdict.status_code == 200, "Per-user verdict lookup should succeed after login.")
        assert_true(current_verdict.status_code == 200, "Current verdict endpoint should succeed.")
        current_payload = current_verdict.json()
        assert_true("snnScore" in current_payload and "behavioralDelta" in current_payload, "Current verdict payload should expose camelCase portal fields.")
        print("[PASS] Verdict lookup routes expose the expected Phase 9 shapes.")

        print("\n>>> CHECKPOINT 9D: Honeypot escalation and sandbox activation <<<")
        honeypot_response = client.post(
            "/api/bank/honeypot-hit",
            json={
                "source": "login_form",
                "user_id": "alice",
                "session_id": "portal-legit",
                "source_ip": "127.0.0.1",
            },
        )
        honeypot_payload = honeypot_response.json()
        assert_true(honeypot_response.status_code == 200, "Honeypot capture route should return HTTP 200.")
        assert_true(honeypot_payload["verdict"] == "HACKER", "Honeypot signals should escalate the session to HACKER.")
        assert_true(honeypot_payload["sandbox"]["active"] is True, "Honeypot escalation should activate sandbox orchestration.")
        assert_true("sandbox_token=" in honeypot_response.headers.get("set-cookie", ""), "Sandbox activation should set the sandbox token cookie.")
        print("[PASS] Honeypot events trigger HACKER verdicts and sandbox tokens.")

        print("\n>>> CHECKPOINT 9E: Alerts and sandbox replay <<<")
        alerts_response = client.get("/api/alerts")
        replay_response = client.get("/api/sandbox/portal-legit/replay")
        alerts_payload = alerts_response.json()
        replay_payload = replay_response.json()
        assert_true(alerts_response.status_code == 200, "Alerts endpoint should return HTTP 200.")
        assert_true(replay_response.status_code == 200, "Sandbox replay endpoint should return HTTP 200.")
        assert_true(bool(alerts_payload) and "message" in alerts_payload[0], "Alerts should be normalized for the dashboard.")
        assert_true(len(replay_payload["actions"]) >= 1, "Replay endpoint should expose sandbox activity.")
        print("[PASS] Dashboard alert payloads and sandbox replay are available.")

        print("\n>>> CHECKPOINT 9F: Optional API-key enforcement <<<")
        inference_main.API_KEY = "phase9-secret"
        unauthorized = client.get("/api/stats")
        authorized = client.get("/api/stats", headers={"X-API-Key": "phase9-secret"})
        assert_true(unauthorized.status_code == 401, "Protected routes should reject requests without X-API-Key when API_KEY is configured.")
        assert_true(authorized.status_code == 200, "Protected routes should accept the correct X-API-Key.")
        inference_main.API_KEY = ""
        print("[PASS] Optional API-key enforcement works as designed.")

    print("\n[SUCCESS] Phase 9 FastAPI gateway checkpoints passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
