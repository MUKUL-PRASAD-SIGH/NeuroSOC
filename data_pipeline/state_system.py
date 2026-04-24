import time

# ---------------------------
# SESSION STORE (like Redis)
# ---------------------------
session_store = {}

def create_session(session_id, data, ttl=5):
    session_store[session_id] = {
        "data": data,
        "expiry": time.time() + ttl
    }

def get_session(session_id):
    session = session_store.get(session_id)

    if not session:
        return None

    # expire check
    if time.time() > session["expiry"]:
        del session_store[session_id]
        return None

    return session["data"]


# ---------------------------
# USER PROFILE (baseline)
# ---------------------------
user_profiles = {
    "user1": {"avg_failed_logins": 2},
    "user2": {"avg_failed_logins": 5}
}

def get_user_profile(user):
    return user_profiles.get(user, {"avg_failed_logins": 1})


# ---------------------------
# SYSTEM FLOW
# ---------------------------
print("=== STATE MANAGEMENT SYSTEM ===")

# simulate incoming request
user = "user1"
session_id = "sess_123"

# store session (short-lived)
create_session(session_id, {"failed_logins": 10})

session_data = get_session(session_id)
profile = get_user_profile(user)

print("\nSession Data:", session_data)
print("User Baseline:", profile)

# simulate decision logic
if session_data:
    if session_data["failed_logins"] > profile["avg_failed_logins"]:
        print("⚠️nomaly detected (above baseline)")

# wait to show expiry
time.sleep(6)

print("\nAfter TTL (session expired):", get_session(session_id))
