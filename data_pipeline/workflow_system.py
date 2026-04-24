import uuid
import time

# ----------------------------
# CASE MANAGEMENT
# ----------------------------
cases = {}

def create_case(alert):
    case_id = str(uuid.uuid4())[:8]

    cases[case_id] = {
        "alert": alert,
        "status": "OPEN",
        "notes": [],
        "created_at": time.time()
    }

    print(f"\n Case created: {case_id}")
    return case_id


def add_note(case_id, note):
    cases[case_id]["notes"].append(note)


def close_case(case_id):
    cases[case_id]["status"] = "CLOSED"


# ----------------------------
# ALERTING (SIMULATION)
# ----------------------------
def send_alert(alert):
    print("\n Alert sent to SOC (Slack/PagerDuty simulated)")
    print(alert)


# ----------------------------
# INVESTIGATION
# ----------------------------
def investigate(case_id):
    print(f"\nInvestigating case {case_id}")
    print(cases[case_id])


# ----------------------------
# DEMO FLOW
# ----------------------------
alert = {
    "risk": 0.82,
    "confidence": "High",
    "factors": ["Failed logins", "New device"]
}

send_alert(alert)

case_id = create_case(alert)

investigate(case_id)

add_note(case_id, "Looks suspicious, checking further...")
add_note(case_id, "User confirmed unknown activity")

close_case(case_id)

print("\nFinal Case State:")
print(cases[case_id])
