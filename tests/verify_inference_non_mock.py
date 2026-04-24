from __future__ import annotations

import os
import sys
import time
from typing import Any

import requests


BASE_URL = os.getenv("INFERENCE_URL", "http://localhost:8000")
ANALYZE_URL = f"{BASE_URL}/analyze"
HEALTH_URL = f"{BASE_URL}/health"
TIMEOUT = 15


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def flow_vector(base: float) -> list[float]:
    return [float(base)] * 80


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(ANALYZE_URL, json=payload, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def main() -> int:
    print("=========================================================")
    print("[TEST] NON-MOCK INFERENCE BEHAVIOR CHECK")
    print("=========================================================\n")

    health = requests.get(HEALTH_URL, timeout=TIMEOUT).json()
    assert_true(health.get("status") == "ok", "Inference health endpoint is not healthy.")
    print(f"[INFO] Inference healthy. model_version={health.get('model_version')}")

    benign_payload = {
        "session_id": f"nonmock-benign-{int(time.time())}",
        "user_id": "probe-benign-user",
        "source_ip": "198.51.100.10",
        "flow_features": flow_vector(0.01),
        "behavioral_events": [{"type": "mousemove", "timestamp": time.time(), "x": 5, "y": 5}],
        "login_attempts": 1,
        "unique_dst_ports": 1,
        "all_different_passwords": False,
        "sql_injection_detected": False,
    }

    suspicious_payload = {
        "session_id": f"nonmock-suspicious-{int(time.time())}",
        "user_id": "probe-suspicious-user",
        "source_ip": "198.51.100.20",
        "flow_features": flow_vector(0.35),
        "behavioral_events": [{"type": "keydown", "timestamp": time.time(), "key": "a"}],
        "login_attempts": 12,
        "unique_dst_ports": 100,
        "all_different_passwords": True,
        "sql_injection_detected": False,
    }

    malicious_payload = {
        "session_id": f"nonmock-malicious-{int(time.time())}",
        "user_id": "probe-malicious-user",
        "source_ip": "198.51.100.30",
        "flow_features": flow_vector(0.95),
        "behavioral_events": [{"type": "submit", "timestamp": time.time(), "target": "login_form"}],
        "login_attempts": 80,
        "unique_dst_ports": 1200,
        "all_different_passwords": True,
        "sql_injection_detected": True,
    }

    benign = analyze(benign_payload)
    suspicious = analyze(suspicious_payload)
    malicious = analyze(malicious_payload)

    print("[INFO] Verdicts:")
    print(f"  benign     -> verdict={benign['verdict']}, confidence={benign['confidence']:.4f}")
    print(f"  suspicious -> verdict={suspicious['verdict']}, confidence={suspicious['confidence']:.4f}")
    print(f"  malicious  -> verdict={malicious['verdict']}, confidence={malicious['confidence']:.4f}")

    confidences = [float(benign["confidence"]), float(suspicious["confidence"]), float(malicious["confidence"])]
    verdicts = [str(benign["verdict"]), str(suspicious["verdict"]), str(malicious["verdict"])]

    unique_confidences = len({round(value, 6) for value in confidences})
    unique_verdicts = len(set(verdicts))

    assert_true(unique_confidences >= 2, "Confidence outputs are constant; inference may be mocked.")
    assert_true(unique_verdicts >= 2, "Verdict outputs are constant; inference may be mocked.")
    assert_true(confidences[2] > confidences[0], "Malicious input did not increase confidence over benign input.")
    assert_true((confidences[2] - confidences[0]) >= 0.20, "Confidence delta is too small for distinct benign/malicious probes.")

    sweep_results: list[float] = []
    for attempts in (1, 5, 20, 60):
        payload = {
            "session_id": f"nonmock-sweep-{attempts}-{int(time.time() * 1000)}",
            "user_id": f"probe-sweep-{attempts}",
            "source_ip": "203.0.113.50",
            "flow_features": flow_vector(0.15),
            "behavioral_events": [],
            "login_attempts": attempts,
            "unique_dst_ports": attempts * 2,
            "all_different_passwords": attempts > 10,
            "sql_injection_detected": False,
        }
        result = analyze(payload)
        sweep_results.append(float(result["confidence"]))

    print(f"[INFO] Confidence sweep by login_attempts [1,5,20,60]: {[round(v, 4) for v in sweep_results]}")
    assert_true(
        len({round(value, 6) for value in sweep_results}) >= 2,
        "Confidence sweep produced identical values for varying inputs; behavior looks mocked.",
    )

    print("\n[SUCCESS] Inference outputs are input-dependent and not constant mock values.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.RequestException as exc:
        print(f"[FAIL] Could not reach inference endpoint at {BASE_URL}: {exc}")
        raise SystemExit(1)
    except AssertionError as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1)
