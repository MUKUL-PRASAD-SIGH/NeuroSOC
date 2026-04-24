from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import torch

try:
    from norse.torch.functional import lif_feed_forward_step
except ImportError:  # pragma: no cover - optional runtime dependency
    lif_feed_forward_step = None


@dataclass(frozen=True)
class ReceptiveFieldConfig:
    n_features: int = 80
    n_neurons_per_feature: int = 5
    timesteps: int = 100


class SpikeEncoder:
    """Gaussian receptive-field spike encoder for normalized 80-feature vectors."""

    def __init__(
        self,
        n_features: int = 80,
        n_neurons_per_feature: int = 5,
        T: int = 100,
    ) -> None:
        self.config = ReceptiveFieldConfig(
            n_features=n_features,
            n_neurons_per_feature=n_neurons_per_feature,
            timesteps=T,
        )
        self.sigma = 1.0 / (2.0 * float(n_neurons_per_feature))
        self.centers = self._create_gaussian_receptive_fields()

    @property
    def input_size(self) -> int:
        return self.config.n_features * self.config.n_neurons_per_feature

    def _create_gaussian_receptive_fields(self) -> torch.Tensor:
        centers = torch.linspace(
            0.0,
            1.0,
            self.config.n_neurons_per_feature,
            dtype=torch.float32,
        )
        return centers.repeat(self.config.n_features, 1)

    def _to_tensor(self, features: np.ndarray | torch.Tensor) -> torch.Tensor:
        tensor = torch.as_tensor(features, dtype=torch.float32)
        if tensor.ndim != 2 or tensor.shape[1] != self.config.n_features:
            raise ValueError(
                f"Expected features with shape [batch, {self.config.n_features}], got {tuple(tensor.shape)}."
            )
        return tensor.clamp(0.0, 1.0)

    def _activation(self, features: np.ndarray | torch.Tensor) -> torch.Tensor:
        tensor = self._to_tensor(features)
        expanded = tensor.unsqueeze(-1)
        centers = self.centers.to(tensor.device).unsqueeze(0)
        activations = torch.exp(-0.5 * ((expanded - centers) / self.sigma) ** 2)
        return activations.clamp(0.0, 1.0)

    def encode(self, features: np.ndarray | torch.Tensor) -> torch.Tensor:
        activations = self._activation(features)
        probs = activations.unsqueeze(0).repeat(self.config.timesteps, 1, 1, 1)
        random_draws = torch.rand_like(probs)
        spikes = (random_draws < probs).to(torch.float32)
        return spikes.reshape(self.config.timesteps, activations.shape[0], self.input_size)

    def encode_deterministic(self, features: np.ndarray | torch.Tensor) -> torch.Tensor:
        activations = self._activation(features)
        periods = torch.where(
            activations > 0,
            torch.ceil(1.0 / torch.clamp(activations, min=1e-6)),
            torch.full_like(activations, float(self.config.timesteps + 1)),
        ).to(torch.int64)
        spikes = torch.zeros(
            self.config.timesteps,
            activations.shape[0],
            self.config.n_features,
            self.config.n_neurons_per_feature,
            dtype=torch.float32,
            device=activations.device,
        )
        for t in range(self.config.timesteps):
            spikes[t] = ((t % periods) == 0).to(torch.float32) * (activations > 0).to(torch.float32)
        return spikes.reshape(self.config.timesteps, activations.shape[0], self.input_size)

    def decode(self, spike_train: torch.Tensor) -> np.ndarray:
        if spike_train.ndim != 3 or spike_train.shape[2] != self.input_size:
            raise ValueError(
                f"Expected spike_train with shape [T, batch, {self.input_size}], got {tuple(spike_train.shape)}."
            )
        firing_rate = spike_train.float().mean(dim=0)
        firing_rate = firing_rate.reshape(
            spike_train.shape[1],
            self.config.n_features,
            self.config.n_neurons_per_feature,
        )
        centers = self.centers.to(firing_rate.device).unsqueeze(0)
        weighted_sum = (firing_rate * centers).sum(dim=-1)
        total_rate = firing_rate.sum(dim=-1)
        decoded = torch.where(total_rate > 0, weighted_sum / total_rate.clamp(min=1e-6), torch.zeros_like(weighted_sum))
        return decoded.cpu().numpy()


if __name__ == "__main__":
    encoder = SpikeEncoder()
    batch = np.random.rand(4, 80).astype(np.float32)
    encoded = encoder.encode(batch)
    decoded = encoder.decode(encoded)
    print(f"Encoded shape: {encoded.shape}")
    print(f"Decoded shape: {decoded.shape}")
