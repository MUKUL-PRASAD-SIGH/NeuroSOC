from __future__ import annotations

import json
import importlib.util
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

import uvicorn
from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = REPO_ROOT / "models"

os.environ.setdefault("MODEL_PATH", str(MODELS_DIR))
os.environ.setdefault("MODEL_VERSION_FILE", str(MODELS_DIR / "model_version.json"))
os.environ.setdefault("FEATURE_COLUMNS_PATH", str(REPO_ROOT / "data" / "feature_columns.txt"))

sys.path.insert(0, str(REPO_ROOT / "inference-service"))
import main as inference_main
from core.behavioral.profiler import BehavioralProfiler


def load_sandbox_module():
    module_path = REPO_ROOT / "sandbox-service" / "main.py"
    module_name = "neuroshield_sandbox_main"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load sandbox-service/main.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


sandbox_main = load_sandbox_module()


class FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict]] = []

    def send(self, topic: str, payload: dict) -> None:
        self.sent.append((topic, payload))

    def flush(self, timeout: float | None = None) -> None:
        return None

    def close(self, timeout: float | None = None) -> None:
        return None


class FakeSandboxRepository:
    def __init__(self) -> None:
        self.sessions: dict[str, dict] = {}
        self.actions: list[dict] = []
        self.hits: list[dict] = []

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
        if session is None:
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
                "timestamp": time.time(),
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
        if session is None:
            return None
        session["ended_at"] = "ended"
        return session

    def expired_tokens(self, timeout_seconds: int) -> list[str]:
        return []

    def list_session_actions(self, sandbox_token: str) -> list[dict]:
        return [action for action in self.actions if action["sandbox_token"] == sandbox_token]


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_http(url: str, timeout: float = 10.0) -> None:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError(f"Timed out waiting for {url}")


def start_sandbox_server() -> tuple[uvicorn.Server, threading.Thread, FakeSandboxRepository, FakeProducer, str]:
    fake_repository = FakeSandboxRepository()
    fake_producer = FakeProducer()

    original_repository = sandbox_main.manager.repository
    original_producer = sandbox_main.manager._producer
    sandbox_main.manager.repository = fake_repository
    sandbox_main.manager._producer = fake_producer

    port = free_port()
    config = uvicorn.Config(sandbox_main.app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    def run_server() -> None:
        try:
            server.run()
        finally:
            sandbox_main.manager.repository = original_repository
            sandbox_main.manager._producer = original_producer

    thread = threading.Thread(target=run_server, name="sandbox-http-test", daemon=True)
    thread.start()
    wait_for_http(f"http://127.0.0.1:{port}/health")
    return server, thread, fake_repository, fake_producer, f"http://127.0.0.1:{port}"


def prepare_inference(temp_dir: str, sandbox_base_url: str) -> TestClient:
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

    inference_main.runtime.start = lambda: None
    inference_main.runtime.stop = lambda: None
    inference_main.runtime._ensure_producer = lambda: None
    inference_main.runtime._producer = None
    inference_main.runtime._latest_verdicts.clear()
    inference_main.runtime._latest_alerts.clear()
    inference_main.runtime._processed_messages = 0
    inference_main.runtime.engine.model_version_path = version_path
    inference_main.runtime.engine.current_model_version = "0.9.0"
    inference_main.runtime.engine.current_validation_f1 = {"snn": 0.91, "lnn": 0.89, "xgb": 0.94}
    inference_main.runtime.engine.behavioral_profiler = BehavioralProfiler(storage_dir=behavior_dir, database_url=None)
    inference_main.portal_state = inference_main.PortalState()
    inference_main.sandbox_gateway = inference_main.SandboxGateway(sandbox_base_url)
    inference_main.API_KEY = ""
    return TestClient(inference_main.app)


def main() -> int:
    print("=========================================================")
    print("[TEST] PHASE 9 LIVE HTTP SANDBOX FLOW")
    print("=========================================================\n")

    server, thread, fake_repository, _fake_producer, sandbox_base_url = start_sandbox_server()
    try:
        with tempfile.TemporaryDirectory(prefix="neuroshield-phase9-http-") as temp_dir:
            client = prepare_inference(temp_dir, sandbox_base_url)

            print(">>> CHECKPOINT 9H-A: Gateway creates a real sandbox session over HTTP <<<")
            response = client.post(
                "/api/bank/honeypot-hit",
                json={
                    "source": "login_form",
                    "user_id": "alice",
                    "session_id": "portal-http-live",
                    "source_ip": "127.0.0.1",
                },
            )
            payload = response.json()
            assert_true(response.status_code == 200, "Honeypot route should succeed.")
            assert_true(payload["sandbox"]["mode"] == "live", "Gateway should switch to live sandbox mode when HTTP sandbox is reachable.")
            sandbox_token = payload["sandbox"]["sandboxToken"]
            assert_true(sandbox_token == "sbx-portal-http-live", "Sandbox token should come from the live sandbox service.")
            assert_true(sandbox_token in fake_repository.sessions, "Sandbox service should receive the create-session call.")
            print("[PASS] Inference gateway creates sandbox sessions through the live HTTP sandbox service.")

            print("\n>>> CHECKPOINT 9H-B: Sandbox replay is fetched through the live HTTP hop <<<")
            import urllib.request

            req = urllib.request.Request(
                f"{sandbox_base_url}/api/internal/user-export",
                headers={"X-Sandbox-Token": sandbox_token, "accept": "application/json"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as remote_response:
                assert_true(remote_response.status == 200, "Live sandbox endpoint should accept the sandbox token.")

            replay_response = client.get("/api/sandbox/portal-http-live/replay")
            replay_payload = replay_response.json()
            assert_true(replay_response.status_code == 200, "Replay bridge should succeed.")
            assert_true(any(action["path"] == "/api/internal/user-export" for action in replay_payload["actions"]), "Replay should come back from the live sandbox service with sandbox-side actions.")
            print("[PASS] Replay is retrieved from the live sandbox HTTP service, not the placeholder cache.")

    finally:
        server.should_exit = True
        thread.join(timeout=10)

    print("\n[SUCCESS] Phase 9 live HTTP sandbox flow checkpoints passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
