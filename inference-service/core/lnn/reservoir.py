from __future__ import annotations

import torch
from torch import nn


class LiquidReservoir(nn.Module):
    """Fixed sparse liquid-state reservoir for sequence modeling."""

    def __init__(
        self,
        input_size: int = 80,
        reservoir_size: int = 500,
        spectral_radius: float = 0.9,
        leak_rate: float = 0.3,
        sparsity: float = 0.1,
        seed: int = 42,
    ) -> None:
        super().__init__()
        self.input_size = input_size
        self.reservoir_size = reservoir_size
        self.target_spectral_radius = spectral_radius
        self.leak_rate = leak_rate
        self.sparsity = sparsity
        self.seed = seed
        self._init_reservoir_weights()

    def _init_reservoir_weights(self) -> None:
        generator = torch.Generator(device="cpu")
        generator.manual_seed(self.seed)

        w_res = torch.randn(self.reservoir_size, self.reservoir_size, generator=generator) * 0.1
        mask = (torch.rand(self.reservoir_size, self.reservoir_size, generator=generator) < self.sparsity).float()
        w_res = w_res * mask
        current_radius = self._compute_radius(w_res)
        if current_radius < 1e-6:
            w_res.fill_diagonal_(1.0)
            current_radius = self._compute_radius(w_res)
        w_res = w_res * (self.target_spectral_radius / current_radius)

        w_input = torch.randn(self.reservoir_size, self.input_size, generator=generator) * 0.1

        self.register_buffer("W_res", w_res)
        self.register_buffer("W_input", w_input)

    def _compute_radius(self, matrix: torch.Tensor) -> float:
        eigenvalues = torch.linalg.eigvals(matrix.cpu())
        return float(torch.max(torch.abs(eigenvalues)).item())

    def compute_spectral_radius(self) -> float:
        return self._compute_radius(self.W_res)

    def forward(
        self,
        x: torch.Tensor,
        initial_state: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if x.ndim != 3 or x.shape[2] != self.input_size:
            raise ValueError(
                f"Expected input with shape [seq_len, batch, {self.input_size}], got {tuple(x.shape)}."
            )

        seq_len, batch_size, _ = x.shape
        if initial_state is None:
            state = torch.zeros(batch_size, self.reservoir_size, device=x.device, dtype=x.dtype)
        else:
            state = initial_state

        all_states: list[torch.Tensor] = []
        w_res = self.W_res.to(x.device, dtype=x.dtype)
        w_input = self.W_input.to(x.device, dtype=x.dtype)

        for timestep in range(seq_len):
            recurrent = state @ w_res.T
            driven = x[timestep] @ w_input.T
            candidate = torch.tanh(recurrent + driven)
            state = (1.0 - self.leak_rate) * state + self.leak_rate * candidate
            all_states.append(state)

        all_states_tensor = torch.stack(all_states, dim=0)
        return all_states_tensor, state


if __name__ == "__main__":
    reservoir = LiquidReservoir()
    print(f"Spectral radius: {reservoir.compute_spectral_radius():.3f}")
    sample = torch.randn(20, 4, 80)
    states, final_state = reservoir(sample)
    print(f"States shape: {states.shape}, Final shape: {final_state.shape}")
