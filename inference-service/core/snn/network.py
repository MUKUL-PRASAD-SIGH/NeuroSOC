from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn

try:
    from norse.torch import LIFRecurrentCell
except ImportError:  # pragma: no cover - optional runtime dependency
    LIFRecurrentCell = None


CLASS_NAMES = [
    "BENIGN",
    "DDOS",
    "BRUTE_FORCE",
    "RECONNAISSANCE",
    "WEB_ATTACK",
    "BOT",
    "OTHER",
]


@dataclass
class _FallbackState:
    z: torch.Tensor
    v: torch.Tensor


class _FallbackLIFRecurrentCell(nn.Module):
    """Simple recurrent spiking approximation when Norse is unavailable locally."""

    def __init__(self, input_size: int, hidden_size: int) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.input_linear = nn.Linear(input_size, hidden_size)
        self.recurrent_linear = nn.Linear(hidden_size, hidden_size, bias=False)
        self.threshold = 0.5
        self.decay = 0.8

    def forward(
        self,
        inputs: torch.Tensor,
        state: _FallbackState | None = None,
    ) -> tuple[torch.Tensor, _FallbackState]:
        batch_size = inputs.shape[0]
        if state is None:
            device = inputs.device
            zeros = torch.zeros(batch_size, self.hidden_size, device=device, dtype=inputs.dtype)
            state = _FallbackState(z=zeros, v=zeros)

        membrane = self.decay * state.v + self.input_linear(inputs) + self.recurrent_linear(state.z)
        spikes = (torch.sigmoid(membrane) > self.threshold).to(inputs.dtype)
        next_state = _FallbackState(z=spikes, v=membrane)
        return spikes, next_state


def _build_lif_cell(input_size: int, hidden_size: int) -> nn.Module:
    if LIFRecurrentCell is not None:
        return LIFRecurrentCell(input_size, hidden_size)
    return _FallbackLIFRecurrentCell(input_size, hidden_size)


class SNNAnomalyDetector(nn.Module):
    """Two-layer recurrent spiking detector with anomaly score head."""

    CLASS_NAMES = CLASS_NAMES

    def __init__(
        self,
        input_size: int = 400,
        hidden_sizes: list[int] | None = None,
        n_classes: int = 7,
    ) -> None:
        super().__init__()
        hidden_sizes = hidden_sizes or [256, 128]
        self.input_size = input_size
        self.hidden_sizes = hidden_sizes
        self.n_classes = n_classes

        self.lif1 = _build_lif_cell(input_size, hidden_sizes[0])
        self.norm1 = nn.BatchNorm1d(hidden_sizes[0])
        self.lif2 = _build_lif_cell(hidden_sizes[0], hidden_sizes[1])
        self.norm2 = nn.BatchNorm1d(hidden_sizes[1])
        self.readout = nn.Linear(hidden_sizes[1], n_classes)

    def _apply_norm(self, norm: nn.BatchNorm1d, tensor: torch.Tensor) -> torch.Tensor:
        if tensor.shape[0] < 2 and self.training:
            return tensor
        return norm(tensor)

    def forward(
        self,
        spike_train: torch.Tensor,
        return_trace: bool = False,
    ) -> tuple[torch.Tensor, torch.Tensor] | tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if spike_train.ndim != 3 or spike_train.shape[2] != self.input_size:
            raise ValueError(
                f"Expected spike_train with shape [T, batch, {self.input_size}], got {tuple(spike_train.shape)}."
            )

        state1 = None
        state2 = None
        traces: list[torch.Tensor] = []

        for timestep in range(spike_train.shape[0]):
            z1, state1 = self.lif1(spike_train[timestep], state1)
            z1 = self._apply_norm(self.norm1, z1)
            z2, state2 = self.lif2(z1, state2)
            z2 = self._apply_norm(self.norm2, z2)
            traces.append(z2)

        trace_tensor = torch.stack(traces, dim=0)
        pooled = trace_tensor[-10:].mean(dim=0) if trace_tensor.shape[0] >= 10 else trace_tensor.mean(dim=0)
        logits = self.readout(pooled)
        benign_probs = torch.softmax(logits, dim=-1)[:, 0]
        anomaly_score = 1.0 - benign_probs
        if return_trace:
            return logits, anomaly_score, trace_tensor
        return logits, anomaly_score

    def apply_stdp(
        self,
        trace_tensor: torch.Tensor,
        strength: float = 1e-3,
        window_size: int = 5,
        coactivation_threshold: float = 0.7,
    ) -> None:
        if trace_tensor.ndim != 3:
            raise ValueError("trace_tensor must have shape [T, batch, hidden_size].")
        if trace_tensor.shape[0] < window_size:
            return

        activity = trace_tensor.float().mean(dim=1)
        windows: list[torch.Tensor] = []
        for start in range(0, activity.shape[0] - window_size + 1):
            windows.append(activity[start : start + window_size].mean(dim=0))
        window_activity = torch.stack(windows, dim=0)
        cofire = torch.einsum("wh,wj->hj", window_activity, window_activity) / max(window_activity.shape[0], 1)
        neuron_score = cofire.mean(dim=1)
        active_neurons = neuron_score > coactivation_threshold
        if not torch.any(active_neurons):
            return

        with torch.no_grad():
            self.readout.weight[:, active_neurons] += strength * torch.sign(
                torch.where(
                    self.readout.weight[:, active_neurons] == 0,
                    torch.ones_like(self.readout.weight[:, active_neurons]),
                    self.readout.weight[:, active_neurons],
                )
            )

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "config": {
                    "input_size": self.input_size,
                    "hidden_sizes": self.hidden_sizes,
                    "n_classes": self.n_classes,
                },
                "state_dict": self.state_dict(),
            },
            target,
        )

    @classmethod
    def load(cls, path: str | Path, map_location: str | torch.device = "cpu") -> "SNNAnomalyDetector":
        checkpoint = torch.load(path, map_location=map_location)
        model = cls(**checkpoint["config"])
        model.load_state_dict(checkpoint["state_dict"])
        return model


if __name__ == "__main__":
    model = SNNAnomalyDetector()
    dummy = torch.zeros(100, 4, 400)
    logits, score = model(dummy)
    print(f"Logits: {logits.shape}, Score: {score.shape}")
