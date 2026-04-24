from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, f1_score
from sklearn.preprocessing import LabelEncoder
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from common import (
    CLASS_NAMES,
    DATASET_TRAIN_PATH,
    MODEL_VERSION_PATH,
    RESULTS_DIR,
    add_inference_service_to_path,
    generate_synthetic_dataset,
    load_tabular_dataset,
    train_val_split,
    update_model_version,
)

add_inference_service_to_path()

from core.snn.encoder import SpikeEncoder
from core.snn.network import SNNAnomalyDetector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the NeuroShield SNN anomaly detector.")
    parser.add_argument("--dataset", type=Path, default=DATASET_TRAIN_PATH)
    parser.add_argument("--model-path", type=Path, default=Path("models/snn_best.pt"))
    parser.add_argument("--version-file", type=Path, default=MODEL_VERSION_PATH)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--timesteps", type=int, default=100)
    return parser.parse_args()


def prepare_dataset(args: argparse.Namespace) -> tuple[np.ndarray, np.ndarray, list[str]]:
    if args.smoke_test or not args.dataset.exists():
        return generate_synthetic_dataset(n_samples_per_class=18)
    return load_tabular_dataset(args.dataset)


def evaluate(
    model: SNNAnomalyDetector,
    encoder: SpikeEncoder,
    loader: DataLoader,
    device: torch.device,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    model.eval()
    predictions: list[int] = []
    targets: list[int] = []
    with torch.no_grad():
        for features, labels in loader:
            spike_train = encoder.encode_deterministic(features.numpy()).to(device)
            logits, _ = model(spike_train)
            predictions.extend(torch.argmax(logits, dim=1).cpu().tolist())
            targets.extend(labels.cpu().tolist())
    accuracy = accuracy_score(targets, predictions)
    f1 = f1_score(targets, predictions, average="macro")
    return accuracy, f1, np.asarray(targets), np.asarray(predictions)


def save_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    path: Path,
    label_encoder: LabelEncoder,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    display = ConfusionMatrixDisplay.from_predictions(
        y_true,
        y_pred,
        display_labels=label_encoder.classes_,
        xticks_rotation=45,
        colorbar=False,
    )
    display.figure_.tight_layout()
    display.figure_.savefig(path)
    plt.close(display.figure_)


def main() -> int:
    args = parse_args()
    device = torch.device(args.device)
    features, labels, feature_names = prepare_dataset(args)
    x_train, x_val, y_train, y_val = train_val_split(features, labels)

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

    encoder = SpikeEncoder(n_features=x_train.shape[1], T=args.timesteps)
    model = SNNAnomalyDetector(input_size=encoder.input_size).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    best_state: dict | None = None
    best_f1 = -1.0
    best_eval: tuple[np.ndarray, np.ndarray] | None = None
    epochs = 2 if args.smoke_test else args.epochs

    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for batch_features, batch_labels in train_loader:
            optimizer.zero_grad()
            spike_train = encoder.encode(batch_features.numpy()).to(device)
            logits, _, trace = model(spike_train, return_trace=True)
            loss = criterion(logits, batch_labels.to(device))
            loss.backward()
            optimizer.step()
            model.apply_stdp(trace.detach())
            running_loss += float(loss.item())

        accuracy, f1, y_true, y_pred = evaluate(model, encoder, val_loader, device)
        print(
            json.dumps(
                {
                    "epoch": epoch + 1,
                    "loss": round(running_loss / max(len(train_loader), 1), 4),
                    "val_accuracy": round(accuracy, 4),
                    "val_f1_macro": round(f1, 4),
                }
            )
        )
        if f1 > best_f1:
            best_f1 = f1
            best_state = {
                "config": {
                    "input_size": encoder.input_size,
                    "hidden_sizes": model.hidden_sizes,
                    "n_classes": model.n_classes,
                    "timesteps": args.timesteps,
                    "n_features": x_train.shape[1],
                    "feature_names": feature_names,
                },
                "state_dict": model.state_dict(),
            }
            best_eval = (y_true, y_pred)

    if best_state is None or best_eval is None:
        raise RuntimeError("Training did not produce a valid checkpoint.")

    args.model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, args.model_path)
    confusion_path = args.results_dir / "snn_confusion_matrix.png"
    save_confusion_matrix(best_eval[0], best_eval[1], confusion_path, label_encoder)
    version_payload = update_model_version("snn", args.model_path, best_f1, args.version_file)

    print(f"[PASS] Saved SNN checkpoint to {args.model_path}")
    print(f"[PASS] Saved confusion matrix to {confusion_path}")
    print(f"[PASS] Updated model_version.json to {version_payload['version']}")
    print(f"[PASS] Best validation F1: {best_f1:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
