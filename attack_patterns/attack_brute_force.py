import requests
import random
import string
import time

LOGIN_TARGET = "http://localhost:8000/api/bank/login"
HONEYPOT_TARGET = "http://localhost:8000/api/bank/honeypot-hit"
VERDICT_TARGET = "http://localhost:8000/api/verdicts/{user_id}"

# fake user
EMAIL = "hacker.bot@novatrust.com"

def random_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

def simulate_typing_delay():
    # attackers type unrealistically fast or random
    return random.uniform(0.01, 0.05)

def attack():
    print("[*] Starting brute force attack...")

    for i in range(50):
        password = random_password()
        honeypot_hit = i % 5 == 0

        payload = {
            "email": EMAIL,
            "password": password,
            "session_id": f"bf-{i}",
        }

        try:
            if honeypot_hit:
                requests.post(HONEYPOT_TARGET, json={"user_id": EMAIL, "source": "bruteforce_sim"}, timeout=5)

            response = requests.post(LOGIN_TARGET, json=payload, timeout=5)
            status = response.status_code

            verdict = "unknown"
            if response.ok:
                user_id = response.json().get("user_id", EMAIL)
                verdict_res = requests.get(VERDICT_TARGET.format(user_id=user_id), timeout=5)
                if verdict_res.ok:
                    verdict = verdict_res.json().get("verdict", "unknown")

            print(f"[{i}] Tried password: {password} | Status: {status} | Verdict: {verdict}")

            time.sleep(simulate_typing_delay())

        except Exception as e:
            print(f"Error: {e}")

    print("[*] Attack complete.")

if __name__ == "__main__":
    attack()