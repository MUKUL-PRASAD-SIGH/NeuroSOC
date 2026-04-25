from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request

import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:  # pragma: no cover - depends on local environment
    psycopg2 = None
    RealDictCursor = None

from common import (
    CLASS_NAMES,
    DATASET_TRAIN_PATH,
    MODEL_VERSION_PATH,
    RESULTS_DIR,
    add_inference_service_to_path,
    generate_synthetic_dataset,
    load_tabular_dataset,
)

add_inference_service_to_path()

from core.xgboost.model import XGBoostClassifier


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [retraining] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


DATABASE_URL = os.getenv("DATABASE_URL", "")
RETRAIN_INTERVAL_SECONDS = int(os.getenv("RETRAIN_INTERVAL_SECONDS", "300"))
RETRAIN_MIN_FEEDBACK_SAMPLES = int(os.getenv("RETRAIN_MIN_FEEDBACK_SAMPLES", "50"))
MODEL_VERSION_FILE = Path(os.getenv("MODEL_VERSION_FILE", str(MODEL_VERSION_PATH))).expanduser()
RETRAIN_STATE_FILE = Path(
    os.getenv("RETRAIN_STATE_FILE", str(MODEL_VERSION_FILE.parent / "retraining_state.json"))
).expanduser()
RESULTS_DIR_PATH = Path(os.getenv("RETRAIN_RESULTS_DIR", str(RESULTS_DIR))).expanduser()
BASE_DATASET_PATH = Path(os.getenv("RETRAIN_BASE_DATASET", str(DATASET_TRAIN_PATH))).expanduser()
INFERENCE_RELOAD_URL = os.getenv("INFERENCE_RELOAD_URL", "").strip()
MIN_F1_IMPROVEMENT = float(os.getenv("RETRAIN_MIN_F1_IMPROVEMENT", "0.0"))


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def increment_version(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return "0.0.1"
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def coerce_feature_vector(raw_value: Any, expected_length: int = 80) -> list[float] | None:
    parsed = raw_value
    if isinstance(parsed, str):
        stripped = parsed.strip()
        if not stripped:
            return None
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return None
    if not isinstance(parsed, list):
        return None
    try:
        vector = [float(value) for value in parsed[:expected_length]]
    except (TypeError, ValueError):
        return None
    if len(vector) < expected_length:
        vector.extend([0.0] * (expected_length - len(vector)))
    return vector


@dataclass
class FeedbackSample:
    id: int
    session_id: str
    features: list[float]
    label: str
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None


@dataclass
class RetrainingState:
    last_seen_feedback_id: int = 0
    last_trained_feedback_id: int = 0
    last_run_at: str | None = None
    last_outcome: str = "never-run"
    last_model_version: str | None = None
    last_validation_f1: float | None = None
    total_runs: int = 0
    total_successful_retrains: int = 0

    @classmethod
    def load(cls, path: Path) -> "RetrainingState":
        if not path.exists():
            return cls()
        return cls(**json.loads(path.read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        atomic_write_text(path, json.dumps(asdict(self), indent=2))


class FeedbackRepositoryLike(Protocol):
    def bootstrap(self) -> None:
        ...

    def fetch_feedback_samples(self, min_id_exclusive: int = 0, max_id_inclusive: int | None = None) -> list[FeedbackSample]:
        ...


class PostgresFeedbackRepository:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("DATABASE_URL is required for the retraining service.")
        self.database_url = database_url

    def connect(self):
        if psycopg2 is None or RealDictCursor is None:
            raise RuntimeError(
                "psycopg2 is required to connect to PostgreSQL. Install retraining-service requirements first."
            )
        return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)

    def bootstrap(self) -> None:
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS labeled_training_data (
                        id BIGSERIAL PRIMARY KEY,
                        session_id TEXT UNIQUE NOT NULL,
                        features JSONB NOT NULL,
                        label TEXT NOT NULL,
                        confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                        attack_type TEXT,
                        trigger_reason TEXT,
                        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                conn.commit()

    def fetch_feedback_samples(
        self,
        min_id_exclusive: int = 0,
        max_id_inclusive: int | None = None,
    ) -> list[FeedbackSample]:
        predicates = ["id > %s"]
        params: list[Any] = [min_id_exclusive]
        if max_id_inclusive is not None:
            predicates.append("id <= %s")
            params.append(max_id_inclusive)

        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT id, session_id, features, label, confidence, metadata, created_at
                    FROM labeled_training_data
                    WHERE {' AND '.join(predicates)}
                    ORDER BY id ASC
                    """,
                    params,
                )
                rows = cur.fetchall()

        samples: list[FeedbackSample] = []
        for row in rows:
            label = str(row["label"]).strip().upper()
            if label not in CLASS_NAMES:
                continue
            vector = coerce_feature_vector(row.get("features"))
            if vector is None:
                continue
            samples.append(
                FeedbackSample(
                    id=int(row["id"]),
                    session_id=str(row["session_id"]),
                    features=vector,
                    label=label,
                    confidence=float(row.get("confidence") or 0.0),
                    metadata=dict(row.get("metadata") or {}),
                    created_at=str(row.get("created_at")) if row.get("created_at") is not None else None,
                )
            )
        return samples


@dataclass
class RetrainingResult:
    status: str
    message: str
    processed_feedback_rows: int = 0
    total_feedback_rows: int = 0
    validation_f1: float | None = None
    validation_accuracy: float | None = None
    model_path: str | None = None
    model_version: str | None = None
    reload_triggered: bool = False


class RetrainingService:
    def __init__(
        self,
        repository: FeedbackRepositoryLike,
        base_dataset_path: Path = BASE_DATASET_PATH,
        model_version_file: Path = MODEL_VERSION_FILE,
        state_file: Path = RETRAIN_STATE_FILE,
        results_dir: Path = RESULTS_DIR_PATH,
        min_feedback_samples: int = RETRAIN_MIN_FEEDBACK_SAMPLES,
        min_f1_improvement: float = MIN_F1_IMPROVEMENT,
        inference_reload_url: str = INFERENCE_RELOAD_URL,
    ) -> None:
        self.repository = repository
        self.base_dataset_path = Path(base_dataset_path)
        self.model_version_file = Path(model_version_file)
        self.state_file = Path(state_file)
        self.results_dir = Path(results_dir)
        self.min_feedback_samples = max(1, int(min_feedback_samples))
        self.min_f1_improvement = float(min_f1_improvement)
        self.inference_reload_url = inference_reload_url

    def _load_model_version_payload(self) -> dict[str, Any]:
        if not self.model_version_file.exists():
            return {
                "version": "0.0.0",
                "snn": None,
                "lnn": None,
                "xgb": None,
                "validation_f1": {"snn": None, "lnn": None, "xgb": None},
            }
        return json.loads(self.model_version_file.read_text(encoding="utf-8-sig"))

    def _load_training_corpus(self, feedback_samples: list[FeedbackSample]) -> tuple[np.ndarray, np.ndarray, list[str]]:
        if self.base_dataset_path.exists():
            base_features, base_labels, feature_names = load_tabular_dataset(self.base_dataset_path)
        else:
            feature_names = [f"feature_{index}" for index in range(80)]
            base_features, base_labels, _ = generate_synthetic_dataset(
                n_samples_per_class=max(24, self.min_feedback_samples),
                n_features=len(feature_names),
            )

        if feedback_samples:
            feedback_features = np.asarray([sample.features for sample in feedback_samples], dtype=np.float32)
            feedback_labels = np.asarray([sample.label for sample in feedback_samples], dtype=object)
            features = np.vstack([base_features, feedback_features]).astype(np.float32)
            labels = np.concatenate([base_labels, feedback_labels])
        else:
            features = np.asarray(base_features, dtype=np.float32)
            labels = np.asarray(base_labels, dtype=object)

        return features, labels, feature_names

    def _split_dataset(self, features: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        unique_labels, counts = np.unique(labels, return_counts=True)
        use_stratify = len(unique_labels) > 1 and int(np.min(counts)) >= 2
        return train_test_split(
            features,
            labels,
            test_size=0.2,
            random_state=42,
            stratify=labels if use_stratify else None,
        )

    def _train_xgboost(
        self,
        features: np.ndarray,
        labels: np.ndarray,
        feature_names: list[str],
    ) -> tuple[XGBoostClassifier, float, float, dict[str, Any]]:
        x_train, x_val, y_train, y_val = self._split_dataset(features, labels)

        label_encoder = LabelEncoder()
        label_encoder.fit(CLASS_NAMES)
        y_train_encoded = label_encoder.transform(y_train)
        y_val_encoded = label_encoder.transform(y_val)

        estimator = XGBClassifier(
            n_estimators=250,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.85,
            objective="multi:softprob",
            num_class=len(CLASS_NAMES),
            eval_metric="mlogloss",
            random_state=42,
            tree_method="hist",
        )
        estimator.fit(x_train, y_train_encoded)
        predictions = estimator.predict(x_val)
        validation_accuracy = float(accuracy_score(y_val_encoded, predictions))
        validation_f1 = float(f1_score(y_val_encoded, predictions, average="macro"))

        wrapper = XGBoostClassifier(feature_names=feature_names)
        wrapper.model = estimator

        metrics = {
            "validation_accuracy": validation_accuracy,
            "validation_f1": validation_f1,
            "training_rows": int(len(x_train)),
            "validation_rows": int(len(x_val)),
            "class_counts": {label: int(count) for label, count in zip(*np.unique(labels, return_counts=True))},
            "top_feature_importances": list(wrapper.feature_importance().items())[:10],
        }
        return wrapper, validation_f1, validation_accuracy, metrics

    def _write_model_version(
        self,
        current_payload: dict[str, Any],
        artifact_name: str,
        validation_f1: float,
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        payload = dict(current_payload)
        payload["version"] = increment_version(str(payload.get("version", "0.0.0")))
        payload["xgb"] = artifact_name
        payload.setdefault("validation_f1", {})
        payload["validation_f1"]["xgb"] = float(validation_f1)
        payload["timestamp"] = utcnow_iso()
        payload["feedback_training"] = metrics
        atomic_write_text(self.model_version_file, json.dumps(payload, indent=2))
        return payload

    def _write_retraining_summary(self, metrics: dict[str, Any], state: RetrainingState) -> None:
        summary_path = self.results_dir / "latest_retraining_summary.json"
        payload = {
            "timestamp": utcnow_iso(),
            "state": asdict(state),
            "metrics": metrics,
        }
        atomic_write_text(summary_path, json.dumps(payload, indent=2))

    def _trigger_reload(self) -> bool:
        if not self.inference_reload_url:
            return False
        try:
            request = urllib_request.Request(self.inference_reload_url, data=b"{}", method="POST")
            request.add_header("Content-Type", "application/json")
            with urllib_request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            log.info("Triggered inference reload: %s", payload)
            return bool(payload.get("reloaded") or payload.get("active_model_version"))
        except (urllib_error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            log.warning("Failed to trigger inference model reload: %s", exc)
            return False

    def run_once(self) -> RetrainingResult:
        self.repository.bootstrap()
        state = RetrainingState.load(self.state_file)
        state.total_runs += 1
        state.last_run_at = utcnow_iso()

        new_feedback = self.repository.fetch_feedback_samples(min_id_exclusive=state.last_seen_feedback_id)
        if len(new_feedback) < self.min_feedback_samples:
            state.last_outcome = "waiting-for-feedback"
            state.save(self.state_file)
            return RetrainingResult(
                status="skipped",
                message=(
                    f"Need at least {self.min_feedback_samples} new feedback rows; "
                    f"found {len(new_feedback)} since id {state.last_seen_feedback_id}."
                ),
                processed_feedback_rows=len(new_feedback),
                total_feedback_rows=len(new_feedback),
            )

        max_feedback_id = max(sample.id for sample in new_feedback)
        all_feedback = self.repository.fetch_feedback_samples(max_id_inclusive=max_feedback_id)
        features, labels, feature_names = self._load_training_corpus(all_feedback)
        wrapper, validation_f1, validation_accuracy, metrics = self._train_xgboost(features, labels, feature_names)

        current_payload = self._load_model_version_payload()
        current_xgb_f1 = current_payload.get("validation_f1", {}).get("xgb")

        metrics.update(
            {
                "new_feedback_rows": len(new_feedback),
                "total_feedback_rows": len(all_feedback),
                "candidate_feedback_max_id": max_feedback_id,
                "previous_xgb_validation_f1": float(current_xgb_f1) if current_xgb_f1 is not None else None,
            }
        )

        state.last_seen_feedback_id = max_feedback_id

        if current_xgb_f1 is not None and validation_f1 + self.min_f1_improvement < float(current_xgb_f1):
            state.last_outcome = "skipped-regression"
            state.save(self.state_file)
            self._write_retraining_summary(metrics, state)
            return RetrainingResult(
                status="skipped",
                message=(
                    f"Candidate validation F1 {validation_f1:.4f} regressed below "
                    f"current {float(current_xgb_f1):.4f}; keeping existing model."
                ),
                processed_feedback_rows=len(new_feedback),
                total_feedback_rows=len(all_feedback),
                validation_f1=validation_f1,
                validation_accuracy=validation_accuracy,
            )

        artifact_name = f"xgboost_feedback_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{max_feedback_id}.json"
        artifact_path = self.model_version_file.parent / artifact_name
        wrapper.save(artifact_path)

        payload = self._write_model_version(current_payload, artifact_name, validation_f1, metrics)
        state.last_trained_feedback_id = max_feedback_id
        state.last_model_version = str(payload["version"])
        state.last_validation_f1 = validation_f1
        state.last_outcome = "trained"
        state.total_successful_retrains += 1
        state.save(self.state_file)
        self._write_retraining_summary(metrics, state)
        reload_triggered = self._trigger_reload()

        return RetrainingResult(
            status="trained",
            message=(
                f"Trained XGBoost on {metrics['training_rows'] + metrics['validation_rows']} total rows "
                f"({len(all_feedback)} feedback rows)."
            ),
            processed_feedback_rows=len(new_feedback),
            total_feedback_rows=len(all_feedback),
            validation_f1=validation_f1,
            validation_accuracy=validation_accuracy,
            model_path=artifact_name,
            model_version=str(payload["version"]),
            reload_triggered=reload_triggered,
        )

    def run_forever(self, interval_seconds: int = RETRAIN_INTERVAL_SECONDS) -> None:
        log.info(
            "Retraining service started. Waiting for %d new feedback rows between runs.",
            self.min_feedback_samples,
        )
        while True:
            try:
                result = self.run_once()
                log.info("%s: %s", result.status.upper(), result.message)
            except Exception as exc:
                log.exception("Retraining iteration failed: %s", exc)
            time.sleep(interval_seconds)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Feedback-driven XGBoost retraining loop for NeuroShield.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run-once", action="store_true", help="Process one retraining iteration and exit.")
    mode.add_argument("--daemon", action="store_true", help="Keep polling for new feedback forever.")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=RETRAIN_INTERVAL_SECONDS,
        help="Polling interval when running as a daemon.",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    service = RetrainingService(repository=PostgresFeedbackRepository(DATABASE_URL))
    if args.daemon:
        service.run_forever(interval_seconds=args.interval_seconds)
        return 0
    result = service.run_once()
    print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
