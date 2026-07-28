import requests
import time
import random
import uuid

# Configuration
BASE_URL = "http://localhost:8000/api"
TRANSFER_URL = f"{BASE_URL}/bank/transfer"
WEB_ATTACK_URL = f"{BASE_URL}/bank/web-attack-detected"
HONEYPOT_URL = f"{BASE_URL}/bank/honeypot-hit"

USER_ID = "hacker.sqli@novatrust.com"
SESSION_ID = f"attack-web-{uuid.uuid4().hex[:8]}"

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE users; --",
    "1 UNION SELECT username, password FROM users--",
    "admin'--",
    "')) OR 1=1--"
]

def simulate_web_attack():
    print(f"[*] Starting SQL Injection / Web Attack Simulation on session {SESSION_ID}")
    
    # 1. Trigger the Honeypot (Confirm Routing Number field in UI)
    print("[!] Triggering Honeypot (hidden field)...")
    try:
        res = requests.post(HONEYPOT_URL, json={
            "source": "transfer_form_hidden_field",
            "user_id": USER_ID,
            "session_id": SESSION_ID
        }, timeout=5)
        print(f"    Honeypot Response: {res.status_code} | Verdict: {res.json().get('verdict')}")
    except Exception as e:
        print(f"    Error: {e}")

    # 2. Sequential SQLi Attempts in the Transfer Memo
    for i, payload in enumerate(SQLI_PAYLOADS):
        print(f"[!] Attempt {i+1}: Injecting SQLi into Memo field...")
        
        # Simulate the portal's client-side detection report
        try:
            requests.post(WEB_ATTACK_URL, json={
                "attack_type": "SQLI",
                "payload": payload,
                "user_id": USER_ID,
                "session_id": SESSION_ID
            }, timeout=5)
        except Exception:
            pass

        # Perform the actual "malicious" transfer
        transfer_payload = {
            "user_id": USER_ID,
            "session_id": SESSION_ID,
            "recipient": "Offshore Account 9982",
            "amount": 50000.00,
            "memo": payload
        }
        
        try:
            res = requests.post(TRANSFER_URL, json=transfer_payload, timeout=5)
            data = res.json()
            print(f"    Payload: {payload}")
            print(f"    Status: {res.status_code} | Verdict: {data.get('verdict')} | Sandbox: {data.get('sandbox', {}).get('active')}")
        except Exception as e:
            print(f"    Error: {e}")

        # Rapid succession to trigger SNN/LNN anomaly detection
        time.sleep(random.uniform(0.1, 0.3))

    print("[*] Web Attack Simulation complete.")

if __name__ == "__main__":
    simulate_web_attack()
