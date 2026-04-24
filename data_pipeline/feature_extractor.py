def extract_features(log):
    return {
        "failed_logins": log["failed_logins"],
        "is_external": 1 if log["ip_type"] == "external" else 0,
        "is_sensitive_action": 1 if log["action"] == "data_exfil" else 0
    }
