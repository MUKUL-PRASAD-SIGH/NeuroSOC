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
                    "path": "/api/internal/user-export",
                    "method": "GET",
                    "timestamp": 1.0,
                    "body": {},
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


def post_behavioral(client: TestClient, user_id: str, session_id: str, page: str) -> dict:
    response = client.post(
        "/api/behavioral",
        json={
            "user_id": user_id,
            "session_id": session_id,
            "source_ip": "127.0.0.1",
            "page": page,
            "events": [
                {"type": "pagevisit", "timestamp": 1.0, "page": page},
                {"type": "mousemove", "timestamp": 1.1, "x": 24, "y": 30},
                {"type": "keydown", "timestamp": 1.2, "key": "n"},
            ],
        },
    )
    assert_true(response.status_code == 200, f"Behavioral ingest failed for {page}.")
    return response.json()


def main() -> int:
    print("=========================================================")
    print("[TEST] PHASE 11 BANK PORTAL FLOW")
    print("=========================================================\n")

    inference_main.runtime.start = lambda: None
    inference_main.runtime.stop = lambda: None
    inference_main.runtime._ensure_producer = lambda: None
    inference_main.runtime._producer = None

    with tempfile.TemporaryDirectory(prefix="neuroshield-phase11-bank-") as temp_dir:
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

        print(">>> CHECKPOINT 11A: Complete normal bank flow <<<")
        session_id = "portal-full-flow"
        post_behavioral(client, "normal1@novatrust.com", session_id, "/login")
        login_response = client.post(
            "/api/bank/login",
            json={
                "email": "normal1@novatrust.com",
                "password": "password123",
                "session_id": session_id,
                "source_ip": "127.0.0.1",
            },
        )
        assert_true(login_response.status_code == 200, "Normal bank login should succeed.")
        login_payload = login_response.json()
        assert_true(login_payload["authenticated"] is True, "Known demo account should authenticate.")
        assert_true(login_payload["next"] == "/dashboard", "Normal login should route to the dashboard.")

        user_verdict = client.get("/api/verdicts/alice")
        assert_true(user_verdict.status_code == 200, "Per-user verdict lookup should succeed after login.")

        post_behavioral(client, "alice", session_id, "/dashboard")
        post_behavioral(client, "alice", session_id, "/transfer")
        transfer_response = client.post(
            "/api/bank/transfer",
            json={
                "user_id": "alice",
                "session_id": session_id,
                "source_ip": "127.0.0.1",
                "destination": "Utilities Reserve acct-4521",
                "amount": 125.0,
                "memo": "Monthly utility settlement",
            },
        )
        transfer_payload = transfer_response.json()
        assert_true(transfer_response.status_code == 200, "Normal transfer should succeed.")
        assert_true(transfer_payload["status"] == "accepted", "Low-risk transfer should stay accepted.")
        assert_true(transfer_payload["sandbox"] is None, "Normal transfer should not activate sandbox.")

        current_response = client.get("/api/verdicts/current")
        current_payload = current_response.json()
        assert_true(current_response.status_code == 200, "Current verdict route should stay live.")
        assert_true(current_payload["verdict"] != "HACKER", "Complete normal flow should stay out of the hacker branch.")
        print("[PASS] Complete bank flow stays on the legitimate path.")

        print("\n>>> CHECKPOINT 11B: Forgetful-user recovery flow <<<")
        session_id = "portal-forgetful-flow"
        post_behavioral(client, "normal1@novatrust.com", session_id, "/login")

        for wrong_password in ("Password124", "password12"):
            attempt = client.post(
                "/api/bank/login",
                json={
                    "email": "normal1@novatrust.com",
                    "password": wrong_password,
                    "session_id": session_id,
                    "source_ip": "127.0.0.1",
                },
            )
            assert_true(attempt.status_code == 200, "Wrong-password attempt should still return a structured JSON response.")

        recovery = client.post(
            "/api/bank/login",
            json={
                "email": "normal1@novatrust.com",
                "password": "password123",
                "session_id": session_id,
                "source_ip": "127.0.0.1",
            },
        )
        recovery_payload = recovery.json()
        assert_true(recovery.status_code == 200, "Recovery login should succeed.")
        assert_true(recovery_payload["authenticated"] is True, "Recovery login should authenticate on the correct password.")

        forgetful_verdict = client.get("/api/verdicts/alice").json()
        assert_true(forgetful_verdict["verdict"] == "FORGETFUL_USER", "Recovery flow should resolve to FORGETFUL_USER.")
        print("[PASS] Wrong-password recovery path lands in the forgetful-user branch.")

        print("\n>>> CHECKPOINT 11C: Suspicious transfer review flow <<<")
        session_id = "portal-suspicious-transfer"
        post_behavioral(client, "normal1@novatrust.com", session_id, "/login")
        login = client.post(
            "/api/bank/login",
            json={
                "email": "normal1@novatrust.com",
                "password": "password123",
                "session_id": session_id,
                "source_ip": "127.0.0.1",
            },
        ).json()
        suspicious_transfer = client.post(
            "/api/bank/transfer",
            json={
                "user_id": login["user_id"],
                "session_id": session_id,
                "source_ip": "203.0.113.61",
                "destination": "Treasury Reserve acct-8891",
                "amount": 25000.0,
                "memo": "Treasury review settlement",
            },
        )
        suspicious_payload = suspicious_transfer.json()
        assert_true(suspicious_transfer.status_code == 200, "Suspicious transfer call should succeed.")
        assert_true(suspicious_payload["status"] == "suspicious", "High-value transfer should stay in manual review.")
        assert_true(suspicious_payload["sandbox"] is None, "Suspicious review should not force sandbox by itself.")
        assert_true(suspicious_payload["verdict"] == "FORGETFUL_USER", "High-value transfer should promote a non-hacker suspicious verdict.")
        print("[PASS] Suspicious transfer flow is distinct from the hard sandbox branch.")

        print("\n>>> CHECKPOINT 11D: Honeypot escalation and replay <<<")
        honeypot_response = client.post(
            "/api/bank/honeypot-hit",
            json={
                "source": "system-flow",
                "user_id": "intruder-demo",
                "session_id": "portal-honeypot-flow",
                "source_ip": "203.0.113.77",
            },
        )
        honeypot_payload = honeypot_response.json()
        assert_true(honeypot_response.status_code == 200, "Honeypot route should succeed.")
        assert_true(honeypot_payload["verdict"] == "HACKER", "Honeypot signals should escalate to HACKER.")
        assert_true(honeypot_payload["sandbox"]["active"] is True, "Honeypot route should activate sandbox mode.")
        assert_true(isinstance(honeypot_payload.get("confidence"), float), "Honeypot payload should expose confidence for the alert page.")

        replay_response = client.get("/api/sandbox/portal-honeypot-flow/replay")
        replay_payload = replay_response.json()
        assert_true(replay_response.status_code == 200, "Replay endpoint should succeed for sandbox sessions.")
        assert_true(len(replay_payload["actions"]) >= 1, "Replay should expose captured sandbox actions.")
        print("[PASS] Honeypot escalation carries confidence, sandbox state, and replay data.")

    print("\n[SUCCESS] Phase 11 bank portal flow checkpoints passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
