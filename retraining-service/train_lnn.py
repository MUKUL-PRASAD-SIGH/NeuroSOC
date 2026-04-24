from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score
from sklearn.preprocessing import LabelEncoder
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from common import (
    CLASS_NAMES,
    DATASET_TRAIN_PATH,
    MODEL_VERSION_PATH,
    add_inference_service_to_path,
    generate_synthetic_dataset,
    load_tabular_dataset,
    make_sliding_windows,
    train_val_split,
    update_model_version,
)

add_inference_service_to_path()

from core.lnn.classifier import LNNClassifier
from core.lnn.reservoir import LiquidReservoir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the NeuroShield LNN readout.")
    parser.add_argument("--dataset", type=Path, default=DATASET_TRAIN_PATH)
    parser.add_argument("--model-path", type=Path, default=Path("models/lnn_best.pt"))
    parser.add_argument("--version-file", type=Path, default=MODEL_VERSION_PATH)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--window-size", type=int, default=20)
    parser.add_argument("--reservoir-size", type=int, default=500)
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--smoke-test", action="store_true")
    return parser.parse_args()


def prepare_dataset(args: argparse.Namespace) -> tuple[np.ndarray, np.ndarray, list[str]]:
    if args.smoke_test or not args.dataset.exists():
        return generate_synthetic_dataset(n_samples_per_class=22)
    return load_tabular_dataset(args.dataset)


def evaluate(
    reservoir: LiquidReservoir,
    classifier: LNNClassifier,
    loader: DataLoader,
    device: torch.device,
) -> tuple[float, float]:
    classifier.eval()
    predictions: list[int] = []
    targets: list[int] = []
    with torch.no_grad():
        for batch_sequences, batch_labels in loader:
            sequence_tensor = batch_sequences.to(device).transpose(0, 1)
            states, _ = reservoir(sequence_tensor)
            logits = classifier(states)
            predictions.extend(torch.argmax(logits, dim=1).cpu().tolist())
            targets.extend(batch_labels.cpu().tolist())
    accuracy = accuracy_score(targets, predictions)
    f1 = f1_score(targets, predictions, average="macro")
    return accuracy, f1


def main() -> int:
    args = parse_args()
    device = torch.device(args.device)
    features, labels, feature_names = prepare_dataset(args)
    windows, window_labels = make_sliding_windows(features, labels, window_size=args.window_size)
    x_train, x_val, y_train, y_val = train_val_split(windows, window_labels)

    label_encoder = LabelEncoder()
    label_encoder.fit(CLASS_NAMES)
    y_train_encoded = label_encoder.transform(y_train)
    y_val_encoded = label_encoder.transform(y_val)

    train_loader = DataLoader(
        TensorDataset(torch.tensor(x_train, dtype=torch.float32), torch.tensor(y_train_encoded, dtype=torch.long)),
        batch_size=args.batch_size,
        shuffle=True,
    )
    val_loader = DataLoader(
        TensorDataset(torch.tensor(x_val, dtype=torch.float32), torch.tensor(y_val_encoded, dtype=torch.long)),
        batch_size=args.batch_size,
    )

    reservoir = LiquidReservoir(
        input_size=x_train.shape[2],
        reservoir_size=128 if args.smoke_test else args.reservoir_size,
    ).to(device)
    assert not any(parameter.requires_grad for parameter in reservoir.parameters())

    classifier = LNNClassifier(reservoir_size=reservoir.reservoir_size).to(device)
    optimizer = torch.optim.Adam(classifier.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    best_f1 = -1.0
    best_payload: dict | None = None
    epochs = 2 if args.smoke_test else args.epochs

    for epoch in range(epochs):
        classifier.train()
        running_loss = 0.0
        for batch_sequences, batch_labels in train_loader:
            optimizer.zero_grad()
            sequence_tensor = batch_sequences.to(device).transpose(0, 1)
            states, _ = reservoir(sequence_tensor)
            logits = classifier(states)
            loss = criterion(logits, batch_labels.to(device))
            loss.backward()
            optimizer.step()
            running_loss += float(loss.item())

        accuracy, f1 = evaluate(reservoir, classifier, val_loader, device)
        print(
            json.dumps(
                {
                    "epoch": epoch + 1,
                    "loss": round(running_loss / max(len(train_loader), 1), 4),
                    "val_accuracy": round(accuracy, 4),
                    "val_f1_macro": round(f1, 4),
                    "spectral_radius": round(reservoir.compute_spectral_radius(), 4),
                }
            )
        )
        if f1 > best_f1:
            best_f1 = f1
            best_payload = {
                "reservoir_config": {
                    "input_size": reservoir.input_size,
                    "reservoir_size": reservoir.reservoir_size,
                    "spectral_radius": reservoir.target_spectral_radius,
                    "leak_rate": reservoir.leak_rate,
                    "sparsity": reservoir.sparsity,
                    "seed": reservoir.seed,
                    "feature_names": feature_names,
                    "window_size": args.window_size,
                },
                "reservoir_state": reservoir.state_dict(),
                "classifier_config": {
                    "reservoir_size": classifier.reservoir_size,
                    "n_classes": classifier.n_classes,
                },
                "classifier_state": classifier.state_dict(),
            }

    if best_payload is None:
        raise RuntimeError("Training did not produce a valid LNN checkpoint.")

    args.model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(best_payload, args.model_path)
    version_payload = update_model_version("lnn", args.model_path, best_f1, args.version_file)
    print(f"[PASS] Saved LNN checkpoint to {args.model_path}")
    print(f"[PASS] Updated model_version.json to {version_payload['version']}")
    print(f"[PASS] Best validation F1: {best_f1:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
