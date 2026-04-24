# policy_hook.py
from policy.engine import PolicyEngine

policy_engine = PolicyEngine()

def apply_policy(prediction, confidence, user_role="user"):
    ctx = {
        "prediction": prediction,
        "confidence": confidence,
        "user_role": user_role
    }
    action = policy_engine.evaluate(ctx)
    print(f"[POLICY] pred={prediction} conf={confidence:.2f} -> {action}")
    return action
