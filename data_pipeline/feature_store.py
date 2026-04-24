import json
import os

def load_features():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "features.json")

    with open(file_path, "r") as f:
        return json.load(f)
