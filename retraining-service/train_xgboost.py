from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

from common import (
    CLASS_NAMES,
    DATASET_TEST_PATH,
    DATASET_TRAIN_PATH,
    MODEL_VERSION_PATH,
    add_inference_service_to_path,
    generate_synthetic_dataset,
    load_tabular_dataset,
    train_val_split,
    update_model_version,
)

add_inference_service_to_path()

from core.xgboost.model import XGBoostClassifier


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the NeuroShield XGBoost classifier.")
    parser.add_argument("--train-dataset", type=Path, default=DATASET_TRAIN_PATH)
    parser.add_argument("--test-dataset", type=Path, default=DATASET_TEST_PATH)
    parser.add_argument("--model-path", type=Path, default=Path("models/xgboost_best.json"))
    parser.add_argument("--version-file", type=Path, default=MODEL_VERSION_PATH)
    parser.add_argument("--smoke-test", action="store_true")
    return parser.parse_args()


def prepare_datasets(args: argparse.Namespace) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    if args.smoke_test or not args.train_dataset.exists():
        features, labels, feature_names = generate_synthetic_dataset(n_samples_per_class=30)
        x_train, x_test, y_train, y_test = train_val_split(features, labels, test_size=0.25)
        return x_train, x_test, y_train, y_test, feature_names

    x_train, y_train, feature_names = load_tabular_dataset(args.train_dataset)
    if args.test_dataset.exists():
        x_test, y_test, _ = load_tabular_dataset(args.test_dataset)
    else:
        x_train, x_test, y_train, y_test = train_val_split(x_train, y_train, test_size=0.2)
    return x_train, x_test, y_train, y_test, feature_names


def build_estimator(smoke_test: bool) -> XGBClassifier:
    return XGBClassifier(
        n_estimators=60 if smoke_test else 500,
        max_depth=4 if smoke_test else 6,
        learning_rate=0.2 if smoke_test else 0.1,
        subsample=0.9 if smoke_test else 0.8,
        colsample_bytree=0.9 if smoke_test else 0.8,
        objective="multi:softprob",
        num_class=len(CLASS_NAMES),
        eval_metric="mlogloss",
        random_state=42,
        tree_method="hist",
    )


def main() -> int:
    args = parse_args()
    x_train, x_test, y_train, y_test, feature_names = prepare_datasets(args)

    label_encoder = LabelEncoder()
    label_encoder.fit(CLASS_NAMES)
    y_train_encoded = label_encoder.transform(y_train)
    y_test_encoded = label_encoder.transform(y_test)

    splitter = StratifiedKFold(n_splits=3 if args.smoke_test else 5, shuffle=True, random_state=42)
    fold_scores: list[float] = []
    for fold, (train_index, val_index) in enumerate(splitter.split(x_train, y_train_encoded), start=1):
        estimator = build_estimator(args.smoke_test)
        estimator.fit(x_train[train_index], y_train_encoded[train_index])
        fold_predictions = estimator.predict(x_train[val_index])
        fold_f1 = f1_score(y_train_encoded[val_index], fold_predictions, average="macro")
        fold_scores.append(fold_f1)
        print(json.dumps({"fold": fold, "f1_macro": round(fold_f1, 4)}))

    final_model = build_estimator(args.smoke_test)
    final_model.fit(x_train, y_train_encoded)
    test_predictions = final_model.predict(x_test)
    test_accuracy = accuracy_score(y_test_encoded, test_predictions)
    test_f1 = f1_score(y_test_encoded, test_predictions, average="macro")

    wrapper = XGBoostClassifier(feature_names=feature_names)
    wrapper.model = final_model
    wrapper.save(args.model_path)
    version_payload = update_model_version("xgb", args.model_path, test_f1, args.version_file)

    top_ten = list(wrapper.feature_importance().items())[:10]
    print(f"[PASS] Saved XGBoost model to {args.model_path}")
    print(f"[PASS] Updated model_version.json to {version_payload['version']}")
    print(json.dumps({"cv_f1_macro_mean": round(float(np.mean(fold_scores)), 4), "test_accuracy": round(test_accuracy, 4), "test_f1_macro": round(test_f1, 4)}))
    print("[PASS] Top 10 feature importances:")
    for name, score in top_ten:
        print(f"  - {name}: {score:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
