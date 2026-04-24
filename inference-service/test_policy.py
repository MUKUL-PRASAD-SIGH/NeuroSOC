from policy.engine import PolicyEngine

policy_engine = PolicyEngine()

# simulate real system outputs
events = [
    {"prediction": "WEB_ATTACK", "confidence": 0.95, "user_role": "user"},
    {"prediction": "WEB_ATTACK", "confidence": 0.85, "user_role": "admin"},
    {"prediction": "DDOS", "confidence": 0.7, "user_role": "user"},
    {"prediction": "NORMAL", "confidence": 0.2, "user_role": "user"},
]

print("=== POLICY ENGINE DEMO ===")

for e in events:
    action = policy_engine.evaluate(e)

    print("-----")
    print(f"Prediction : {e['prediction']}")
    print(f"Confidence : {e['confidence']}")
    print(f"User Role  : {e['user_role']}")
    print(f"Decision   : {action}")
