from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Sequence

import joblib
import numpy as np
import torch
from torch import nn
from xgboost import XGBClassifier


log = logging.getLogger(__name__)

CLASS_NAMES = [
    "BENIGN",
    "DDOS",
    "BRUTE_FORCE",
    "RECONNAISSANCE",
    "WEB_ATTACK",
    "BOT",
    "OTHER",
]

CLASS_INDEX = {name: index for index, name in enumerate(CLASS_NAMES)}

DEFAULT_LEGACY_LABELS = [
    "BENIGN",
    "Bot",
    "DDoS",
    "DoS GoldenEye",
    "DoS Hulk",
    "DoS Slowhttptest",
    "DoS slowloris",
    "FTP-Patator",
    "Heartbleed",
    "Infiltration",
    "PortScan",
    "SSH-Patator",
    "Web Attack - Brute Force",
    "Web Attack - Sql Injection",
    "Web Attack - XSS",
]

FEATURE_NAME_ALIASES = {
    "flow_byts_s": "flow_bytes_per_s",
    "flow_bytes_s": "flow_bytes_per_s",
    "flow_packets_s": "flow_packets_per_s",
    "flow_pkts_s": "flow_packets_per_s",
    "tot_fwd_pkts": "fwd_packets_total",
    "total_fwd_packets": "fwd_packets_total",
    "total_forward_packets": "fwd_packets_total",
    "tot_bwd_pkts": "bwd_packets_total",
    "total_backward_packets": "bwd_packets_total",
    "total_bwd_packets": "bwd_packets_total",
    "totlen_fwd_pkts": "fwd_bytes_total",
    "total_length_of_fwd_packets": "fwd_bytes_total",
    "totlen_bwd_pkts": "bwd_bytes_total",
    "total_length_of_bwd_packets": "bwd_bytes_total",
    "fwd_iat_tot": "fwd_iat_total",
    "bwd_iat_tot": "bwd_iat_total",
    "fwd_header_len": "fwd_header_length",
    "bwd_header_len": "bwd_header_length",
    "fwd_header_length_1": "fwd_header_length_again",
    "pkt_len_var": "pkt_len_variance",
    "packet_length_variance": "pkt_len_variance",
    "packet_size_variance": "pkt_len_variance",
    "average_packet_size": "avg_packet_size",
    "pkt_size_avg": "avg_packet_size",
    "fwd_seg_size_avg": "avg_fwd_segment_size",
    "avg_fwd_segment_size": "avg_fwd_segment_size",
    "bwd_seg_size_avg": "avg_bwd_segment_size",
    "avg_bwd_segment_size": "avg_bwd_segment_size",
    "subflow_fwd_pkts": "subflow_fwd_packets",
    "subflow_fwd_byts": "subflow_fwd_bytes",
    "subflow_bwd_pkts": "subflow_bwd_packets",
    "subflow_bwd_byts": "subflow_bwd_bytes",
    "init_fwd_win_byts": "init_win_bytes_fwd",
    "init_bwd_win_byts": "init_win_bytes_bwd",
    "init_win_bytes_forward": "init_win_bytes_fwd",
    "init_win_bytes_backward": "init_win_bytes_bwd",
    "fwd_act_data_pkts": "act_data_pkt_fwd",
    "fwd_seg_size_min": "min_seg_size_fwd",
    "min_seg_size_forward": "min_seg_size_fwd",
    "cwr_flag_count": "cwe_flag_count",
}


def canonicalize_feature_name(name: object) -> str:
    text = str(name).strip().lower()
    text = text.replace("%", "percent")
    text = text.replace("/", "_s")
    text = text.replace("–", "-")
    text = text.replace("\x96", "-")
    text = re.sub(r"[\s\-\.]+", "_", text)
    text = re.sub(r"[^a-z0-9_]", "", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return FEATURE_NAME_ALIASES.get(text, text or "unnamed")


def normalize_label_name(label: object) -> str:
    text = str(label).strip().lower()
    text = text.replace("–", "-")
    text = text.replace("\x96", "-")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def map_legacy_label(label: object) -> str:
    normalized = normalize_label_name(label)
    if normalized in {"benign", "normal"}:
        return "BENIGN"
    if "bot" in normalized:
        return "BOT"
    if "portscan" in normalized or "scan" in normalized or "recon" in normalized or "probe" in normalized:
        return "RECONNAISSANCE"
    if "ftp patator" in normalized or "ssh patator" in normalized or "brute force" in normalized:
        return "BRUTE_FORCE"
    if "sql injection" in normalized or "xss" in normalized or "web attack" in normalized or "injection" in normalized:
        return "WEB_ATTACK"
    if "ddos" in normalized or normalized.startswith("dos "):
        return "DDOS"
    return "OTHER"


def aggregate_probabilities(probabilities: np.ndarray, raw_labels: Sequence[str]) -> np.ndarray:
    current = np.zeros(len(CLASS_NAMES), dtype=np.float32)
    for probability, label in zip(np.asarray(probabilities, dtype=np.float32).reshape(-1), raw_labels):
        mapped = map_legacy_label(label)
        current[CLASS_INDEX[mapped]] += float(probability)

    total = float(current.sum())
    if total <= 0.0:
        current[CLASS_INDEX["BENIGN"]] = 1.0
        return current
    return current / total


def load_legacy_labels(artifact_root: Path) -> list[str]:
    encoder_path = artifact_root / "label_encoder.pkl"
    if encoder_path.exists():
        try:
            encoder = joblib.load(encoder_path)
            classes = getattr(encoder, "classes_", None)
            if classes is not None and len(classes) > 0:
                return [str(item) for item in list(classes)]
        except Exception as exc:
            log.warning("Failed to load legacy label encoder from %s: %s", encoder_path, exc)
    return list(DEFAULT_LEGACY_LABELS)


class LegacyFeatureBridge:
    def __init__(self, artifact_root: Path, current_feature_names: Sequence[str]) -> None:
        self.artifact_root = Path(artifact_root)
        self.current_feature_names = list(current_feature_names)
        self.current_index = {
            canonicalize_feature_name(name): index
            for index, name in enumerate(self.current_feature_names)
        }
        self.legacy_feature_names = self._load_legacy_feature_names()
        self.legacy_keys = [canonicalize_feature_name(name) for name in self.legacy_feature_names]
        self.scaler = self._load_scaler()

    def _load_legacy_feature_names(self) -> list[str]:
        feature_path = self.artifact_root / "feature_columns.txt"
        if feature_path.exists():
            return [line.strip() for line in feature_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return list(self.current_feature_names)

    def _load_scaler(self):
        scaler_path = self.artifact_root / "scaler.pkl"
        if not scaler_path.exists():
            return None
        try:
            return joblib.load(scaler_path)
        except Exception as exc:
            log.warning("Failed to load legacy scaler from %s: %s", scaler_path, exc)
            return None

    def map_vector(self, current_vector: np.ndarray) -> np.ndarray:
        current = np.asarray(current_vector, dtype=np.float32).reshape(-1)
        mapped = np.zeros(len(self.legacy_keys), dtype=np.float32)
        for legacy_index, key in enumerate(self.legacy_keys):
            current_index = self.current_index.get(key)
            if current_index is None or current_index >= current.shape[0]:
                continue
            mapped[legacy_index] = current[current_index]
        return mapped

    def map_sequence(self, current_sequence: np.ndarray) -> np.ndarray:
        sequence = np.asarray(current_sequence, dtype=np.float32)
        if sequence.ndim == 1:
            return self.map_vector(sequence).reshape(1, -1)
        if sequence.ndim != 2:
            raise ValueError("legacy feature bridge expects a 1D or 2D feature array.")
        return np.asarray([self.map_vector(row) for row in sequence], dtype=np.float32)

    def scale_vector(self, vector: np.ndarray, *, enabled: bool) -> np.ndarray:
        if not enabled or self.scaler is None:
            return np.asarray(vector, dtype=np.float32)
        return np.asarray(self.scaler.transform([np.asarray(vector, dtype=np.float32)])[0], dtype=np.float32)

    def scale_sequence(self, sequence: np.ndarray, *, enabled: bool) -> np.ndarray:
        if not enabled or self.scaler is None:
            return np.asarray(sequence, dtype=np.float32)
        return np.asarray(self.scaler.transform(np.asarray(sequence, dtype=np.float32)), dtype=np.float32)


class LegacyMLPClassifier(nn.Module):
    def __init__(
        self,
        input_size: int,
        hidden_sizes: Sequence[int],
        n_classes: int,
        feature_bridge: LegacyFeatureBridge,
        raw_labels: Sequence[str],
    ) -> None:
        super().__init__()
        hidden_sizes = list(hidden_sizes)
        self.fc1 = nn.Linear(input_size, hidden_sizes[0])
        self.fc2 = nn.Linear(hidden_sizes[0], hidden_sizes[1])
        self.fc3 = nn.Linear(hidden_sizes[1], n_classes)
        self.feature_bridge = feature_bridge
        self.raw_labels = [str(label) for label in raw_labels]

    @classmethod
    def from_state_dict(
        cls,
        state_dict: dict[str, torch.Tensor],
        artifact_root: Path,
        current_feature_names: Sequence[str],
    ) -> "LegacyMLPClassifier":
        model = cls(
            input_size=int(state_dict["fc1.weight"].shape[1]),
            hidden_sizes=[
                int(state_dict["fc1.weight"].shape[0]),
                int(state_dict["fc2.weight"].shape[0]),
            ],
            n_classes=int(state_dict["fc3.weight"].shape[0]),
            feature_bridge=LegacyFeatureBridge(artifact_root, current_feature_names),
            raw_labels=load_legacy_labels(artifact_root),
        )
        model.load_state_dict(state_dict)
        model.eval()
        return model

    def _prepare_batch(self, current_features: np.ndarray, *, apply_scaler: bool) -> torch.Tensor:
        array = np.asarray(current_features, dtype=np.float32)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        mapped = np.asarray([self.feature_bridge.map_vector(row) for row in array], dtype=np.float32)
        mapped = np.asarray(
            [self.feature_bridge.scale_vector(row, enabled=apply_scaler) for row in mapped],
            dtype=np.float32,
        )
        return torch.tensor(mapped, dtype=torch.float32)

    def predict_proba(self, current_features: np.ndarray, *, apply_scaler: bool) -> np.ndarray:
        batch = self._prepare_batch(current_features, apply_scaler=apply_scaler)
        with torch.no_grad():
            logits = self.fc3(torch.relu(self.fc2(torch.relu(self.fc1(batch)))))
            probabilities = torch.softmax(logits, dim=-1).cpu().numpy()
        return np.asarray(
            [aggregate_probabilities(row, self.raw_labels) for row in probabilities],
            dtype=np.float32,
        )

    def anomaly_score(self, current_features: np.ndarray, *, apply_scaler: bool) -> np.ndarray:
        probabilities = self.predict_proba(current_features, apply_scaler=apply_scaler)
        benign = probabilities[:, CLASS_INDEX["BENIGN"]]
        return 1.0 - benign


class LegacyLSTMClassifier(nn.Module):
    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        num_layers: int,
        n_classes: int,
        feature_bridge: LegacyFeatureBridge,
        raw_labels: Sequence[str],
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers=num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, n_classes)
        self.feature_bridge = feature_bridge
        self.raw_labels = [str(label) for label in raw_labels]

    @classmethod
    def from_state_dict(
        cls,
        state_dict: dict[str, torch.Tensor],
        artifact_root: Path,
        current_feature_names: Sequence[str],
    ) -> "LegacyLSTMClassifier":
        layer_ids = sorted(
            int(match.group(1))
            for key in state_dict
            for match in [re.fullmatch(r"lstm\.weight_ih_l(\d+)", key)]
            if match is not None
        )
        num_layers = max(layer_ids) + 1 if layer_ids else 1
        model = cls(
            input_size=int(state_dict["lstm.weight_ih_l0"].shape[1]),
            hidden_size=int(state_dict["lstm.weight_hh_l0"].shape[1]),
            num_layers=num_layers,
            n_classes=int(state_dict["fc.weight"].shape[0]),
            feature_bridge=LegacyFeatureBridge(artifact_root, current_feature_names),
            raw_labels=load_legacy_labels(artifact_root),
        )
        model.load_state_dict(state_dict)
        model.eval()
        return model

    def _prepare_batch(self, current_sequence: np.ndarray, *, apply_scaler: bool) -> torch.Tensor:
        sequence = np.asarray(current_sequence, dtype=np.float32)
        if sequence.ndim == 1:
            sequence = sequence.reshape(1, -1)
        if sequence.ndim == 2:
            mapped = self.feature_bridge.map_sequence(sequence)
            mapped = self.feature_bridge.scale_sequence(mapped, enabled=apply_scaler)
            batch = mapped.reshape(1, mapped.shape[0], mapped.shape[1])
            return torch.tensor(batch, dtype=torch.float32)
        if sequence.ndim == 3:
            mapped = np.asarray([self.feature_bridge.map_sequence(item) for item in sequence], dtype=np.float32)
            if apply_scaler and self.feature_bridge.scaler is not None:
                mapped = np.asarray(
                    [self.feature_bridge.scale_sequence(item, enabled=True) for item in mapped],
                    dtype=np.float32,
                )
            return torch.tensor(mapped, dtype=torch.float32)
        raise ValueError("legacy LSTM expects a 1D, 2D, or 3D array.")

    def predict_proba(self, current_sequence: np.ndarray, *, apply_scaler: bool) -> np.ndarray:
        batch = self._prepare_batch(current_sequence, apply_scaler=apply_scaler)
        with torch.no_grad():
            outputs, _ = self.lstm(batch)
            logits = self.fc(outputs[:, -1, :])
            probabilities = torch.softmax(logits, dim=-1).cpu().numpy()
        return np.asarray(
            [aggregate_probabilities(row, self.raw_labels) for row in probabilities],
            dtype=np.float32,
        )


class LegacyXGBoostClassifier:
    def __init__(
        self,
        model: XGBClassifier,
        feature_bridge: LegacyFeatureBridge,
        raw_labels: Sequence[str],
    ) -> None:
        self.model = model
        self.feature_bridge = feature_bridge
        self.raw_labels = [str(label) for label in raw_labels]

    @classmethod
    def from_artifacts(
        cls,
        model_path: Path,
        artifact_root: Path,
        current_feature_names: Sequence[str],
    ) -> "LegacyXGBoostClassifier":
        model = XGBClassifier()
        model.load_model(str(model_path))
        return cls(
            model=model,
            feature_bridge=LegacyFeatureBridge(artifact_root, current_feature_names),
            raw_labels=load_legacy_labels(artifact_root),
        )

    def predict_proba(self, current_features: np.ndarray, *, apply_scaler: bool) -> np.ndarray:
        array = np.asarray(current_features, dtype=np.float32)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        mapped = np.asarray([self.feature_bridge.map_vector(row) for row in array], dtype=np.float32)
        if apply_scaler and self.feature_bridge.scaler is not None:
            mapped = self.feature_bridge.scaler.transform(mapped)
        raw_probabilities = self.model.predict_proba(mapped)
        return np.asarray(
            [aggregate_probabilities(row, self.raw_labels) for row in raw_probabilities],
            dtype=np.float32,
        )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = [
    "CLASS_NAMES",
    "LegacyLSTMClassifier",
    "LegacyMLPClassifier",
    "LegacyXGBoostClassifier",
    "canonicalize_feature_name",
    "map_legacy_label",
]
