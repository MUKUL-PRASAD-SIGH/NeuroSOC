# Builder A: ML/AI Lead

## Overview of Team Tasks
- **Builder A (ML/AI Lead)**: Neural network components (SNN, LNN, Behavioral Profiler, Models).
- **Builder B (Backend Lead)**: FastAPI, PostgreSQL, Kafka, Sandbox, Microservices.
- **Builder C (Frontend Lead)**: Analyst Dashboard, Bank Simulation Portal.
- **Builder D (DevOps/Research Lead)**: Infrastructure, CI/CD, Docker, Datasets, Research.

## Your Domain & Responsibilities
You own all neural network components: SNN encoder, LNN reservoir, behavioral profiler, model training, and evaluation. 
You are required to achieve ≥ 92% F1-score across models and ensure inference pipeline latency < 100ms.

## Allowed Edit Paths (You may only edit these files/folders)
- `inference-service/core/`
- `inference-service/weights/` (create this if needed)
- `feature-service/` (ML/Data processing logic)
- `models/`
- *Note: Coordinate with Builder B if edits to `inference-service/main.py` are needed for model loading.*

## Relevant Folders & Files to be Aware Of
- `data/` (for `feature_columns.txt`)
- `Docs/`

## Parallel Workflow Strategy
- **Mocking for others**: Provide Builder B with a simple dummy script (e.g., a function that returns a random prediction) so they can test the inference pipeline before your actual models are trained.
- **Independent work**: You can train and evaluate the SNN, LNN, and XGBoost models entirely locally or on a separate machine using the raw datasets, independent of the Docker/FastAPI setup.
- **Integration point**: Once your models (`.pt` or `.pkl`) are trained, drop them into the `weights/` directory and update the loading logic in `inference-service`.

## Detailed Implementation Plan
- **Week 1**: Dataset preprocessing. Deliverable: `preprocess.py` running cleanly, `scaler.pkl` saved.
- **Week 2**: SNN encoder + network. Deliverable: `core/snn/encoder.py`, `network.py`.
- **Week 2-3**: SNN training + eval. Deliverable: `weights/snn_best.pt`, confusion matrix.
- **Week 3**: LNN reservoir + classifier. Deliverable: `core/lnn/reservoir.py`, `weights/lnn_reservoir.pt`.
- **Week 3-4**: XGBoost ensemble classifier. Deliverable: `core/inference/xgboost_classifier.py`, `weights/xgb_classifier.pkl`.
- **Week 4**: Behavioral profiler. Deliverable: `core/behavioral/`.
- **Week 5**: Wire inference pipeline. Deliverable: Coordinate with Builder B to integrate models into `inference_service/main.py`.
- **Week 9-10**: Model evaluation against all datasets. Deliverable: Benchmark results table.