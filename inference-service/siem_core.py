# siem_core.py

usual_geo = "IN"

def detect_threat(log):
    # simple detection logic
    if log["failed_logins"] > 5 and log["geo"] != usual_geo:
        return "BRUTE_FORCE", 0.9
    return "NORMAL", 0.2


def explain(log):
    reasons = []
    if log["failed_logins"] > 5:
        reasons.append("Too many failed logins")
    if log["geo"] != usual_geo:
        reasons.append("Unusual location")
    return reasons


def mitre_map(prediction):
    if prediction == "BRUTE_FORCE":
        return "T1110"
    return "None"
