from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False)


def assert_ok(result: subprocess.CompletedProcess[str], context: str) -> None:
    if result.returncode != 0:
        raise AssertionError(f"{context} failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")


def main() -> int:
    print("=========================================================")
    print("[TEST] PHASE 4-6 MODEL CORE: CHECKPOINT VERIFICATION")
    print("=========================================================\n")

    module_commands = {
        "SNN encoder": [PYTHON, "inference-service/core/snn/encoder.py"],
        "SNN network": [PYTHON, "inference-service/core/snn/network.py"],
        "LNN reservoir": [PYTHON, "inference-service/core/lnn/reservoir.py"],
        "LNN classifier": [PYTHON, "inference-service/core/lnn/classifier.py"],
        "XGBoost wrapper": [PYTHON, "inference-service/core/xgboost/model.py"],
        "Tree logic": [PYTHON, "inference-service/core/xgboost/tree_logic.py"],
    }

    print(">>> CHECKPOINT 4A/5A/6A: Standalone module smoke tests <<<")
    for label, command in module_commands.items():
        result = run_command(command)
        assert_ok(result, label)
        print(f"[PASS] {label} module runs standalone.")

    with tempfile.TemporaryDirectory(prefix="neuroshield-models-") as temp_dir:
        temp_root = Path(temp_dir)
        models_dir = temp_root / "models"
        results_dir = temp_root / "results"
        version_file = models_dir / "model_version.json"
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(
            json.dumps(
                {
                    "version": "0.0.0",
                    "snn": None,
                    "lnn": None,
                    "xgb": None,
                    "validation_f1": {"snn": None, "lnn": None, "xgb": None},
                }
            ),
            encoding="utf-8",
        )

        print("\n>>> CHECKPOINT 4B/5B/6B: Training script smoke tests <<<")
        snn_result = run_command(
            [
                PYTHON,
                "retraining-service/train_snn.py",
                "--smoke-test",
                "--model-path",
                str(models_dir / "snn_best.pt"),
                "--version-file",
                str(version_file),
                "--results-dir",
                str(results_dir),
            ]
        )
        assert_ok(snn_result, "train_snn.py")
        print("[PASS] SNN training smoke test completed.")

        lnn_result = run_command(
            [
                PYTHON,
                "retraining-service/train_lnn.py",
                "--smoke-test",
                "--model-path",
                str(models_dir / "lnn_best.pt"),
                "--version-file",
                str(version_file),
            ]
        )
        assert_ok(lnn_result, "train_lnn.py")
        print("[PASS] LNN training smoke test completed.")

        xgb_result = run_command(
            [
                PYTHON,
                "retraining-service/train_xgboost.py",
                "--smoke-test",
                "--model-path",
                str(models_dir / "xgboost_best.json"),
                "--version-file",
                str(version_file),
            ]
        )
        assert_ok(xgb_result, "train_xgboost.py")
        print("[PASS] XGBoost training smoke test completed.")

        required_paths = [
            models_dir / "snn_best.pt",
            models_dir / "lnn_best.pt",
            models_dir / "xgboost_best.json",
            models_dir / "xgboost_best.json.meta.json",
            results_dir / "snn_confusion_matrix.png",
            version_file,
        ]
        for artifact in required_paths:
            if not artifact.exists():
                raise AssertionError(f"Expected artifact missing: {artifact}")

        version_payload = json.loads(version_file.read_text(encoding="utf-8"))
        if not all(version_payload.get(key) for key in ("snn", "lnn", "xgb")):
            raise AssertionError("model_version.json was not fully populated.")

        sys.path.insert(0, str(REPO_ROOT / "inference-service"))
        from core.lnn.reservoir import LiquidReservoir
        from core.xgboost.tree_logic import TreeLogicOverride

        print("\n>>> CHECKPOINT 5C: Reservoir spectral radius <<<")
        reservoir = LiquidReservoir()
        spectral_radius = reservoir.compute_spectral_radius()
        if not (0.85 <= spectral_radius <= 0.95):
            raise AssertionError(f"Spectral radius out of range: {spectral_radius}")
        print(f"[PASS] Spectral radius is within range: {spectral_radius:.4f}")

        print("\n>>> CHECKPOINT 6C: Tree logic override <<<")
        override = TreeLogicOverride()
        label, confidence = override.apply(
            {"packet_rate": 15000, "syn_ratio": 0.97},
            xgb_prediction="BENIGN",
            xgb_confidence=0.42,
        )
        if label != "DDOS" or confidence < 0.99:
            raise AssertionError("TreeLogicOverride failed to force the DDOS rule.")
        print("[PASS] Tree logic override forces DDOS when the documented rule triggers.")

    print("\n[SUCCESS] Phase 4-6 model checkpoints passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
