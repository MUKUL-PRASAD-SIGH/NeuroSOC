from __future__ import annotations

from pathlib import Path

import torch
from torch import nn


CLASS_NAMES = [
    "BENIGN",
    "DDOS",
    "BRUTE_FORCE",
    "RECONNAISSANCE",
    "WEB_ATTACK",
    "BOT",
    "OTHER",
]


class LNNClassifier(nn.Module):
    """Linear readout on liquid reservoir state traces."""

    CLASS_NAMES = CLASS_NAMES

    def __init__(self, reservoir_size: int = 500, n_classes: int = 7) -> None:
        super().__init__()
        self.reservoir_size = reservoir_size
        self.n_classes = n_classes
        self.readout = nn.Linear(reservoir_size, n_classes)

    def forward(self, reservoir_states: torch.Tensor) -> torch.Tensor:
        if reservoir_states.ndim == 3:
            features = reservoir_states[-1]
        elif reservoir_states.ndim == 2:
            features = reservoir_states
        else:
            raise ValueError("reservoir_states must have shape [seq_len, batch, reservoir] or [batch, reservoir].")
        return self.readout(features)

    def predict_proba(self, reservoir_states: torch.Tensor) -> torch.Tensor:
        return torch.softmax(self.forward(reservoir_states), dim=-1)

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "config": {
                    "reservoir_size": self.reservoir_size,
                    "n_classes": self.n_classes,
                },
                "state_dict": self.state_dict(),
            },
            target,
        )

    @classmethod
    def load(cls, path: str | Path, map_location: str | torch.device = "cpu") -> "LNNClassifier":
        checkpoint = torch.load(path, map_location=map_location)
        model = cls(**checkpoint["config"])
        model.load_state_dict(checkpoint["state_dict"])
        return model


if __name__ == "__main__":
    classifier = LNNClassifier()
    dummy_states = torch.randn(20, 4, 500)
    logits = classifier(dummy_states)
    probs = classifier.predict_proba(dummy_states)
    print(f"Logits shape: {logits.shape}, Probabilities shape: {probs.shape}")
