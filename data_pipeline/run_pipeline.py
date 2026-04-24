from generator import generate_logs
from feature_extractor import extract_features
from feature_store import save_features

logs = generate_logs(10)

features = [extract_features(log) for log in logs]

save_features(features)

print("Pipeline complete. Features saved.")
