import random

def statistical_score():
    return random.uniform(0, 1)

def sequence_score():
    return random.uniform(0, 1)

def xgboost_score():
    return random.uniform(0, 1)

print("=== HYBRID MODEL DEMO ===")

for i in range(3):
    stat = statistical_score()
    seq = sequence_score()
    xgb = xgboost_score()

    final = (stat + seq + xgb) / 3

    print("-----")
    print(f"Statistical : {stat:.2f}")
    print(f"Sequence    : {seq:.2f}")
    print(f"XGBoost     : {xgb:.2f}")
    print(f"Final Score : {final:.2f}")
