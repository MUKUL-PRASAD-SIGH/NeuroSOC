from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


CLASS_NAMES = [
    "BENIGN",
    "DDOS",
    "BRUTE_FORCE",
    "RECONNAISSANCE",
    "WEB_ATTACK",
    "BOT",
    "OTHER",
]

REPO_ROOT = Path(__file__).resolve().parents[1]
INFERENCE_SERVICE_DIR = REPO_ROOT / "inference-service"
MODELS_DIR = REPO_ROOT / "models"
RESULTS_DIR = REPO_ROOT / "retraining-service" / "results"
DATASET_TRAIN_PATH = REPO_ROOT / "datasets" / "processed" / "unified_train.csv"
DATASET_TEST_PATH = REPO_ROOT / "datasets" / "processed" / "unified_test.csv"
MODEL_VERSION_PATH = MODELS_DIR / "model_version.json"


def add_inference_service_to_path() -> None:
    target = str(INFERENCE_SERVICE_DIR)
    if target not in sys.path:
        sys.path.insert(0, target)


def load_tabular_dataset(csv_path: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    frame = pd.read_csv(csv_path)
    if "label" not in frame.columns:
        raise ValueError(f"{csv_path} is missing the 'label' column.")
    feature_names = [column for column in frame.columns if column != "label"]
    features = frame[feature_names].to_numpy(dtype=np.float32)
    labels = frame["label"].astype(str).to_numpy()
    return features, labels, feature_names


def generate_synthetic_dataset(
    n_samples_per_class: int = 24,
    n_features: int = 80,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    rng = np.random.default_rng(seed)
    centers = np.linspace(0.05, 0.95, len(CLASS_NAMES))
    features: list[np.ndarray] = []
    labels: list[str] = []
    for class_index, class_name in enumerate(CLASS_NAMES):
        base = centers[class_index]
        class_features = rng.normal(loc=base, scale=0.03, size=(n_samples_per_class, n_features))
        class_features[:, class_index % n_features] += 0.12
        features.append(np.clip(class_features, 0.0, 1.0).astype(np.float32))
        labels.extend([class_name] * n_samples_per_class)
    feature_names = [f"feature_{index}" for index in range(n_features)]
    return np.vstack(features), np.asarray(labels), feature_names


def train_val_split(
    features: np.ndarray,
    labels: np.ndarray,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    return train_test_split(
        features,
        labels,
        test_size=test_size,
        stratify=labels,
        random_state=random_state,
    )


def make_sliding_windows(
    features: np.ndarray,
    labels: np.ndarray,
    window_size: int = 20,
) -> tuple[np.ndarray, np.ndarray]:
    if len(features) < window_size:
        raise ValueError(f"Need at least {window_size} samples to build sliding windows.")
    windows = []
    window_labels = []
    for start in range(0, len(features) - window_size + 1):
        end = start + window_size
        windows.append(features[start:end])
        window_labels.append(labels[end - 1])
    return np.stack(windows).astype(np.float32), np.asarray(window_labels)


def _increment_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return "0.0.1"
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def update_model_version(
    key: str,
    artifact_path: Path,
    validation_f1: float,
    version_file: Path = MODEL_VERSION_PATH,
) -> dict:
    if version_file.exists():
        payload = json.loads(version_file.read_text(encoding="utf-8"))
    else:
        payload = {
            "version": "0.0.0",
            "snn": None,
            "lnn": None,
            "xgb": None,
            "validation_f1": {"snn": None, "lnn": None, "xgb": None},
        }

    payload["version"] = _increment_version(payload.get("version", "0.0.0"))
    payload[key] = str(artifact_path)
    payload.setdefault("validation_f1", {})
    payload["validation_f1"][key] = float(validation_f1)
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
