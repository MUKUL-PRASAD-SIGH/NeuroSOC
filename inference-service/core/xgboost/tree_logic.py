from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OverrideResult:
    label: str
    confidence: float
    overridden: bool
    reason: str


class TreeLogicOverride:
    """Hard safety overrides layered on top of the XGBoost prediction."""

    def apply(
        self,
        features: dict,
        xgb_prediction: str,
        xgb_confidence: float,
    ) -> tuple[str, float]:
        result = self.evaluate(features, xgb_prediction, xgb_confidence)
        return result.label, result.confidence

    def evaluate(
        self,
        features: dict,
        xgb_prediction: str,
        xgb_confidence: float,
    ) -> OverrideResult:
        packet_rate = float(features.get("packet_rate", 0.0))
        syn_ratio = float(features.get("syn_ratio", 0.0))
        unique_dst_ports = int(features.get("unique_dst_ports", 0))
        login_attempts = int(features.get("login_attempts", 0))
        all_different_passwords = bool(features.get("all_different_passwords", False))

        if packet_rate > 10_000 and syn_ratio > 0.95:
            return OverrideResult("DDOS", 0.99, True, "packet_rate/syn_ratio")
        if unique_dst_ports > 1_000:
            return OverrideResult("RECONNAISSANCE", 0.95, True, "unique_dst_ports")
        if login_attempts > 50 and all_different_passwords:
            return OverrideResult("BRUTE_FORCE", 0.97, True, "credential_stuffing_pattern")
        return OverrideResult(xgb_prediction, xgb_confidence, False, "model_prediction")


if __name__ == "__main__":
    override = TreeLogicOverride()
    label, confidence = override.apply(
        {"packet_rate": 15000, "syn_ratio": 0.97},
        xgb_prediction="BENIGN",
        xgb_confidence=0.52,
    )
    print(f"Override result: {label} ({confidence:.2f})")
