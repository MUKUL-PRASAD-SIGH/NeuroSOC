# Phases 4-6 — SNN, LNN, and XGBoost Core

> **Master Plan Reference:** Phase 4 (SNN), Phase 5 (LNN), Phase 6 (XGBoost)

## What Was Built

### Phase 4 — SNN Engine

- `inference-service/core/snn/encoder.py`
  Gaussian receptive-field spike encoder for the 80-feature contract.
- `inference-service/core/snn/network.py`
  Recurrent spiking anomaly detector with anomaly score output and checkpoint save/load helpers.
- `retraining-service/train_snn.py`
  Training script with validation tracking, confusion matrix export, STDP-inspired post-step adjustment, and `model_version.json` updates.

### Phase 5 — LNN Engine

- `inference-service/core/lnn/reservoir.py`
  Fixed sparse liquid reservoir with verified spectral-radius scaling.
- `inference-service/core/lnn/classifier.py`
  Trainable linear readout over the reservoir state.
- `retraining-service/train_lnn.py`
  Sliding-window training script that freezes the reservoir and updates the version tracker.

### Phase 6 — XGBoost Engine

- `inference-service/core/xgboost/model.py`
  Runtime wrapper for prediction, confidence lookup, feature importance, save/load.
- `inference-service/core/xgboost/tree_logic.py`
  Hard override rules for DDOS, reconnaissance, and brute-force patterns.
- `retraining-service/train_xgboost.py`
  Cross-validation + final-fit script that saves `xgboost_best.json` and updates `model_version.json`.

## Important Logic Notes

- The docs assume `norse`, but the current local environment does not have it installed. The SNN core now prefers Norse automatically when available and falls back to a local PyTorch-compatible recurrent spiking approximation for smoke tests.
- All three training scripts support `--smoke-test` so we can verify the build and artifact flow without waiting on the real dataset pipeline.
- `models/model_version.json` remains the contract for later hot-swap logic in the inference service, so each training script updates it directly.

## Checkpoints

### Checkpoint 4-6A — Full local smoke verification

```bash
python tests/verify_phase4_to_6_models.py
```

Expected:

- all standalone model modules run successfully
- all three training scripts complete in smoke-test mode
- synthetic artifacts are created
- `model_version.json` is populated

### Checkpoint 4B — SNN training smoke path

```bash
python retraining-service/train_snn.py --smoke-test
```

Expected:

- `snn_best.pt` saved
- confusion matrix PNG saved
- `model_version.json` updated

### Checkpoint 5B — LNN training smoke path

```bash
python retraining-service/train_lnn.py --smoke-test
```

Expected:

- `lnn_best.pt` saved
- reservoir spectral radius remains near `0.9`
- `model_version.json` updated

### Checkpoint 6B — XGBoost training smoke path

```bash
python retraining-service/train_xgboost.py --smoke-test
```

Expected:

- `xgboost_best.json` saved
- feature importance printed
- `model_version.json` updated

## What Is Still Next

The next major build step after these phases is the inference/deployment wiring:

- Phase 7 decision engine
- model loading into `inference-service/main.py`
- later feedback/retraining loop integration

That work can now assume the SNN, LNN, and XGBoost core files exist and have a verified smoke-test path.
