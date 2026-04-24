from __future__ import annotations

from typing import Any

__all__ = ["DecisionEngine", "ThreatVerdict"]


def __getattr__(name: str) -> Any:
    if name in {"DecisionEngine", "ThreatVerdict"}:
        from .engine import DecisionEngine, ThreatVerdict

        exports = {
            "DecisionEngine": DecisionEngine,
            "ThreatVerdict": ThreatVerdict,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
