# THE FINAL 4 HOURS — Completion Roadmap

This document outlines the final push to reach 100% production readiness for the NeuroShield ML/AI ecosystem.

---

## 🕒 Hour 1: The Heavy Lift (Colab Training)
**Goal:** Generate production-grade weights using the full CIC-IDS datasets.

| Task | Execution | Priority |
| :--- | :--- | :--- |
| **Full Data Preprocessing** | Sequential | **Critical** |
| **SNN Model Training** (50 epochs) | **Parallel** (Tab 1) | High |
| **LNN Model Training** (30 windows) | **Parallel** (Tab 2) | High |
| **XGBoost Training** (5-fold CV) | **Parallel** (Tab 3) | High |

*   **Tip:** Use the same `scaler.pkl` for all three models to ensure feature alignment.

---

## 🕒 Hour 2: The Handoff & Hybrid Logic
**Goal:** Move weights to the local repository and expand the autonomous loop.

*   **Task 2.1: Transfer Artifacts** (Sequential)
    *   Download `snn_best.pt`, `lnn_best.pt`, `xgboost_best.json`, and `scaler.pkl`.
    *   Place in `/models` and `/data`.
*   **Task 2.2: Retraining Orchestrator Upgrade** (**Independent**)
    *   Modify `retraining-service/main.py` to include `train_snn` and `train_lnn` imports.
    *   Ensure the `RetrainingService` triggers all three retraining paths when feedback threshold is met.

---

## 🕒 Hour 3: Integrated System Validation
**Goal:** Run the full "Cycle of Trust" via Docker Compose.

*   **Task 3.1: The "Kill-Chain" Smoke Test** (Sequential)
    1.  `docker-compose up -d --build`
    2.  Inject SQLI payload via `ingestion-service`.
    3.  Verify: **Inference** detects -> **Sandbox** redirects -> **Feedback** labels.
*   **Task 3.2: Retraining Verification** (Sequential)
    *   Manually push 50 labels to the `feedback` topic.
    *   Verify: **Retraining** triggers -> **Inference** hot-swaps to Version 1.0.1.

---

## 🕒 Hour 4: Analytics & Polish
**Goal:** Final documentation and Dashboard validation.

| Task | Execution | Description |
| :--- | :--- | :--- |
| **Dashboard Bindings** | **Parallel** | Ensure React Dashboard correctly pulls stats from `/api/stats`. |
| **Metrics Generation** | **Parallel** | Extract final F1-scores and Latency metrics for the Master Plan report. |
| **Final Documentation** | Sequential | Update [implemented_so_far.md](./implemented_so_far.md) to 100% status. |

---

## 🚀 Execution Strategy Summary
1.  **Start Colab immediately.** While it trains, work on the **Retraining Orchestrator Upgrade** (Task 2.2) locally.
2.  Once models are ready, do the **Handoff** (Task 2.1) and immediately pivot to **System Validation** (Task 3.1).
3.  Use the final 30 minutes for **Analytics** while the system is running live.
