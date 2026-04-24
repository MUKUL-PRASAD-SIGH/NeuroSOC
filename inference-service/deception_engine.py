class DeceptionEngine:

    def should_trigger(self, context):
        # Conditions
        if not context.get("external_ip"):
            return False

        if context.get("known_user"):
            return False

        if context.get("confidence", 0) < 0.9:
            return False

        if context.get("risk_level") not in ["HIGH", "CRITICAL"]:
            return False

        return True

    def execute(self, context):
        actions = []

        # 1. Decoy endpoint
        actions.append("ROUTE_TO_DECOY_API")

        # 2. Fake credentials
        actions.append("INJECT_HONEYTOKEN")

        # 3. Canary DB row access
        actions.append("MONITOR_CANARY_ACCESS")

        return actions
