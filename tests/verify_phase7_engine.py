from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "inference-service"))

from core.behavioral.profiler import BehavioralProfiler
from core.behavioral.signals import (
    extract_dwell_times,
    extract_mouse_curvature,
    extract_mouse_velocity,
    extract_session_vector,
    extract_typing_rhythm,
)
from core.engine import DecisionEngine


class StaticSNN:
    def __init__(self, score: float) -> None:
        self.score = float(score)

    def anomaly_score(self, _: np.ndarray) -> np.ndarray:
        return np.asarray([self.score], dtype=np.float32)


class StaticProbModel:
    def __init__(self, probabilities: list[float]) -> None:
        self.probabilities = np.asarray(probabilities, dtype=np.float32)

    def predict_proba(self, _: np.ndarray) -> np.ndarray:
        return self.probabilities.copy()


class StaticXGB:
    def __init__(self, probabilities: list[float]) -> None:
        self.probabilities = np.asarray([probabilities], dtype=np.float32)

    def predict_proba(self, _: np.ndarray) -> np.ndarray:
        return self.probabilities.copy()


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def build_behavioral_events() -> list[dict]:
    return [
        {"type": "pagevisit", "timestamp": 1.0, "page": "/login"},
        {"type": "keydown", "timestamp": 1.10, "key": "a", "page": "/login"},
        {"type": "keyup", "timestamp": 1.16, "key": "a", "page": "/login"},
        {"type": "keydown", "timestamp": 1.24, "key": "space", "page": "/login"},
        {"type": "keyup", "timestamp": 1.28, "key": "space", "page": "/login"},
        {"type": "keydown", "timestamp": 1.36, "key": "b", "page": "/login"},
        {"type": "keyup", "timestamp": 1.41, "key": "b", "page": "/login"},
        {"type": "mousemove", "timestamp": 1.45, "x": 0, "y": 0, "page": "/login"},
        {"type": "mousemove", "timestamp": 1.50, "x": 30, "y": 10, "page": "/login"},
        {"type": "mousemove", "timestamp": 1.58, "x": 65, "y": 28, "page": "/login"},
        {"type": "click", "timestamp": 1.70, "x": 65, "y": 28, "page": "/login"},
        {"type": "scroll", "timestamp": 1.82, "y": 140, "page": "/dashboard"},
        {"type": "pagevisit", "timestamp": 2.10, "page": "/dashboard"},
    ]


def verify_signal_extractors() -> None:
    print(">>> CHECKPOINT 7A: Behavioral signal extraction <<<")
    events = build_behavioral_events()
    typing = extract_typing_rhythm(events)
    dwell = extract_dwell_times(events)
    velocity = extract_mouse_velocity(events)
    curvature = extract_mouse_curvature(events)
    session_vector = extract_session_vector(events)

    assert_true(typing.size >= 2, "Typing rhythm extraction should find at least two intervals.")
    assert_true(dwell.size >= 2, "Dwell time extraction should find at least two key dwell values.")
    assert_true(velocity.size >= 2, "Mouse velocity extraction should find at least two movement velocities.")
    assert_true(curvature.size >= 1, "Mouse curvature extraction should find at least one turn angle.")
    assert_true(session_vector.shape == (20,), "Session vector must be exactly 20-dimensional.")
    print("[PASS] Signal extraction produced a valid 20-dimensional behavioral session vector.")


def verify_profiler_roundtrip() -> None:
    print("\n>>> CHECKPOINT 7B: Behavioral profiler persistence + delta <<<")
    with tempfile.TemporaryDirectory(prefix="neuroshield-phase7-profiler-") as temp_dir:
        profiler = BehavioralProfiler(storage_dir=temp_dir)
        baseline = extract_session_vector(build_behavioral_events())
        drifted = baseline.copy()
        drifted[0] += 400.0
        drifted[4] += 2.0

        profiler.update_profile("alice", baseline)
        loaded = profiler.load_profile("alice")
        assert_true(loaded is not None, "Profile should load after being saved.")

        same_delta = profiler.compute_delta("alice", baseline)
        drift_delta = profiler.compute_delta("alice", drifted)
        assert_true(drift_delta > same_delta, "A drifted session should score farther from the baseline.")
        assert_true(profiler.classify_delta(0.2) == "LEGITIMATE", "Low deltas should classify as LEGITIMATE.")
        assert_true(profiler.classify_delta(0.5) == "FORGETFUL_USER", "Mid deltas should classify as FORGETFUL_USER.")
        assert_true(profiler.classify_delta(0.8) == "HACKER", "High deltas should classify as HACKER.")
        print("[PASS] Behavioral profiler saves, reloads, and separates baseline vs drifted sessions.")


def verify_decision_engine() -> None:
    print("\n>>> CHECKPOINT 7C: Decision fusion + Kafka publishing <<<")
    published: list[tuple[str, dict]] = []

    def publisher(topic: str, payload: dict) -> None:
        published.append((topic, payload))

    with tempfile.TemporaryDirectory(prefix="neuroshield-phase7-engine-") as temp_dir:
        version_path = Path(temp_dir) / "model_version.json"
        version_path.write_text(
            json.dumps(
                {
                    "version": "0.0.1",
                    "snn": None,
                    "lnn": None,
                    "xgb": None,
                    "validation_f1": {"snn": 0.91, "lnn": 0.89, "xgb": 0.93},
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        profiler = BehavioralProfiler(storage_dir=Path(temp_dir) / "profiles")
        normal_engine = DecisionEngine(
            model_version_path=version_path,
            behavioral_profiler=profiler,
            publish_callback=publisher,
            snn_model=StaticSNN(0.05),
            lnn_classifier=StaticProbModel([0.95, 0.01, 0.01, 0.01, 0.01, 0.005, 0.005]),
            xgb_model=StaticXGB([0.92, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01]),
        )

        normal_verdict = normal_engine.analyze_session(
            {
                "session_id": "normal-1",
                "user_id": "alice",
                "source_ip": "10.0.0.10",
                "flow_features": [0.05] * 80,
                "behavioral_events": build_behavioral_events(),
            }
        )
        assert_true(normal_verdict.verdict == "LEGITIMATE", "Normal session should remain LEGITIMATE.")
        assert_true(normal_verdict.confidence < 0.30, "Normal session confidence should stay below 0.30.")

        attack_engine = DecisionEngine(
            model_version_path=version_path,
            behavioral_profiler=BehavioralProfiler(storage_dir=Path(temp_dir) / "profiles-attack"),
            publish_callback=publisher,
            snn_model=StaticSNN(0.97),
            lnn_classifier=StaticProbModel([0.08, 0.86, 0.02, 0.01, 0.01, 0.01, 0.01]),
            xgb_model=StaticXGB([0.04, 0.91, 0.01, 0.01, 0.01, 0.01, 0.01]),
        )

        ddos_features = [0.10] * 80
        ddos_features[2] = 16000.0
        ddos_features[31] = 70.0
        ddos_features[76] = 0.98

        attack_verdict = attack_engine.analyze_session(
            {
                "session_id": "attack-1",
                "user_id": "intruder",
                "source_ip": "172.16.1.99",
                "flow_features": ddos_features,
                "behavioral_vector": np.asarray([900.0, 200.0] + [5.0] * 18, dtype=np.float32),
                "unique_dst_ports": 1200,
                "login_attempts": 80,
                "all_different_passwords": True,
            }
        )
        assert_true(attack_verdict.verdict == "HACKER", "Attack session should escalate to HACKER.")
        assert_true(attack_verdict.confidence > 0.80, "Attack session confidence should exceed 0.80.")
        assert_true(any(topic == "alerts" for topic, _ in published), "HACKER verdicts should publish an alert.")
        assert_true(sum(1 for topic, _ in published if topic == "verdicts") >= 2, "Verdicts should be published for both sessions.")

        version_path.write_text(
            json.dumps(
                {
                    "version": "0.0.2",
                    "snn": None,
                    "lnn": None,
                    "xgb": None,
                    "validation_f1": {"snn": 0.91, "lnn": 0.89, "xgb": 0.70},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        swapped = attack_engine.check_model_version()
        assert_true(swapped is False, "Hot-swap should reject regressed validation metrics.")
        assert_true(attack_engine.current_model_version == "0.0.1", "Rejected hot-swap must keep the previous version active.")
        print("[PASS] DecisionEngine fuses signals correctly, publishes Kafka-style events, and blocks regressed hot-swaps.")


def main() -> int:
    print("=========================================================")
    print("[TEST] PHASE 7: BEHAVIORAL PROFILER + DECISION ENGINE")
    print("=========================================================\n")
    verify_signal_extractors()
    verify_profiler_roundtrip()
    verify_decision_engine()
    print("\n[SUCCESS] Phase 7 checkpoints passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
