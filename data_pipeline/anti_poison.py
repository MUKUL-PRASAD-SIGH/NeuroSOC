import random

# --- 1. SEPARATE STREAMS ---
human_data = [
    {"features": [1, 0, 1], "label": 1},
    {"features": [0, 0, 0], "label": 0}
]

sandbox_data = [
    {"features": [1, 1, 1], "label": 1},
    {"features": [0, 1, 0], "label": 0}
]

# --- 2. WEIGHTING SYSTEM ---
human_weight = 1.0
sandbox_weight = 0.3

def apply_weights(data, weight):
    return [(d["features"], d["label"], weight) for d in data]

weighted_data = apply_weights(human_data, human_weight) + apply_weights(sandbox_data, sandbox_weight)

print("=== WEIGHTED DATA ===")
for d in weighted_data:
    print(d)


# --- 3. DRIFT DETECTION ---
def detect_drift(old_data, new_data):
    old_avg = sum(sum(x["features"]) for x in old_data) / len(old_data)
    new_avg = sum(sum(x["features"]) for x in new_data) / len(new_data)

    if abs(new_avg - old_avg) > 2:
        return True
    return False

drift = detect_drift(human_data, sandbox_data)

print("\nDrift detected:", drift)


# --- 4. REPLAY VALIDATION ---
def validate_model():
    test_cases = [
        {"features": [1, 0, 1], "expected": 1},
        {"features": [0, 0, 0], "expected": 0}
    ]

    print("\n=== REPLAY VALIDATION ===")
    for t in test_cases:
        predicted = random.choice([0, 1])  # simulate model
        print(f"Expected: {t['expected']}, Got: {predicted}")

validate_model()
