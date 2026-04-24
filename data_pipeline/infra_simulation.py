import queue
import random

# ----------------------------
# KAFKA SIMULATION
# ----------------------------
partitions = {
    "user1": queue.Queue(),
    "user2": queue.Queue()
}

def send_event(user, event):
    partitions[user].put(event)


def process_events():
    print("=== PROCESSING STREAM ===")

    for user, q in partitions.items():
        while not q.empty():
            event = q.get()

            print(f"[{user}] Processing:", event)


# ----------------------------
# BACKPRESSURE (LIMIT)
# ----------------------------
MAX_QUEUE = 5

def safe_send(user, event):
    if partitions[user].qsize() > MAX_QUEUE:
        print(f"⚠️ackpressure triggered for {user}")
        return
    send_event(user, event)


# ----------------------------
# STORAGE SIMULATION
# ----------------------------
hot_storage = []   # Elasticsearch
cold_storage = []  # S3-like

def store_event(event):
    if event["risk"] > 0.7:
        hot_storage.append(event)
    else:
        cold_storage.append(event)


# ----------------------------
# DEMO FLOW
# ----------------------------
print("=== INFRASTRUCTURE SIMULATION ===")

# generate events
for i in range(10):
    user = random.choice(["user1", "user2"])
    event = {
        "id": i,
        "risk": random.random()
    }

    safe_send(user, event)
    store_event(event)

process_events()

print("\nHot Storage (Elasticsearch):", len(hot_storage))
print("Cold Storage (S3):", len(cold_storage))
