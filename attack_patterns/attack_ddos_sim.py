import requests
import time
import uuid
import random

TARGET = "http://localhost:8080/ingest"

def generate_packet():
    return {
        "packet_id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "src_ip": f"192.168.1.{random.randint(1,254)}",
        "dst_ip": "10.0.0.1",
        "src_port": random.randint(1024, 65535),
        "dst_port": 80,
        "protocol": "TCP",
        "length": random.randint(40, 1500),
        "flags": {"SYN": 1, "ACK": 0, "FIN": 0},
        "ttl": 64
    }

def ddos():
    print("[*] Starting DDoS simulation...")
    sent_ok = 0
    sent_fail = 0

    for _ in range(1000):
        batch = [generate_packet() for _ in range(50)]
        payload = {
            "events": batch,
            "session_id": f"ddos-{uuid.uuid4()}",
            "user_id": "ddos-simulator",
        }

        try:
            response = requests.post(TARGET, json=payload, timeout=5)
            if response.ok:
                sent_ok += len(batch)
            else:
                sent_fail += len(batch)
        except Exception:
            sent_fail += len(batch)

    print(f"[*] DDoS simulation complete. accepted_packets={sent_ok} failed_packets={sent_fail}")

if __name__ == "__main__":
    ddos()