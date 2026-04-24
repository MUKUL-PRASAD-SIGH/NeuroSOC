def calculate_risk(event):
    score = 0
    factors = []

    # Map features safely
    new_device = event.get("is_external", 0)
    off_hours = event.get("is_sensitive_action", 0)
    failed_logins = event.get("failed_logins", 0)

    # --- RULES ---

    if new_device:
        score += 0.2
        factors.append(("External access", 0.2))

    if off_hours:
        score += 0.15
        factors.append(("Sensitive action timing", 0.15))

    if failed_logins > 5:
        score += 0.3
        factors.append(("Multiple failed logins", 0.3))

    if failed_logins > 8:
        score += 0.17
        factors.append(("Abnormal login pattern", 0.17))

    score = min(score, 1.0)

    # Confidence
    if score > 0.8:
        confidence = "High"
    elif score > 0.5:
        confidence = "Medium"
    else:
        confidence = "Low"

    return score, confidence, factors
