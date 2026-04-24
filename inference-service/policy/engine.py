import yaml

class PolicyEngine:
    def __init__(self, config_path="policy.yaml"):
        with open(config_path, "r") as f:
            self.rules = yaml.safe_load(f)["rules"]

    def evaluate(self, context):
        for rule in self.rules:
            cond = rule.get("condition", {})

            if "user_role" in cond and cond["user_role"] != context["user_role"]:
                continue

            if "min_confidence" in cond and context["confidence"] < cond["min_confidence"]:
                continue

            if "attack_type" in cond and cond["attack_type"] != context["prediction"]:
                continue

            return rule["action"]

        return "LOG_ONLY"
