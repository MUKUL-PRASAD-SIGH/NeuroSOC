import yaml

class PolicyEngine:
    def __init__(self, policy_path="policy.yaml"):
        with open(policy_path, "r") as f:
            self.policy = yaml.safe_load(f)["rules"]

    def evaluate(self, context):
        for rule in self.policy:
            if self._match(rule["conditions"], context):
                return {
                    "action": rule["action"],
                    "priority": rule["priority"],
                    "rule": rule["name"]
                }
        return {"action": "LOG_ONLY", "priority": "P4"}

    def _match(self, conditions, context):
        for key, value in conditions.items():
            if key == "confidence_gt":
                if context.get("confidence", 0) <= value:
                    return False
            elif context.get(key) != value:
                return False
        return True
