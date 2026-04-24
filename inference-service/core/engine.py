from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import torch

try:
    from kafka import KafkaProducer
except ImportError:  # pragma: no cover - optional in local smoke environments
    KafkaProducer = None

from core.behavioral.profiler import BehavioralProfiler
from core.behavioral.signals import extract_session_vector
from core.lnn.classifier import LNNClassifier
from core.lnn.reservoir import LiquidReservoir
from core.snn.encoder import SpikeEncoder
from core.snn.network import CLASS_NAMES, SNNAnomalyDetector
from core.xgboost.model import XGBoostClassifier
from core.xgboost.tree_logic import OverrideResult, TreeLogicOverride


log = logging.getLogger(__name__)

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL_ROOT = Path(os.getenv("MODEL_PATH", "")).expanduser() if os.getenv("MODEL_PATH") else None
DEFAULT_MODEL_VERSION_PATH = (
    Path(os.getenv("MODEL_VERSION_FILE")).expanduser()
    if os.getenv("MODEL_VERSION_FILE")
    else (MODEL_ROOT / "model_version.json" if MODEL_ROOT else REPO_ROOT / "models" / "model_version.json")
)
DEFAULT_FEATURE_COLUMN_PATHS = tuple(
    candidate
    for candidate in (
        Path(os.getenv("FEATURE_COLUMNS_PATH")).expanduser() if os.getenv("FEATURE_COLUMNS_PATH") else None,
        Path("/data/feature_columns.txt"),
        REPO_ROOT / "data" / "feature_columns.txt",
        REPO_ROOT / "datasets" / "feature_columns.txt",
        SERVICE_ROOT / "data" / "feature_columns.txt",
        Path.cwd() / "data" / "feature_columns.txt",
    )
    if candidate is not None
)


@dataclass
class ThreatVerdict:
    session_id: str
    user_id: str
    source_ip: str
    snn_score: float
    lnn_class: str
    xgb_class: str
    behavioral_delta: float
    confidence: float
    verdict: str
    timestamp: float
    model_version: str
    features_dict: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class KafkaTopicPublisher:
    def __init__(self, bootstrap_servers: str) -> None:
        self.bootstrap_servers = bootstrap_servers
        self._producer = None
        if KafkaProducer is None:
            return
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda payload: json.dumps(payload).encode("utf-8"),
            )
        except Exception as exc:  # pragma: no cover - depends on Kafka availability
            log.warning("Kafka producer unavailable at %s: %s", bootstrap_servers, exc)

    def __call__(self, topic: str, payload: dict[str, Any]) -> None:
        if self._producer is None:
            return
        try:
            self._producer.send(topic, payload)
        except Exception as exc:  # pragma: no cover - depends on Kafka availability
            log.warning("Failed to publish to Kafka topic %s: %s", topic, exc)


class DecisionEngine:
    def __init__(
        self,
        model_version_path: str | Path = DEFAULT_MODEL_VERSION_PATH,
        snn_path: str | Path | None = None,
        lnn_path: str | Path | None = None,
        xgb_path: str | Path | None = None,
        behavioral_profiler: BehavioralProfiler | None = None,
        publish_callback: Callable[[str, dict[str, Any]], None] | None = None,
        kafka_bootstrap: str | None = None,
        device: str = "cpu",
        model_poll_interval_seconds: float = 60.0,
        start_model_monitor: bool = False,
        snn_model: Any | None = None,
        snn_encoder: SpikeEncoder | None = None,
        lnn_reservoir: Any | None = None,
        lnn_classifier: Any | None = None,
        xgb_model: Any | None = None,
        tree_logic: TreeLogicOverride | None = None,
    ) -> None:
        self.device = torch.device(device)
        self.model_version_path = Path(model_version_path)
        self.model_poll_interval_seconds = model_poll_interval_seconds
        self.feature_names = self._load_feature_names()
        self.behavioral_profiler = behavioral_profiler or BehavioralProfiler()
        self.tree_logic = tree_logic or TreeLogicOverride()
        self._lock = threading.RLock()
        self._monitor_stop = threading.Event()
        self._monitor_thread: threading.Thread | None = None

        self.snn_model = snn_model
        self.snn_encoder = snn_encoder
        self.lnn_reservoir = lnn_reservoir
        self.lnn_classifier = lnn_classifier
        self.xgb_model = xgb_model
        self.lnn_window_size = 20
        self._override_flags = {
            "snn": snn_model is not None,
            "lnn": lnn_classifier is not None,
            "xgb": xgb_model is not None,
        }

        self.publish_callback = publish_callback
        if self.publish_callback is None and kafka_bootstrap:
            self.publish_callback = KafkaTopicPublisher(kafka_bootstrap)

        payload = self._read_model_version()
        self.current_model_version = str(payload.get("version", "0.0.0"))
        self.current_validation_f1 = dict(payload.get("validation_f1", {}))

        if self.snn_model is None:
            resolved_snn_path = self._resolve_artifact_path(snn_path or payload.get("snn"))
            if resolved_snn_path is not None:
                self.snn_encoder, self.snn_model = self._load_snn_bundle(resolved_snn_path)

        if self.lnn_classifier is None:
            resolved_lnn_path = self._resolve_artifact_path(lnn_path or payload.get("lnn"))
            if resolved_lnn_path is not None:
                self.lnn_reservoir, self.lnn_classifier, self.lnn_window_size = self._load_lnn_bundle(resolved_lnn_path)

        if self.xgb_model is None:
            resolved_xgb_path = self._resolve_artifact_path(xgb_path or payload.get("xgb"))
            if resolved_xgb_path is not None:
                self.xgb_model = self._load_xgb_bundle(resolved_xgb_path)

        if start_model_monitor:
            self.start_model_monitor()

    def _load_feature_names(self) -> list[str]:
        for candidate in DEFAULT_FEATURE_COLUMN_PATHS:
            if candidate.exists():
                return [line.strip() for line in candidate.read_text(encoding="utf-8").splitlines() if line.strip()]
        return [f"feature_{index}" for index in range(80)]

    def _read_model_version(self) -> dict[str, Any]:
        if not self.model_version_path.exists():
            return {
                "version": "0.0.0",
                "snn": None,
                "lnn": None,
                "xgb": None,
                "validation_f1": {"snn": None, "lnn": None, "xgb": None},
            }
        return json.loads(self.model_version_path.read_text(encoding="utf-8-sig"))

    def _resolve_artifact_path(self, raw_path: str | Path | None) -> Path | None:
        if raw_path in (None, "", "null"):
            return None
        candidate = Path(raw_path)
        if candidate.is_absolute():
            return candidate if candidate.exists() else None
        anchored_to_version = (self.model_version_path.parent / candidate).resolve()
        if anchored_to_version.exists():
            return anchored_to_version
        anchored_to_repo = (REPO_ROOT / candidate).resolve()
        if anchored_to_repo.exists():
            return anchored_to_repo
        return None

    def _load_snn_bundle(self, checkpoint_path: Path) -> tuple[SpikeEncoder, SNNAnomalyDetector]:
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        config = checkpoint.get("config", {})
        input_size = int(config.get("input_size", 400))
        n_features = int(config.get("n_features", len(self.feature_names)))
        n_neurons_per_feature = max(1, input_size // max(n_features, 1))
        encoder = SpikeEncoder(
            n_features=n_features,
            n_neurons_per_feature=n_neurons_per_feature,
            T=int(config.get("timesteps", 100)),
        )
        model = SNNAnomalyDetector(
            input_size=input_size,
            hidden_sizes=list(config.get("hidden_sizes", [256, 128])),
            n_classes=int(config.get("n_classes", len(CLASS_NAMES))),
        ).to(self.device)
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()
        return encoder, model

    def _load_lnn_bundle(self, checkpoint_path: Path) -> tuple[LiquidReservoir, LNNClassifier, int]:
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        reservoir_config = dict(checkpoint["reservoir_config"])
        classifier_config = dict(checkpoint["classifier_config"])
        feature_names = reservoir_config.get("feature_names")
        if isinstance(feature_names, list) and feature_names:
            self.feature_names = feature_names
        reservoir = LiquidReservoir(
            input_size=int(reservoir_config.get("input_size", len(self.feature_names))),
            reservoir_size=int(reservoir_config.get("reservoir_size", 500)),
            spectral_radius=float(reservoir_config.get("spectral_radius", 0.9)),
            leak_rate=float(reservoir_config.get("leak_rate", 0.3)),
            sparsity=float(reservoir_config.get("sparsity", 0.1)),
            seed=int(reservoir_config.get("seed", 42)),
        ).to(self.device)
        reservoir.load_state_dict(checkpoint["reservoir_state"])
        reservoir.eval()
        classifier = LNNClassifier(
            reservoir_size=int(classifier_config.get("reservoir_size", reservoir.reservoir_size)),
            n_classes=int(classifier_config.get("n_classes", len(CLASS_NAMES))),
        ).to(self.device)
        classifier.load_state_dict(checkpoint["classifier_state"])
        classifier.eval()
        window_size = int(reservoir_config.get("window_size", 20))
        return reservoir, classifier, window_size

    def _load_xgb_bundle(self, checkpoint_path: Path) -> XGBoostClassifier:
        wrapper = XGBoostClassifier(feature_names=self.feature_names)
        wrapper.load(checkpoint_path)
        return wrapper

    def _coerce_feature_vector(self, raw_features: Any) -> np.ndarray:
        if isinstance(raw_features, dict) and "features" in raw_features:
            raw_features = raw_features["features"]
        if isinstance(raw_features, dict):
            vector = [float(raw_features.get(name, 0.0)) for name in self.feature_names]
            return np.asarray(vector, dtype=np.float32)
        array = np.asarray(raw_features, dtype=np.float32).reshape(-1)
        if array.shape[0] != len(self.feature_names):
            raise ValueError(f"Expected {len(self.feature_names)} flow features, got {array.shape[0]}.")
        return np.nan_to_num(array, copy=False)

    def _build_features_dict(self, feature_vector: np.ndarray, session_data: dict[str, Any]) -> dict[str, float]:
        feature_map = {
            name: float(feature_vector[index]) if index < len(feature_vector) else 0.0
            for index, name in enumerate(self.feature_names)
        }
        feature_map.setdefault("packet_rate", feature_map.get("flow_packets_per_s", 0.0))
        feature_map.setdefault("syn_ratio", feature_map.get("syn_ratio", 0.0))
        if "unique_dst_ports" in session_data:
            feature_map["unique_dst_ports"] = float(session_data.get("unique_dst_ports") or 0.0)
        if "login_attempts" in session_data:
            feature_map["login_attempts"] = float(session_data.get("login_attempts") or 0.0)
        if "all_different_passwords" in session_data:
            feature_map["all_different_passwords"] = bool(session_data.get("all_different_passwords") or False)
        if "sql_injection_detected" in session_data:
            feature_map["sql_injection_detected"] = bool(session_data.get("sql_injection_detected") or False)
        return feature_map

    def _build_session_sequence(self, feature_vector: np.ndarray, session_data: dict[str, Any]) -> np.ndarray:
        sequence = session_data.get("session_sequence") or session_data.get("flow_sequence")
        if sequence is None:
            return np.repeat(feature_vector.reshape(1, -1), self.lnn_window_size, axis=0)
        array = np.asarray(sequence, dtype=np.float32)
        if array.ndim == 1:
            return np.repeat(array.reshape(1, -1), self.lnn_window_size, axis=0)
        if array.ndim != 2:
            raise ValueError("session_sequence must be a 1D or 2D array.")
        if array.shape[1] != len(self.feature_names):
            raise ValueError(
                f"Expected session_sequence with feature width {len(self.feature_names)}, got {array.shape[1]}."
            )
        return array

    def _extract_behavioral_vector(self, session_data: dict[str, Any]) -> np.ndarray:
        if session_data.get("behavioral_vector") is not None:
            return np.asarray(session_data["behavioral_vector"], dtype=np.float32).reshape(-1)
        events = session_data.get("behavioral_events") or []
        return extract_session_vector(events)

    def _heuristic_class_probabilities(self, features_dict: dict[str, Any]) -> np.ndarray:
        packet_rate = float(features_dict.get("packet_rate", 0.0))
        syn_ratio = float(features_dict.get("syn_ratio", 0.0))
        login_attempts = float(features_dict.get("login_attempts", 0.0))
        unique_dst_ports = float(features_dict.get("unique_dst_ports", 0.0))
        sql_injection_detected = bool(features_dict.get("sql_injection_detected", False))
        all_different_passwords = bool(features_dict.get("all_different_passwords", False))
        ack_ratio = float(features_dict.get("ack_ratio", 0.0))
        rst_flag_count = float(features_dict.get("rst_flag_count", 0.0))

        ddos = np.clip(0.55 * min(packet_rate / 15000.0, 1.0) + 0.45 * min(max(syn_ratio, 0.0), 1.0), 0.0, 1.0)
        brute_force = np.clip(
            0.7 * min(login_attempts / 25.0, 1.0) + 0.3 * (1.0 if all_different_passwords else 0.0),
            0.0,
            1.0,
        )
        reconnaissance = np.clip(unique_dst_ports / 1000.0, 0.0, 1.0)
        web_attack = 0.92 if sql_injection_detected else np.clip((rst_flag_count + ack_ratio) / 10.0, 0.0, 0.45)
        bot = np.clip((packet_rate / 6000.0) * max(ack_ratio, 0.1), 0.0, 0.65)
        other = np.clip((rst_flag_count + feature_value(features_dict, "psh_flag_count")) / 20.0, 0.0, 0.55)

        suspiciousness = max(ddos, brute_force, reconnaissance, web_attack, bot, other)
        benign = np.clip(1.0 - suspiciousness, 0.05, 0.99)

        raw = np.asarray(
            [benign, ddos, brute_force, reconnaissance, web_attack, bot, other],
            dtype=np.float32,
        ) + 1e-3
        return raw / raw.sum()

    def _run_snn(self, feature_vector: np.ndarray, features_dict: dict[str, Any]) -> float:
        if self.snn_model is not None and hasattr(self.snn_model, "anomaly_score"):
            score = self.snn_model.anomaly_score(feature_vector.reshape(1, -1))
            return float(np.asarray(score).reshape(-1)[0])

        if self.snn_model is not None and self.snn_encoder is not None:
            tensor = torch.tensor(feature_vector.reshape(1, -1), dtype=torch.float32)
            spike_train = self.snn_encoder.encode_deterministic(tensor.numpy()).to(self.device)
            with torch.no_grad():
                _, anomaly_score = self.snn_model(spike_train)
            return float(anomaly_score.detach().cpu().numpy().reshape(-1)[0])

        heuristic_probs = self._heuristic_class_probabilities(features_dict)
        return float(1.0 - heuristic_probs[0])

    def _run_lnn(self, feature_vector: np.ndarray, session_data: dict[str, Any], features_dict: dict[str, Any]) -> tuple[str, float]:
        if self.lnn_reservoir is not None and self.lnn_classifier is not None:
            sequence = self._build_session_sequence(feature_vector, session_data)
            tensor = torch.tensor(sequence, dtype=torch.float32, device=self.device).unsqueeze(1)
            with torch.no_grad():
                states, _ = self.lnn_reservoir(tensor)
                probs = self.lnn_classifier.predict_proba(states).detach().cpu().numpy()[0]
            return self._label_and_threat_confidence(probs)

        if self.lnn_classifier is not None and hasattr(self.lnn_classifier, "predict_proba"):
            sequence = self._build_session_sequence(feature_vector, session_data)
            probs = np.asarray(self.lnn_classifier.predict_proba(sequence), dtype=np.float32).reshape(-1)
            return self._label_and_threat_confidence(probs)

        heuristic_probs = self._heuristic_class_probabilities(features_dict)
        return self._label_and_threat_confidence(heuristic_probs)

    def _run_xgb(self, feature_vector: np.ndarray, features_dict: dict[str, Any]) -> tuple[str, float]:
        probabilities: np.ndarray | None = None
        predicted_label = "BENIGN"
        threat_confidence = 0.0

        if self.xgb_model is not None:
            try:
                if hasattr(self.xgb_model, "predict_proba"):
                    probabilities = np.asarray(
                        self.xgb_model.predict_proba(feature_vector.reshape(1, -1)),
                        dtype=np.float32,
                    )[0]
                    predicted_label, threat_confidence = self._label_and_threat_confidence(probabilities)
                elif hasattr(self.xgb_model, "get_top_class"):
                    predicted_label, top_confidence = self.xgb_model.get_top_class(feature_vector.reshape(1, -1))
                    threat_confidence = float(top_confidence if predicted_label != "BENIGN" else 0.0)
            except RuntimeError:
                probabilities = None

        if probabilities is None and predicted_label == "BENIGN" and threat_confidence == 0.0:
            probabilities = self._heuristic_class_probabilities(features_dict)
            predicted_label, threat_confidence = self._label_and_threat_confidence(probabilities)

        override_result = self._apply_tree_override(features_dict, predicted_label, threat_confidence)
        return override_result.label, float(np.clip(override_result.confidence, 0.0, 1.0))

    def _apply_tree_override(
        self,
        features_dict: dict[str, Any],
        predicted_label: str,
        threat_confidence: float,
    ) -> OverrideResult:
        if hasattr(self.tree_logic, "evaluate"):
            return self.tree_logic.evaluate(features_dict, predicted_label, threat_confidence)
        label, confidence = self.tree_logic.apply(features_dict, predicted_label, threat_confidence)
        return OverrideResult(label=label, confidence=confidence, overridden=label != predicted_label, reason="apply")

    def _label_and_threat_confidence(self, probabilities: np.ndarray) -> tuple[str, float]:
        probs = np.asarray(probabilities, dtype=np.float32).reshape(-1)
        if probs.shape[0] != len(CLASS_NAMES):
            raise ValueError(f"Expected {len(CLASS_NAMES)} class probabilities, got {probs.shape[0]}.")
        probs = np.clip(probs, 0.0, None)
        total = float(probs.sum())
        if total <= 0:
            probs = np.ones(len(CLASS_NAMES), dtype=np.float32) / len(CLASS_NAMES)
        else:
            probs = probs / total
        best_index = int(np.argmax(probs))
        label = CLASS_NAMES[best_index]
        benign_probability = float(probs[0])
        threat_confidence = 1.0 - benign_probability
        return label, float(np.clip(threat_confidence, 0.0, 1.0))

    def _fuse_confidence(self, snn_score: float, lnn_confidence: float, xgb_confidence: float, behavioral_delta: float) -> float:
        confidence = (
            0.35 * snn_score
            + 0.30 * lnn_confidence
            + 0.25 * xgb_confidence
            + 0.10 * behavioral_delta
        )
        return float(np.clip(confidence, 0.0, 1.0))

    def _derive_verdict(self, confidence: float, behavioral_delta: float) -> str:
        if confidence > 0.80:
            return "HACKER"
        if confidence > 0.50:
            return "HACKER" if behavioral_delta > 0.50 else "FORGETFUL_USER"
        if confidence > 0.30:
            return "FORGETFUL_USER"
        return "LEGITIMATE"

    def _publish(self, topic: str, payload: dict[str, Any]) -> None:
        if self.publish_callback is None:
            return
        self.publish_callback(topic, payload)

    def analyze_session(self, session_data: dict[str, Any]) -> ThreatVerdict:
        session_id = str(session_data.get("session_id", f"session-{int(time.time() * 1000)}"))
        user_id = str(session_data.get("user_id", "unknown-user"))
        source_ip = str(session_data.get("source_ip", "unknown"))
        timestamp = float(session_data.get("timestamp") or time.time())
        features_dict: dict[str, float] = {}

        try:
            with self._lock:
                feature_vector = self._coerce_feature_vector(
                    session_data.get("flow_features", session_data.get("features"))
                )
                features_dict = self._build_features_dict(feature_vector, session_data)
                behavioral_vector = self._extract_behavioral_vector(session_data)
                snn_score = self._run_snn(feature_vector, features_dict)
                lnn_class, lnn_confidence = self._run_lnn(feature_vector, session_data, features_dict)
                xgb_class, xgb_confidence = self._run_xgb(feature_vector, features_dict)
                behavioral_delta = self.behavioral_profiler.compute_delta(user_id, behavioral_vector)
                confidence = self._fuse_confidence(snn_score, lnn_confidence, xgb_confidence, behavioral_delta)
                verdict = self._derive_verdict(confidence, behavioral_delta)
                model_version = self.current_model_version

            self.behavioral_profiler.update_profile(user_id, behavioral_vector)
            threat_verdict = ThreatVerdict(
                session_id=session_id,
                user_id=user_id,
                source_ip=source_ip,
                snn_score=float(snn_score),
                lnn_class=lnn_class,
                xgb_class=xgb_class,
                behavioral_delta=float(behavioral_delta),
                confidence=float(confidence),
                verdict=verdict,
                timestamp=timestamp,
                model_version=model_version,
                features_dict=features_dict,
            )
            if verdict == "HACKER":
                self._publish(
                    "alerts",
                    {
                        "session_id": session_id,
                        "user_id": user_id,
                        "source_ip": source_ip,
                        "confidence": threat_verdict.confidence,
                        "verdict": threat_verdict.verdict,
                        "timestamp": threat_verdict.timestamp,
                    },
                )
            self._publish("verdicts", threat_verdict.to_dict())
            return threat_verdict
        except Exception as exc:
            log.exception("DecisionEngine failed for session %s: %s", session_id, exc)
            return ThreatVerdict(
                session_id=session_id,
                user_id=user_id,
                source_ip=source_ip,
                snn_score=0.0,
                lnn_class="INCONCLUSIVE",
                xgb_class="INCONCLUSIVE",
                behavioral_delta=0.0,
                confidence=0.0,
                verdict="INCONCLUSIVE",
                timestamp=timestamp,
                model_version=self.current_model_version,
                features_dict={**features_dict, "_error": str(exc)},
            )

    def check_model_version(self) -> bool:
        payload = self._read_model_version()
        new_version = str(payload.get("version", "0.0.0"))
        if new_version == self.current_model_version:
            return False

        new_validation = dict(payload.get("validation_f1", {}))
        for key in ("snn", "lnn", "xgb"):
            previous = self.current_validation_f1.get(key)
            current = new_validation.get(key)
            if previous is not None and current is not None and float(current) < float(previous):
                log.warning(
                    "Skipping hot-swap to %s because %s validation F1 regressed from %.4f to %.4f.",
                    new_version,
                    key,
                    float(previous),
                    float(current),
                )
                return False

        try:
            with self._lock:
                if not self._override_flags["snn"]:
                    snn_path = self._resolve_artifact_path(payload.get("snn"))
                    if snn_path is not None:
                        self.snn_encoder, self.snn_model = self._load_snn_bundle(snn_path)
                if not self._override_flags["lnn"]:
                    lnn_path = self._resolve_artifact_path(payload.get("lnn"))
                    if lnn_path is not None:
                        self.lnn_reservoir, self.lnn_classifier, self.lnn_window_size = self._load_lnn_bundle(lnn_path)
                if not self._override_flags["xgb"]:
                    xgb_path = self._resolve_artifact_path(payload.get("xgb"))
                    if xgb_path is not None:
                        self.xgb_model = self._load_xgb_bundle(xgb_path)
                self.current_model_version = new_version
                self.current_validation_f1 = new_validation
            return True
        except Exception as exc:
            log.warning("Failed to hot-swap model version %s: %s", new_version, exc)
            return False

    def start_model_monitor(self) -> None:
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            return

        def _poll() -> None:
            while not self._monitor_stop.wait(self.model_poll_interval_seconds):
                self.check_model_version()

        self._monitor_stop.clear()
        self._monitor_thread = threading.Thread(target=_poll, name="decision-engine-model-monitor", daemon=True)
        self._monitor_thread.start()

    def stop_model_monitor(self) -> None:
        self._monitor_stop.set()
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=1.0)


def feature_value(features_dict: dict[str, Any], key: str) -> float:
    value = features_dict.get(key, 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


__all__ = ["ThreatVerdict", "DecisionEngine"]
