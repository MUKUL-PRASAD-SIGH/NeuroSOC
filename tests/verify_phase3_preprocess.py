from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import joblib
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
PREPROCESS_SCRIPT = REPO_ROOT / "datasets" / "preprocess.py"
CONTRACT_FILE = REPO_ROOT / "data" / "feature_columns.txt"


def build_sample_rows() -> list[dict[str, object]]:
    label_plan = [
        ("BENIGN", "BENIGN"),
        ("BENIGN", "Normal"),
        ("DDOS", "DoS Hulk"),
        ("DDOS", "DDoS LOIC-UDP"),
        ("BRUTE_FORCE", "FTP-BruteForce"),
        ("BRUTE_FORCE", "SSH-Bruteforce"),
        ("RECONNAISSANCE", "PortScan"),
        ("RECONNAISSANCE", "Recon-HostDiscovery"),
        ("WEB_ATTACK", "Web Attack SQL Injection"),
        ("WEB_ATTACK", "XSS"),
        ("BOT", "Bot"),
        ("OTHER", "Heartbleed"),
    ]

    rows: list[dict[str, object]] = []
    for idx in range(42):
        _, raw_label = label_plan[idx % len(label_plan)]
        rows.append(
            {
                " Flow Duration ": 1000 + idx * 10,
                "Flow Bytes/s": 2000 + idx * 7 if idx != 3 else float("inf"),
                "Flow Packets/s": 15 + (idx % 5),
                "Total Fwd Packets": 3 + (idx % 4),
                " Total Backward Packets": 2 + (idx % 3),
                "Total Length of Fwd Packets": 100 + idx * 3,
                "Total Length of Bwd Packets": 90 + idx * 2,
                "Fwd Packet Length Max": 60 + idx,
                "Fwd Packet Length Mean": 40 + idx * 0.5,
                "Bwd Packet Length Max": 55 + idx * 0.8,
                "Fwd IAT Total": 0.2 + idx * 0.01,
                "Fwd IAT Mean": 0.05 + idx * 0.002,
                "Flow IAT Mean": 0.08 + idx * 0.003,
                "Flow IAT Total": 0.5 + idx * 0.01,
                "PSH Flag Count": idx % 2,
                "ACK Flag Count": 1 + (idx % 4),
                "Fwd Header Length": 20 + (idx % 3),
                "Bwd Header Length": 20 + (idx % 2),
                "Average Packet Size": 70 + idx * 0.4,
                "Packet Length Variance": 4 + idx * 0.2,
                "Mostly Null": None if idx < 35 else 999,
                "Reviewer Note": "señal" if idx % 2 == 0 else "señal-extra",
                "Label": raw_label,
            }
        )
    return rows


def write_fixture_dataset(raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows = build_sample_rows()
    first = pd.DataFrame(rows[:21])
    second = pd.DataFrame(rows[21:])

    first_path = raw_dir / "fixture_a.csv"
    second_path = raw_dir / "fixture_b.csv"

    first.to_csv(first_path, index=False)
    second.to_csv(second_path, index=False, encoding="latin-1")


def run_preprocess(raw_dir: Path, processed_dir: Path, artifacts_dir: Path) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(PREPROCESS_SCRIPT),
        "--raw-dir",
        str(raw_dir),
        "--processed-dir",
        str(processed_dir),
        "--scaler-path",
        str(artifacts_dir / "scaler.pkl"),
        "--feature-columns-path",
        str(artifacts_dir / "feature_columns.txt"),
        "--runtime-data-dir",
        str(artifacts_dir / "runtime"),
        "--contract-file",
        str(CONTRACT_FILE),
        "--min-samples-per-class",
        "6",
        "--max-rows",
        "1000",
    ]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def main() -> int:
    print("=========================================================")
    print("[TEST] PHASE 3 DATASET PIPELINE: CHECKPOINT VERIFICATION")
    print("=========================================================\n")

    if not CONTRACT_FILE.exists():
        print(f"[FAIL] Missing feature contract: {CONTRACT_FILE}")
        return 1

    with tempfile.TemporaryDirectory(prefix="neuroshield-phase3-") as temp_dir:
        temp_root = Path(temp_dir)
        raw_dir = temp_root / "raw"
        processed_dir = temp_root / "processed"
        artifacts_dir = temp_root / "artifacts"

        write_fixture_dataset(raw_dir)
        result = run_preprocess(raw_dir, processed_dir, artifacts_dir)

        if result.returncode != 0:
            print("[FAIL] preprocess.py exited with a non-zero status.")
            print(result.stdout)
            print(result.stderr)
            return 1

        train_path = processed_dir / "unified_train.csv"
        test_path = processed_dir / "unified_test.csv"
        feature_columns_path = artifacts_dir / "feature_columns.txt"
        runtime_feature_columns_path = artifacts_dir / "runtime" / "feature_columns.txt"
        scaler_path = artifacts_dir / "scaler.pkl"
        runtime_scaler_path = artifacts_dir / "runtime" / "scaler.pkl"

        print(">>> CHECKPOINT 3A: Artifact existence <<<")
        required_paths = [
            train_path,
            test_path,
            feature_columns_path,
            runtime_feature_columns_path,
            scaler_path,
            runtime_scaler_path,
        ]
        missing = [path for path in required_paths if not path.exists()]
        if missing:
            print("[FAIL] Missing expected artifacts:")
            for path in missing:
                print(f"  - {path}")
            return 1
        print("[PASS] Train/test CSVs, scaler, and feature contract files were created.")

        train_df = pd.read_csv(train_path)
        test_df = pd.read_csv(test_path)
        feature_names = [line.strip() for line in feature_columns_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        runtime_feature_names = [line.strip() for line in runtime_feature_columns_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        contract_feature_names = [line.strip() for line in CONTRACT_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]

        print("\n>>> CHECKPOINT 3B: Schema contract <<<")
        if feature_names != contract_feature_names or runtime_feature_names != contract_feature_names:
            print("[FAIL] Saved feature columns do not match the runtime contract.")
            return 1
        if list(train_df.columns[:-1]) != contract_feature_names or list(test_df.columns[:-1]) != contract_feature_names:
            print("[FAIL] Output CSV column order does not match the runtime contract.")
            return 1
        print("[PASS] Train/test CSVs follow the exact 80-feature contract.")

        print("\n>>> CHECKPOINT 3C: Data hygiene <<<")
        if train_df.isna().sum().sum() != 0 or test_df.isna().sum().sum() != 0:
            print("[FAIL] NaN values remain in the saved outputs.")
            return 1
        if "label" not in train_df.columns or "label" not in test_df.columns:
            print("[FAIL] Label column missing from one or both outputs.")
            return 1
        if train_df["label"].nunique() < 7 or test_df["label"].nunique() < 7:
            print("[FAIL] Expected all 7 unified classes to survive the split.")
            return 1
        print("[PASS] No NaNs remain, labels are preserved, and all 7 classes are present.")

        print("\n>>> CHECKPOINT 3D: Scaler readability <<<")
        scaler = joblib.load(scaler_path)
        if getattr(scaler, "n_features_in_", None) != len(contract_feature_names):
            print("[FAIL] Saved scaler does not align with the feature contract.")
            return 1
        print("[PASS] Saved scaler loads cleanly and matches the 80-feature schema.")

        print("\n>>> CHECKPOINT 3E: Script output <<<")
        stdout = result.stdout.strip()
        if "Class distribution before balancing:" not in stdout or "Class distribution after balancing:" not in stdout:
            print("[FAIL] preprocess.py did not print the expected checkpoint summaries.")
            return 1
        print("[PASS] preprocess.py printed the expected checkpoint summary information.")

        shutil.rmtree(temp_root, ignore_errors=True)

    print("\n[SUCCESS] Phase 3 preprocessing pipeline checkpoints passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
