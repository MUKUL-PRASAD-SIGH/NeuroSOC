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


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    print("=========================================================")
    print("[TEST] PHASE 7 LIVE INFERENCE SERVICE")
    print("=========================================================\n")

    inference_main.runtime.start = lambda: None
    inference_main.runtime.stop = lambda: None
    inference_main.runtime._ensure_producer = lambda: None
    inference_main.runtime._producer = None

    with tempfile.TemporaryDirectory(prefix="neuroshield-phase7-live-") as temp_dir:
        version_path = Path(temp_dir) / "model_version.json"
        version_path.write_text(
            json.dumps(
                {
                    "version": "0.0.1",
                    "snn": None,
                    "lnn": None,
                    "xgb": None,
                    "validation_f1": {"snn": None, "lnn": None, "xgb": None},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        inference_main.runtime.engine.model_version_path = version_path
        inference_main.runtime.engine.current_model_version = "0.0.1"
        inference_main.runtime.engine.current_validation_f1 = {"snn": None, "lnn": None, "xgb": None}

        client = TestClient(inference_main.app)

        print(">>> CHECKPOINT 7L-A: Health endpoint <<<")
        health_response = client.get("/health")
        assert_true(health_response.status_code == 200, "Health endpoint should return HTTP 200.")
        health_payload = health_response.json()
        assert_true(health_payload["status"] == "ok", "Health endpoint should report ok status.")
        print("[PASS] /health is live.")

        print("\n>>> CHECKPOINT 7L-B: Behavioral vectorization <<<")
        vector_response = client.post(
            "/behavioral/vectorize",
            json={
                "events": [
                    {"type": "pagevisit", "timestamp": 1.0, "page": "/login"},
                    {"type": "keydown", "timestamp": 1.1, "key": "a"},
                    {"type": "keyup", "timestamp": 1.2, "key": "a"},
                    {"type": "mousemove", "timestamp": 1.3, "x": 0, "y": 0},
                    {"type": "mousemove", "timestamp": 1.4, "x": 10, "y": 10},
                ]
            },
        )
        assert_true(vector_response.status_code == 200, "Behavioral vectorization endpoint should return HTTP 200.")
        assert_true(len(vector_response.json()["vector"]) == 20, "Behavioral vector endpoint must return 20 values.")
        print("[PASS] /behavioral/vectorize returns the expected 20-dimensional vector.")

        print("\n>>> CHECKPOINT 7L-C: Manual session analysis <<<")
        analyze_response = client.post(
            "/analyze",
            json={
                "session_id": "manual-normal",
                "user_id": "alice",
                "source_ip": "10.0.0.10",
                "flow_features": [0.05] * 80,
                "behavioral_events": [
                    {"type": "pagevisit", "timestamp": 1.0, "page": "/login"},
                    {"type": "keydown", "timestamp": 1.1, "key": "a"},
                    {"type": "keyup", "timestamp": 1.18, "key": "a"},
                ],
            },
        )
        assert_true(analyze_response.status_code == 200, "Analyze endpoint should return HTTP 200.")
        analyze_payload = analyze_response.json()
        assert_true(analyze_payload["verdict"] in {"LEGITIMATE", "FORGETFUL_USER", "HACKER", "INCONCLUSIVE"}, "Analyze endpoint should return a verdict.")
        latest_response = client.get("/verdicts/latest")
        assert_true(latest_response.status_code == 200, "Latest verdicts endpoint should return HTTP 200.")
        assert_true(len(latest_response.json()["items"]) >= 1, "Latest verdicts should include the manual analysis result.")
        print("[PASS] /analyze produces verdicts and /verdicts/latest exposes them.")

        print("\n>>> CHECKPOINT 7L-D: Kafka-path feature message handling <<<")
        verdict = inference_main.runtime._handle_feature_message(
            {
                "flow_id": "stream-ddos",
                "src_ip": "172.16.1.44",
                "dst_ip": "10.0.0.2",
                "timestamp": 1234.5,
                "features": [0.1] * 80,
            }
        )
        assert_true(hasattr(verdict, "verdict"), "Kafka feature path should produce a ThreatVerdict.")
        print("[PASS] Runtime can process feature-engine messages directly.")

    print("\n[SUCCESS] Phase 7 live service checkpoints passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
