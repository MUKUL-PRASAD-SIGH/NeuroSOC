# THE FINAL 4 HOURS — Completion Playbook

This document is the execution guide for the final project push. Use the **Developer Prompts** provided for each task to trigger the work.

---

## 🕒 Hour 1: The Heavy Lift (Full-Scale Training)
**Goal:** Transition from sample data to production-grade weights in Google Colab.

### Task 1.1: Preprocessing & Feature Contract (Sequential)
*   **Developer Prompt:** 
    ```python
    # Run in Colab Cell
    !python datasets/preprocess.py --raw-dir /content/CIC_DATA --max-rows 1000000 --balance-smote True
    ```
*   **Expected Outcome:** `scaler.pkl` and `feature_columns.txt` generated. **DO NOT** lose these; they are the "Feature Contract" for the whole system.

### Task 1.2: Parallel Model Training (Parallel)
*   **SNN (Tab 1) Prompt:** `!python retraining-service/train_snn.py --epochs 50 --batch-size 256 --device cuda`
*   **LNN (Tab 2) Prompt:** `!python retraining-service/train_lnn.py --windows 30 --hidden-size 128 --device cuda`
*   **XGBoost (Tab 3) Prompt:** `!python retraining-service/train_xgboost.py --n-estimators 500 --max-depth 8`

---

## 🕒 Hour 2: Handoff & Orchestrator Expansion
**Goal:** Integrate the "brains" and enable autonomous triple-model retraining.

### Task 2.1: Artifact Handoff (Sequential)
*   **Developer Prompt:** Download the 4 files (`snn_best.pt`, `lnn_best.pt`, `xgboost_best.json`, `scaler.pkl`) and upload them to `/models` and `/data` in the local repo.
*   **Action:** Update `models/model_version.json` with the new F1-scores and timestamps.

### Task 2.2: Triple-Model Retraining Expansion (Independent)
*   **Developer Prompt:** 
    *"Refactor `retraining-service/main.py`. Import `train_snn` and `train_lnn`. Update the `RetrainingService.run_once()` logic so that it triggers a retraining cycle for ALL THREE models sequentially when the `RETRAIN_MIN_FEEDBACK_SAMPLES` threshold is hit."*

---

## 🕒 Hour 3: Integrated "Kill-Chain" Validation
**Goal:** Verify the autonomous loop: **Inference -> Sandbox -> Feedback -> Retraining**.

### Task 3.1: Stack Deployment
*   **Developer Prompt:** `docker-compose up -d --build && docker logs -f neuroshield-inference`
*   **Verification:** Ensure the logs show `Decision Engine loaded version X.X.X with SNN, LNN, and XGBoost components.`

### Task 3.2: Simulated Attack Trace
*   **Developer Prompt:** 
    ```bash
    # Send a malicious payload to trigger the Sandbox
    curl -X POST http://localhost:8000/analyze \
    -H "Content-Type: application/json" \
    -d '{"session_id": "hacker-001", "features": [ ... 80 features ... ]}'
    ```
*   **Trace:** Monitor `neuroshield-feedback` logs to confirm it generated a `WEB_ATTACK` label for PostgreSQL.

---

## 🕒 Hour 4: Dashboard & Final Metrics
**Goal:** Connect the UI and verify analytics.

### Task 4.1: Dashboard Sync
*   **Developer Prompt:** *"Verify `dashboard/src/services/dashboardApi.js` is pointing to the correct Inference WebSocket. Open the dashboard and confirm the 'Model Status' cards show the current version from `model_version.json`."*

### Task 4.2: Final Analytics Export
*   **Developer Prompt:** 
    ```bash
    # Extract results
    ls retraining-service/results/*.png
    ```
*   **Action:** Copy the confusion matrices and final performance table into the [Walkthrough report](../Docs/WALKTHROUGH.md).

---

## 🚀 Execution Strategy
1.  **Immediate Action:** Open 3 Colab tabs and start **Hour 1** training.
2.  **During Training:** Perform the code expansion in **Task 2.2** locally.
3.  **The Pivot:** As soon as models download, execute **Hour 3** in one go.
