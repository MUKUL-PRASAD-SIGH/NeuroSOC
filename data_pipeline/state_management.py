import time

# --- SESSION STORE (simulating Redis with TTL) ---
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

    if time.time() > session["expiry"]:
        del session_store[session_id]
        return None

    return session["data"]


# --- USER PROFILE STORE (aggregated baseline) ---
user_profiles = {
    "user1": {"avg_failed_logins": 2},
    "user2": {"avg_failed_logins": 5}
}

def get_user_profile(user):
    return user_profiles.get(user, {"avg_failed_logins": 1})


# --- DEMO FLOW ---
print("=== STATE MANAGEMENT DEMO ===")

# create session (short-lived)
create_session("sess1", {"failed_logins": 10})

print("\nSession Data:", get_session("sess1"))

# wait for expiry
time.sleep(6)

print("After TTL:", get_session("sess1"))


# use user profile
profile = get_user_profile("user1")
print("\nUser Profile:", profile)
