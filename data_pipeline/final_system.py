from risk_scoring import calculate_risk
from workflow_system import create_case, send_alert
from trust_layer import log_decision
from feature_store import load_features

print("=== FINAL SYSTEM FLOW ===")

features = load_features()

for event in features:

    print("\n=== NEW EVENT ===")

    score, confidence, factors = calculate_risk(event)

    print("\nRisk:", score)
    print("Confidence:", confidence)

    # Decision logic (FIXED)
    if score > 0.8:
        decision = "AUTO_CONTAIN"
    elif score > 0.5:
        decision = "OBSERVE"
    else:
        decision = "LOG_ONLY"

    print("Decision:", decision)

    alert = {
        "risk": score,
        "confidence": confidence,
        "factors": [f[0] for f in factors]
    }

    # Workflow
    if decision != "LOG_ONLY":
        send_alert(alert)
        case_id = create_case(alert)
        print("Case created:", case_id)
    else:
        print("Logged only — no case created")

    # Always log
    log_decision(event, decision)
