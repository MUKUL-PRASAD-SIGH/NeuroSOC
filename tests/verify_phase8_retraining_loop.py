from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "retraining-service"))

import main as retraining_main


class FakeRepository:
    def __init__(self, samples):
        self.samples = list(samples)
        self.bootstrapped = False

    def bootstrap(self) -> None:
        self.bootstrapped = True

    def fetch_feedback_samples(self, min_id_exclusive: int = 0, max_id_inclusive: int | None = None):
        rows = [sample for sample in self.samples if sample.id > min_id_exclusive]
        if max_id_inclusive is not None:
            rows = [sample for sample in rows if sample.id <= max_id_inclusive]
        return rows


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def build_feedback_samples() -> list[retraining_main.FeedbackSample]:
    samples: list[retraining_main.FeedbackSample] = []
    base_vectors = [
        [0.02] * 80,
        [0.95 if index in {2, 31, 76} else 0.05 for index in range(80)],
        [0.88 if index in {3, 4, 9} else 0.07 for index in range(80)],
        [0.7 if index in {5, 6, 7} else 0.12 for index in range(80)],
        [0.92 if index in {10, 11, 12} else 0.03 for index in range(80)],
    ]
    labels = ["BENIGN", "DDOS", "BRUTE_FORCE", "RECONNAISSANCE", "WEB_ATTACK"]
    for offset, (vector, label) in enumerate(zip(base_vectors, labels), start=1):
        samples.append(
            retraining_main.FeedbackSample(
                id=offset,
                session_id=f"feedback-{offset}",
                features=vector,
                label=label,
                confidence=0.9,
                metadata={"source": "test"},
            )
        )
    return samples


def main() -> int:
    print("=========================================================")
    print("[TEST] PHASE 8 RETRAINING LOOP")
    print("=========================================================\n")

    samples = build_feedback_samples()
    repository = FakeRepository(samples)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        model_version_path = temp_root / "models" / "model_version.json"
        state_file = temp_root / "models" / "retraining_state.json"
        results_dir = temp_root / "results"

        model_version_path.parent.mkdir(parents=True, exist_ok=True)
        model_version_path.write_text(
            json.dumps(
                {
                    "version": "0.0.0",
                    "snn": None,
                    "lnn": None,
                    "xgb": None,
                    "validation_f1": {"snn": None, "lnn": None, "xgb": None},
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        service = retraining_main.RetrainingService(
            repository=repository,
            base_dataset_path=temp_root / "missing_train.csv",
            model_version_file=model_version_path,
            state_file=state_file,
            results_dir=results_dir,
            min_feedback_samples=5,
            inference_reload_url="",
        )

        result = service.run_once()
        assert_true(repository.bootstrapped, "Retraining service should bootstrap the repository before use.")
        assert_true(result.status == "trained", "Retraining service should train when enough new feedback exists.")
        assert_true(result.validation_f1 is not None and result.validation_f1 >= 0.0, "Validation F1 should be recorded.")
        assert_true(result.model_path is not None, "Retraining should publish a model artifact path.")

        artifact_path = model_version_path.parent / str(result.model_path)
        assert_true(artifact_path.exists(), "Retraining should save the new XGBoost artifact.")
        assert_true(artifact_path.with_suffix(artifact_path.suffix + ".meta.json").exists(), "Model metadata should be saved.")

        model_version = json.loads(model_version_path.read_text(encoding="utf-8"))
        assert_true(model_version["version"] == result.model_version, "model_version.json should be incremented.")
        assert_true(model_version["xgb"] == result.model_path, "model_version.json should point at the trained XGBoost artifact.")
        assert_true(model_version["validation_f1"]["xgb"] == result.validation_f1, "Validation F1 should be persisted.")
        assert_true(bool(model_version.get("timestamp")), "Retraining should stamp the model version with a timestamp.")

        state_payload = json.loads(state_file.read_text(encoding="utf-8"))
        assert_true(state_payload["last_seen_feedback_id"] == 5, "Retraining state should record the latest feedback id seen.")
        assert_true(state_payload["last_trained_feedback_id"] == 5, "Successful retraining should update the last trained feedback id.")
        assert_true(state_payload["last_outcome"] == "trained", "Retraining state should remember the latest successful outcome.")

        summary_path = results_dir / "latest_retraining_summary.json"
        assert_true(summary_path.exists(), "Retraining should emit a summary artifact for inspection.")

        second_result = service.run_once()
        assert_true(second_result.status == "skipped", "Without new feedback rows, retraining should wait instead of retraining again.")
        assert_true("Need at least" in second_result.message, "Skip reason should explain the feedback threshold.")

        print("[PASS] Retraining consumes feedback rows, saves a model artifact, updates model_version.json, and persists daemon state.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
