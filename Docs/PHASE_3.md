# Phase 3 — Dataset Preprocessing Pipeline

> **Master Plan Reference:** Phase 3 (Week 1-2 after Feature Engine)

## What Was Built

### `datasets/preprocess.py`

A standalone preprocessing pipeline that:

- Recursively loads raw dataset files from `datasets/raw/`
- Handles both `.csv` and `.txt` inputs so NSL-KDD is not silently skipped
- Normalizes column names to `snake_case`
- Maps raw labels into the 7-class NeuroShield taxonomy
- Keeps numeric features only, removes sparse columns, fills missing values with medians
- Aligns the output to the exact runtime feature contract from `data/feature_columns.txt`
- Scales features with `MinMaxScaler`
- Balances low-count classes with SMOTE when available, or replacement oversampling when `imbalanced-learn` is missing
- Saves:
  - `datasets/processed/unified_train.csv`
  - `datasets/processed/unified_test.csv`
  - `datasets/scaler.pkl`
  - `datasets/feature_columns.txt`
  - runtime copies to `data/scaler.pkl` and `data/feature_columns.txt`

### `tests/verify_phase3_preprocess.py`

A local checkpoint script that generates synthetic raw dataset files, runs the preprocessing pipeline, and asserts:

- train/test CSVs are created
- schema matches the 80-feature runtime contract
- no NaN values remain
- all 7 unified classes survive the split
- the saved scaler loads and matches the feature count

## Checkpoints

### Checkpoint 3A — Local synthetic verification

```bash
python tests/verify_phase3_preprocess.py
```

Expected:

- `Phase 3 preprocessing pipeline checkpoints passed`

### Checkpoint 3B — Real raw dataset run

After downloading the real datasets into `datasets/raw/`:

```bash
python datasets/preprocess.py
```

Expected:

- `datasets/processed/unified_train.csv` exists
- `datasets/processed/unified_test.csv` exists
- `datasets/scaler.pkl` exists
- `datasets/feature_columns.txt` exists
- `data/scaler.pkl` exists for runtime services

### Checkpoint 3C — Output sanity

```bash
python -c "import pandas as pd; df = pd.read_csv('datasets/processed/unified_train.csv'); print(df.shape); print(df.isna().sum().sum())"
python -c "from pathlib import Path; print(len([line for line in Path('datasets/feature_columns.txt').read_text().splitlines() if line.strip()]))"
```

Expected:

- first command prints a non-zero shape and `0` NaN values
- second command prints `80`

## Important Logic Notes

- The repo docs had a practical mismatch: training artifacts were described under `datasets/`, while runtime services load them from `data/`. The Phase 3 pipeline now writes both copies so training and runtime stay in sync.
- NSL-KDD is distributed as `.txt`, not `.csv`, so Phase 3 now supports both input types.
- If `imbalanced-learn` is unavailable, the pipeline still works using deterministic replacement oversampling. That keeps the checkpoint path usable in local environments without extra installs.

## Next: Phase 4 — SNN Engine

Phase 4 should now train against `datasets/processed/unified_train.csv` while reusing the exact same 80-feature order saved by Phase 2 and Phase 3.
