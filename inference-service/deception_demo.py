def should_trigger_deception(event):
    """
    Conditions:
    - External IP
    - No identity
    - High confidence (>0.9)
    - High-risk action
    """

    if (
        event["external_ip"]
        and not event["known_user"]
        and event["confidence"] > 0.9
        and event["action"] in ["data_exfil", "privilege_escalation"]
    ):
        return True

    return False


def choose_deception_type():
    return [
        "Decoy API endpoint",
        "Fake credentials (honeytoken)",
        "Canary database row"
    ]


print("=== SELECTIVE DECEPTION DEMO ===")

events = [
    {"external_ip": True, "known_user": False, "confidence": 0.95, "action": "data_exfil"},
    {"external_ip": True, "known_user": True, "confidence": 0.92, "action": "login"},
    {"external_ip": False, "known_user": False, "confidence": 0.93, "action": "privilege_escalation"},
]

for e in events:
    print("-----")
    print(e)

    if should_trigger_deception(e):
        print(" Deception Triggered!")
        for d in choose_deception_type():
            print(f" - {d}")
    else:
        print("No deception (safe handling)")
