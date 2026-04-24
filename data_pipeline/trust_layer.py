import time

audit_log = []

def log_decision(event, decision):
    record = {
        "event": event,
        "decision": decision,
        "timestamp": time.time()
    }
    audit_log.append(record)

    print("\n Audit Log Entry:")
    print(record)
