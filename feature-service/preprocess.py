from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_PREPROCESS_PATH = REPO_ROOT / "datasets" / "preprocess.py"


def _load_dataset_preprocess_module():
    spec = importlib.util.spec_from_file_location("neuroshield_dataset_preprocess", DATASET_PREPROCESS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load dataset preprocessing module from {DATASET_PREPROCESS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    """
    Backward-compatible entrypoint kept for older docs/scripts.

    Phase 3's real preprocessing pipeline now lives in `datasets/preprocess.py`.
    This shim delegates to that implementation so callers do not keep hitting
    the old random-data placeholder path.
    """
    module = _load_dataset_preprocess_module()
    return int(module.main())


if __name__ == "__main__":
    sys.exit(main())
