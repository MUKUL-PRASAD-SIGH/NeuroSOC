from __future__ import annotations

import argparse
import sys
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

try:
    from imblearn.over_sampling import SMOTE
except ImportError:
    SMOTE = None


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = REPO_ROOT / "datasets"
DEFAULT_RAW_DIR = DATASETS_DIR / "raw"
DEFAULT_PROCESSED_DIR = DATASETS_DIR / "processed"
DEFAULT_SCALER_PATH = DATASETS_DIR / "scaler.pkl"
DEFAULT_FEATURE_COLUMNS_PATH = DATASETS_DIR / "feature_columns.txt"
DEFAULT_RUNTIME_DATA_DIR = REPO_ROOT / "data"
DEFAULT_CONTRACT_CANDIDATES = [
    DEFAULT_RUNTIME_DATA_DIR / "feature_columns.txt",
    DEFAULT_FEATURE_COLUMNS_PATH,
]

CHUNK_SIZE = 100_000
DEFAULT_MAX_ROWS = 500_000
DEFAULT_RANDOM_STATE = 42

LABEL_CANDIDATES = (
    "label",
    "attack",
    "attack_type",
    "class",
    "classification",
    "category",
)

COLUMN_ALIASES = {
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
    "fwd_act_data_pkts": "act_data_pkt_fwd",
    "fwd_seg_size_min": "min_seg_size_fwd",
    "cwr_flag_count": "cwe_flag_count",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unify raw intrusion datasets into NeuroShield train/test CSVs."
    )
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--scaler-path", type=Path, default=DEFAULT_SCALER_PATH)
    parser.add_argument("--feature-columns-path", type=Path, default=DEFAULT_FEATURE_COLUMNS_PATH)
    parser.add_argument("--runtime-data-dir", type=Path, default=DEFAULT_RUNTIME_DATA_DIR)
    parser.add_argument("--contract-file", type=Path, default=None)
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS)
    parser.add_argument("--min-samples-per-class", type=int, default=1000)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=DEFAULT_RANDOM_STATE)
    return parser.parse_args()


def snake_case(name: object) -> str:
    text = str(name).strip().lower()
    text = text.replace("%", "percent")
    text = text.replace("/", "_s")
    text = re.sub(r"[\s\-\.]+", "_", text)
    text = re.sub(r"[^a-z0-9_]", "", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return COLUMN_ALIASES.get(text, text or "unnamed")


def load_contract_features(contract_file: Path | None) -> list[str]:
    candidates = [contract_file] if contract_file else DEFAULT_CONTRACT_CANDIDATES
    for candidate in candidates:
        if candidate and candidate.exists():
            with candidate.open("r", encoding="utf-8") as handle:
                features = [line.strip() for line in handle if line.strip()]
            if features:
                print(f"[INFO] Loaded feature contract from {candidate}")
                return features
    print("[WARN] No feature contract file found. Falling back to discovered numeric columns.")
    return []


def find_input_files(raw_dir: Path) -> list[Path]:
    patterns = ("*.csv", "*.txt")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(sorted(raw_dir.rglob(pattern)))
    return files


def iter_file_chunks(path: Path):
    read_kwargs = {
        "chunksize": CHUNK_SIZE,
        "low_memory": False,
    }
    if path.suffix.lower() == ".txt":
        read_kwargs["header"] = None

    last_error: Exception | None = None
    for encoding in ("utf-8", "latin-1"):
        try:
            reader = pd.read_csv(path, encoding=encoding, **read_kwargs)
            for chunk in reader:
                yield chunk
            return
        except UnicodeDecodeError as exc:
            last_error = exc
        except pd.errors.ParserError as exc:
            last_error = exc
            break

    if last_error is not None:
        raise last_error


def assign_default_headers(frame: pd.DataFrame) -> pd.DataFrame:
    if not all(isinstance(col, int) for col in frame.columns):
        return frame

    renamed = frame.copy()
    renamed.columns = [f"column_{idx}" for idx in range(len(renamed.columns))]
    if len(renamed.columns) >= 2:
        renamed = renamed.rename(
            columns={
                renamed.columns[-2]: "label",
                renamed.columns[-1]: "difficulty",
            }
        )
    return renamed


def collapse_duplicate_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if not frame.columns.duplicated().any():
        return frame

    collapsed: dict[str, pd.Series] = {}
    for column in dict.fromkeys(frame.columns):
        duplicate_frame = frame.loc[:, frame.columns == column]
        if duplicate_frame.shape[1] == 1:
            collapsed[column] = duplicate_frame.iloc[:, 0]
        else:
            collapsed[column] = duplicate_frame.bfill(axis=1).iloc[:, 0]
    return pd.DataFrame(collapsed, index=frame.index)


def locate_label_column(columns: list[str]) -> str | None:
    for candidate in LABEL_CANDIDATES:
        if candidate in columns:
            return candidate
    for column in columns:
        if "label" in column:
            return column
    return None


def map_label(value: object) -> str:
    text = str(value).strip().lower()
    if not text:
        return "OTHER"
    if "ddos" in text or "dos" in text:
        return "DDOS"
    if "brute" in text:
        return "BRUTE_FORCE"
    if "scan" in text or "probe" in text or "recon" in text:
        return "RECONNAISSANCE"
    if "xss" in text or "sql" in text or "web" in text or "injection" in text:
        return "WEB_ATTACK"
    if "bot" in text:
        return "BOT"
    if text in {"benign", "normal"}:
        return "BENIGN"
    return "OTHER"


def preprocess_chunk(chunk: pd.DataFrame, source: Path) -> pd.DataFrame | None:
    frame = assign_default_headers(chunk)
    frame = frame.copy()
    frame.columns = [snake_case(column) for column in frame.columns]
    frame = collapse_duplicate_columns(frame)

    label_column = locate_label_column(list(frame.columns))
    if label_column is None:
        print(f"[WARN] Skipping {source.name}: no label column found after normalization.")
        return None

    labels = frame[label_column].map(map_label).astype(str)
    frame = frame.drop(columns=[label_column], errors="ignore")
    frame = frame.drop(columns=["difficulty"], errors="ignore")

    numeric_frame = pd.DataFrame(index=frame.index)
    for column in frame.columns:
        numeric_series = pd.to_numeric(frame[column], errors="coerce")
        if numeric_series.notna().any():
            numeric_frame[column] = numeric_series

    if numeric_frame.empty:
        print(f"[WARN] Skipping {source.name}: no numeric features found.")
        return None

    numeric_frame["label"] = labels
    return numeric_frame


def load_raw_frames(raw_dir: Path) -> pd.DataFrame:
    input_files = find_input_files(raw_dir)
    if not input_files:
        raise FileNotFoundError(
            f"No dataset files found under {raw_dir}. "
            "Download the raw datasets into datasets/raw/ first."
        )

    processed_chunks: list[pd.DataFrame] = []
    for path in input_files:
        print(f"[INFO] Reading {path}")
        chunk_count = 0
        for chunk in iter_file_chunks(path):
            processed = preprocess_chunk(chunk, path)
            if processed is not None and not processed.empty:
                processed_chunks.append(processed)
                chunk_count += 1
        if chunk_count == 0:
            print(f"[WARN] No usable chunks were loaded from {path.name}")

    if not processed_chunks:
        raise ValueError("No usable labeled numeric data was found in datasets/raw/.")

    return pd.concat(processed_chunks, ignore_index=True)


def print_distribution(title: str, labels: pd.Series) -> None:
    print(title)
    counts = labels.value_counts().sort_index()
    for label, count in counts.items():
        print(f"  - {label}: {count}")


def stratified_cap_rows(frame: pd.DataFrame, max_rows: int, random_state: int) -> pd.DataFrame:
    if max_rows <= 0 or len(frame) <= max_rows:
        return frame

    fraction = max_rows / float(len(frame))
    capped_parts: list[pd.DataFrame] = []
    for _, group in frame.groupby("label", sort=True):
        minimum = 2 if len(group) >= 2 else 1
        sample_size = min(len(group), max(minimum, int(round(len(group) * fraction))))
        capped_parts.append(group.sample(n=sample_size, random_state=random_state))

    capped = pd.concat(capped_parts, ignore_index=True)
    if len(capped) > max_rows:
        capped = capped.sample(n=max_rows, random_state=random_state)
    return capped.reset_index(drop=True)


def clean_numeric_frame(frame: pd.DataFrame) -> pd.DataFrame:
    numeric = frame.drop(columns=["label"]).replace([np.inf, -np.inf], np.nan)
    sparse_columns = [
        column for column in numeric.columns
        if numeric[column].isna().mean() > 0.5
    ]
    if sparse_columns:
        print(f"[INFO] Dropping {len(sparse_columns)} sparse columns (>50% null/inf).")
        numeric = numeric.drop(columns=sparse_columns)

    medians = numeric.median(numeric_only=True)
    numeric = numeric.fillna(medians).fillna(0.0)
    labels = frame["label"].astype(str).reset_index(drop=True)
    numeric = numeric.reset_index(drop=True)
    numeric["label"] = labels
    return numeric


def align_to_contract(frame: pd.DataFrame, contract_features: list[str]) -> tuple[pd.DataFrame, list[str]]:
    labels = frame["label"].astype(str).reset_index(drop=True)
    numeric = frame.drop(columns=["label"]).reset_index(drop=True)

    if not contract_features:
        discovered = sorted(numeric.columns.tolist())
        aligned = numeric.reindex(columns=discovered, fill_value=0.0)
        aligned["label"] = labels
        return aligned, discovered

    matched = [feature for feature in contract_features if feature in numeric.columns]
    print(f"[INFO] Contract feature coverage: {len(matched)}/{len(contract_features)} columns matched from raw data.")

    aligned = numeric.reindex(columns=contract_features, fill_value=0.0)
    aligned = aligned.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    aligned["label"] = labels
    return aligned, contract_features


def oversample_with_replacement(
    features: pd.DataFrame,
    labels: pd.Series,
    targets: dict[str, int],
    random_state: int,
) -> tuple[pd.DataFrame, pd.Series]:
    merged = features.copy()
    merged["label"] = labels.values
    pieces = [merged]
    for label, target_size in targets.items():
        current = merged[merged["label"] == label]
        needed = target_size - len(current)
        if needed > 0:
            pieces.append(current.sample(n=needed, replace=True, random_state=random_state))
    resampled = pd.concat(pieces, ignore_index=True)
    resampled = resampled.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
    return resampled.drop(columns=["label"]), resampled["label"]


def balance_classes(
    features: pd.DataFrame,
    labels: pd.Series,
    min_samples_per_class: int,
    random_state: int,
) -> tuple[pd.DataFrame, pd.Series]:
    counts = labels.value_counts().sort_index()
    targets = {
        label: min_samples_per_class
        for label, count in counts.items()
        if count < min_samples_per_class
    }

    if not targets:
        print("[INFO] Class balancing skipped: all classes already meet the minimum target.")
        return features, labels

    if SMOTE is not None:
        smallest_class = min(counts[label] for label in targets)
        if smallest_class > 1:
            neighbors = min(5, smallest_class - 1)
            try:
                sampler = SMOTE(
                    sampling_strategy=targets,
                    random_state=random_state,
                    k_neighbors=neighbors,
                )
                resampled_features, resampled_labels = sampler.fit_resample(features, labels)
                print(f"[INFO] Applied SMOTE with k_neighbors={neighbors}.")
                return (
                    pd.DataFrame(resampled_features, columns=features.columns),
                    pd.Series(resampled_labels, name="label"),
                )
            except Exception as exc:
                print(f"[WARN] SMOTE failed ({exc}). Falling back to replacement oversampling.")

    print("[INFO] Using replacement oversampling fallback.")
    return oversample_with_replacement(features, labels, targets, random_state)


def save_feature_contract(feature_names: list[str], feature_columns_path: Path, runtime_data_dir: Path) -> None:
    feature_columns_path.parent.mkdir(parents=True, exist_ok=True)
    feature_columns_path.write_text("\n".join(feature_names) + "\n", encoding="utf-8")

    runtime_data_dir.mkdir(parents=True, exist_ok=True)
    runtime_feature_columns_path = runtime_data_dir / "feature_columns.txt"
    runtime_feature_columns_path.write_text("\n".join(feature_names) + "\n", encoding="utf-8")

    print(f"[INFO] Saved training feature contract to {feature_columns_path}")
    print(f"[INFO] Saved runtime feature contract to {runtime_feature_columns_path}")


def save_scaler(scaler: MinMaxScaler, scaler_path: Path, runtime_data_dir: Path) -> None:
    scaler_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, scaler_path)

    runtime_data_dir.mkdir(parents=True, exist_ok=True)
    runtime_scaler_path = runtime_data_dir / "scaler.pkl"
    joblib.dump(scaler, runtime_scaler_path)

    print(f"[INFO] Saved training scaler to {scaler_path}")
    print(f"[INFO] Saved runtime scaler to {runtime_scaler_path}")


def ensure_split_is_feasible(labels: pd.Series, test_size: float) -> None:
    class_count = labels.nunique()
    minimum_test_rows = int(np.ceil(len(labels) * test_size))
    if minimum_test_rows < class_count:
        raise ValueError(
            f"Stratified split is not possible: test split would contain {minimum_test_rows} rows "
            f"for {class_count} classes. Increase the dataset size or lower the class count."
        )


def main() -> int:
    args = parse_args()

    try:
        contract_features = load_contract_features(args.contract_file)
        raw_frame = load_raw_frames(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}")
        return 1
    except Exception as exc:
        print(f"[ERROR] Failed while loading raw datasets: {exc}")
        return 1

    raw_frame = stratified_cap_rows(raw_frame, args.max_rows, args.random_state)
    print(f"[INFO] Combined usable rows: {len(raw_frame)}")
    print_distribution("[INFO] Class distribution before balancing:", raw_frame["label"])

    cleaned = clean_numeric_frame(raw_frame)
    aligned, feature_names = align_to_contract(cleaned, contract_features)

    features = aligned.drop(columns=["label"])
    labels = aligned["label"].astype(str)

    scaler = MinMaxScaler()
    scaled_array = scaler.fit_transform(features)
    scaled_features = pd.DataFrame(scaled_array, columns=feature_names)

    balanced_features, balanced_labels = balance_classes(
        scaled_features,
        labels,
        args.min_samples_per_class,
        args.random_state,
    )
    print_distribution("[INFO] Class distribution after balancing:", balanced_labels)

    try:
        ensure_split_is_feasible(balanced_labels, args.test_size)
        x_train, x_test, y_train, y_test = train_test_split(
            balanced_features,
            balanced_labels,
            test_size=args.test_size,
            stratify=balanced_labels,
            random_state=args.random_state,
        )
    except Exception as exc:
        print(f"[ERROR] Failed during train/test split: {exc}")
        return 1

    args.processed_dir.mkdir(parents=True, exist_ok=True)
    train_frame = x_train.copy()
    train_frame["label"] = y_train.values
    test_frame = x_test.copy()
    test_frame["label"] = y_test.values

    train_path = args.processed_dir / "unified_train.csv"
    test_path = args.processed_dir / "unified_test.csv"
    train_frame.to_csv(train_path, index=False)
    test_frame.to_csv(test_path, index=False)

    save_scaler(scaler, args.scaler_path, args.runtime_data_dir)
    save_feature_contract(feature_names, args.feature_columns_path, args.runtime_data_dir)

    print_distribution("[INFO] Train split distribution:", y_train)
    print_distribution("[INFO] Test split distribution:", y_test)
    print(f"[PASS] Saved train split to {train_path}")
    print(f"[PASS] Saved test split to {test_path}")
    print(f"[PASS] Train shape: {train_frame.shape}")
    print(f"[PASS] Test shape: {test_frame.shape}")
    print(f"[PASS] Feature count (excluding label): {len(feature_names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
