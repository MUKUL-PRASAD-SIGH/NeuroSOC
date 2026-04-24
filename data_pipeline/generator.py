import random

users = ["user1", "user2", "admin"]
geos = ["IN", "US", "RU"]

def generate_log():
    return {
        "user": random.choice(users),
        "failed_logins": random.randint(0, 10),
        "geo": random.choice(geos),
        "ip_type": random.choice(["internal", "external"]),
        "action": random.choice(["login", "data_exfil", "transfer"])
    }

def generate_logs(n=10):
    return [generate_log() for _ in range(n)]
