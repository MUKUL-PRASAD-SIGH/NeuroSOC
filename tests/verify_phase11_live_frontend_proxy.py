from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_BASE_URL = os.environ.get("DASHBOARD_BASE_URL", "http://127.0.0.1:3000")
PORTAL_BASE_URL = os.environ.get("PORTAL_BASE_URL", "http://127.0.0.1:3001")
SANDBOX_BASE_URL = os.environ.get("SANDBOX_BASE_URL", "http://127.0.0.1:8001")
SKIP_STACK_START = os.environ.get("SKIP_STACK_START", "").strip().lower() in {"1", "true", "yes"}


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(command)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def http_request(method: str, url: str, payload: dict | None = None, headers: dict[str, str] | None = None):
    request_headers = dict(headers or {})
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read()
        response_headers = dict(response.headers.items())
        content_type = response_headers.get("Content-Type", "")
        if "application/json" in content_type:
            return json.loads(body.decode("utf-8")), response_headers
        return body.decode("utf-8"), response_headers


def wait_for(url: str, predicate, timeout_seconds: int = 180):
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            payload, headers = http_request("GET", url)
            if predicate(payload, headers):
                return payload, headers
        except Exception as exc:  # pragma: no cover - depends on container startup
            last_error = exc
        time.sleep(3)
    raise RuntimeError(f"Timed out waiting for {url}. Last error: {last_error}")


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print("=========================================================")
    print("[TEST] PHASE 11 LIVE FRONTEND PROXY + REAL SANDBOX")
    print("=========================================================\n")

    if not SKIP_STACK_START:
        print(">>> STEP 1: Build and start dashboard, portal, inference, and sandbox <<<")
        run(
            [
                "docker",
                "compose",
                "--profile",
                "phase8plus",
                "--profile",
                "phase10plus",
                "--profile",
                "phase11plus",
                "up",
                "-d",
                "--build",
                "postgres",
                "kafka",
                "redis",
                "inference",
                "feedback",
                "retraining",
                "sandbox",
                "dashboard",
                "simulation_portal",
            ]
        )
        print("[PASS] Containers launched.")
    else:
        print(">>> STEP 1: Using already-running live containers <<<")
        print("[PASS] Stack startup skipped by SKIP_STACK_START.")

    print("\n>>> STEP 2: Wait for dashboard and portal to serve the built apps <<<")
    dashboard_html, _ = wait_for(
        f"{DASHBOARD_BASE_URL}/",
        lambda payload, _headers: isinstance(payload, str) and "<div id=\"root\"></div>" in payload,
    )
    portal_html, _ = wait_for(
        f"{PORTAL_BASE_URL}/",
        lambda payload, _headers: isinstance(payload, str) and "<div id=\"root\"></div>" in payload,
    )
    assert_true("root" in dashboard_html, "Dashboard container should serve the built React app.")
    assert_true("root" in portal_html, "Simulation portal container should serve the built React app.")
    print("[PASS] Frontend containers are serving built assets.")

    print("\n>>> STEP 3: Verify dashboard proxies backend analyst APIs <<<")
    dashboard_model, _ = wait_for(
        f"{DASHBOARD_BASE_URL}/api/model/version",
        lambda payload, _headers: isinstance(payload, dict) and "version" in payload,
    )
    dashboard_alerts, _ = http_request("GET", f"{DASHBOARD_BASE_URL}/api/alerts")
    assert_true(isinstance(dashboard_model, dict), "Dashboard /api/model/version should proxy to inference JSON.")
    assert_true(isinstance(dashboard_alerts, list), "Dashboard /api/alerts should proxy to inference JSON list.")
    print("[PASS] Dashboard container proxies backend model and alert APIs.")

    print("\n>>> STEP 4: Trigger a live sandbox session through the portal-facing API <<<")
    session_id = f"portal-live-{int(time.time())}"
    honeypot_payload = {
        "source": "live-portal-check",
        "user_id": "portal-check-user",
        "session_id": session_id,
        "source_ip": "203.0.113.55",
    }
    honeypot_response, _ = http_request("POST", f"{PORTAL_BASE_URL}/api/bank/honeypot-hit", honeypot_payload)
    assert_true(honeypot_response["sandbox"]["active"] is True, "Portal API should activate sandboxing.")
    assert_true(honeypot_response["sandbox"]["mode"] == "live", "Portal API should reach the live sandbox service.")
    sandbox_token = honeypot_response["sandbox"]["sandboxToken"]
    assert_true(bool(sandbox_token), "Live sandbox token should be returned through the portal API.")
    print("[PASS] Portal API creates real sandbox sessions via inference.")

    print("\n>>> STEP 5: Record a real sandbox action and fetch replay back through the portal proxy <<<")
    _, sandbox_headers = http_request(
        "GET",
        f"{SANDBOX_BASE_URL}/api/internal/user-export",
        headers={"X-Sandbox-Token": sandbox_token, "Accept": "application/json"},
    )
    assert_true(isinstance(sandbox_headers, dict), "Sandbox action request should succeed.")
    replay_payload, _ = wait_for(
        f"{PORTAL_BASE_URL}/api/sandbox/{session_id}/replay",
        lambda payload, _headers: isinstance(payload, dict) and len(payload.get("actions", [])) > 0,
    )
    assert_true(
        any(action.get("path") == "/api/internal/user-export" for action in replay_payload["actions"]),
        "Replay should include the sandbox-side action triggered against the live honeypot.",
    )
    print("[PASS] Portal replay flows back from the live sandbox through inference.")

    print("\n>>> STEP 6: Verify the portal proxy now reports live sandbox state <<<")
    current_verdict, _ = wait_for(
        f"{PORTAL_BASE_URL}/api/verdicts/current",
        lambda payload, _headers: isinstance(payload, dict) and payload.get("sandbox", {}).get("active") is True,
    )
    assert_true(
        isinstance(current_verdict, dict) and current_verdict.get("sandbox", {}).get("active") is True,
        "Portal /api/verdicts/current should report an active sandbox session after the honeypot flow.",
    )
    print("[PASS] Portal proxy reports live sandbox state for the active session.")

    print("\n[SUCCESS] Phase 11 live frontend proxy and real sandbox verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
