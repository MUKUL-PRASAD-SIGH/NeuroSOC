from siem_core import detect_threat, explain, mitre_map
from policy.engine import PolicyEngine

# sample logs (input)
logs = [
    {"user": "A", "failed_logins": 2, "geo": "IN"},
    {"user": "B", "failed_logins": 7, "geo": "RU"},
    {"user": "C", "failed_logins": 10, "geo": "US"},
]

policy = PolicyEngine()

print("=== MINI SIEM SYSTEM ===")

for log in logs:
    prediction, confidence = detect_threat(log)

    context = {
        "prediction": prediction,
        "confidence": confidence,
        "user_role": "user"
    }

    decision = policy.evaluate(context)

    print("\n-----")
    print(f"Log: {log}")
    print(f"Prediction: {prediction}")
    print(f"Confidence: {confidence}")
    print(f"MITRE: {mitre_map(prediction)}")

    print("Why triggered:")
    for r in explain(log):
        print(f" - {r}")

    print(f"Final Decision: {decision}")
