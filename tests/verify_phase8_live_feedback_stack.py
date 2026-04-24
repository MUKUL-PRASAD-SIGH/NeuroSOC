from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SESSION_ID = os.environ.get("LIVE_SESSION_ID", "live-feedback-demo")
INFERENCE_BASE_URL = os.environ.get("INFERENCE_BASE_URL", "http://127.0.0.1:8000")
SANDBOX_BASE_URL = os.environ.get("SANDBOX_BASE_URL", "http://127.0.0.1:8001")
SKIP_STACK_START = os.environ.get("SKIP_STACK_START", "").strip().lower() in {"1", "true", "yes"}


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(command)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def http_json(method: str, url: str, payload: dict | None = None, headers: dict[str, str] | None = None) -> dict:
    data = None
    merged_headers = {"Content-Type": "application/json"}
    if headers:
        merged_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=merged_headers, method=method)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_json(url: str, predicate, timeout_seconds: int = 180) -> dict:
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            payload = http_json("GET", url)
            if predicate(payload):
                return payload
        except Exception as exc:  # pragma: no cover - depends on service startup
            last_error = exc
        time.sleep(3)
    raise RuntimeError(f"Timed out waiting for {url}. Last error: {last_error}")


def postgres_scalar(sql: str) -> str:
    result = run(
        [
            "docker",
            "exec",
            "neuroshield-postgres",
            "psql",
            "-U",
            "ns_user",
            "-d",
            "neuroshield",
            "-t",
            "-A",
            "-c",
            sql,
        ]
    )
    return result.stdout.strip()


def kafka_feedback_contains(session_id: str, timeout_seconds: int = 30) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        result = run(
            [
                "docker",
                "exec",
                "neuroshield-kafka",
                "bash",
                "-lc",
                (
                    "kafka-console-consumer --bootstrap-server kafka:9092 "
                    "--topic feedback --from-beginning --timeout-ms 4000 "
                    f"| grep -F '\"session_id\": \"{session_id}\"'"
                ),
            ],
            check=False,
        )
        if result.returncode == 0 and session_id in result.stdout:
            return True
        time.sleep(3)
    return False


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print("=========================================================")
    print("[TEST] PHASE 8 LIVE FEEDBACK STACK")
    print("=========================================================\n")

    if not SKIP_STACK_START:
        print(">>> STEP 1: Build and start live services <<<")
        run(
            [
                "docker",
                "compose",
                "--profile",
                "phase8plus",
                "--profile",
                "phase10plus",
                "up",
                "-d",
                "--build",
                "postgres",
                "kafka",
                "redis",
                "inference",
                "feedback",
                "sandbox",
            ]
        )
        print("[PASS] Containers launched.")
    else:
        print(">>> STEP 1: Using already-running live services <<<")
        print("[PASS] Stack startup skipped by SKIP_STACK_START.")

    print("\n>>> STEP 2: Wait for inference and sandbox health <<<")
    inference_health = wait_for_json(f"{INFERENCE_BASE_URL}/health", lambda payload: payload.get("status") == "ok")
    sandbox_health = wait_for_json(f"{SANDBOX_BASE_URL}/health", lambda payload: payload.get("status") == "ok")
    assert_true(inference_health["status"] == "ok", "Inference service did not become healthy.")
    assert_true(sandbox_health["status"] == "ok", "Sandbox service did not become healthy.")
    print("[PASS] Live services are healthy.")

    print("\n>>> STEP 3: Send a live inference verdict <<<")
    analyze_payload = {
        "session_id": SESSION_ID,
        "user_id": "attacker-demo",
        "source_ip": "198.51.100.77",
        "flow_features": [16000.0 if idx == 2 else 0.98 if idx == 76 else 70.0 if idx == 31 else 0.1 for idx in range(80)],
        "behavioral_vector": [900.0, 200.0] + [5.0] * 18,
        "unique_dst_ports": 1200,
        "login_attempts": 80,
        "all_different_passwords": True,
    }
    verdict = http_json("POST", f"{INFERENCE_BASE_URL}/analyze", analyze_payload)
    assert_true(verdict["session_id"] == SESSION_ID, "Inference response session_id mismatch.")
    verdict_row = postgres_scalar(f"SELECT verdict FROM verdicts WHERE session_id = '{SESSION_ID}' ORDER BY id DESC LIMIT 1;")
    assert_true(bool(verdict_row), "Verdict was not persisted to PostgreSQL.")
    print(f"[PASS] Inference produced and persisted verdict: {verdict_row}")

    print("\n>>> STEP 4: Create sandbox session and simulate attacker actions <<<")
    session = http_json(
        "POST",
        f"{SANDBOX_BASE_URL}/sessions",
        {"session_id": SESSION_ID, "user_id": "attacker-demo", "source_ip": "198.51.100.77"},
    )
    sandbox_token = session["sandbox_token"]
    headers = {"X-Sandbox-Token": sandbox_token}
    for index in range(12):
        login_payload = {
            "username": "alice",
            "password": f"guess-{index}",
            "flow_features": [0.2] * 80 if index == 0 else None,
        }
        http_json("POST", f"{SANDBOX_BASE_URL}/login", login_payload, headers=headers)
    http_json(
        "POST",
        f"{SANDBOX_BASE_URL}/sessions/" + sandbox_token + "/terminate",
        {},
    )
    action_count = postgres_scalar(f"SELECT COUNT(*) FROM sandbox_actions WHERE session_id = '{SESSION_ID}';")
    assert_true(int(action_count) >= 12, "Sandbox actions were not persisted correctly.")
    print("[PASS] Sandbox actions were recorded and the session was terminated.")

    print("\n>>> STEP 5: Wait for feedback labeling <<<")
    deadline = time.time() + 90
    assigned_label = ""
    while time.time() < deadline:
        assigned_label = postgres_scalar(
            f"SELECT label FROM labeled_training_data WHERE session_id = '{SESSION_ID}' ORDER BY id DESC LIMIT 1;"
        )
        if assigned_label:
            break
        time.sleep(5)
    assert_true(assigned_label == "BRUTE_FORCE", f"Expected BRUTE_FORCE feedback label, got: {assigned_label!r}")
    print("[PASS] Feedback service labeled and stored the sandbox session.")

    print("\n>>> STEP 6: Confirm feedback Kafka publication <<<")
    assert_true(
        kafka_feedback_contains(SESSION_ID, timeout_seconds=30),
        "Feedback Kafka topic did not contain the labeled session.",
    )
    print("[PASS] Feedback Kafka topic contains the labeled session.")

    print("\n[SUCCESS] Live Phase 8 feedback stack verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
