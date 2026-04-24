# Builder Progress Script

This is a consolidated progress script for all builders based on the work plan and current repository structure.

## 1. Builder A — ML/AI Lead

### Work Done So Far
- Defined responsibilities around SNN encoder, LNN reservoir, behavioral profiler, model training, and evaluation.
- Identified target metrics: ≥ 92% F1-score and inference latency < 100ms.
- Set integration expectations for `inference-service` and data preprocessing in `feature-service`.
- Documented a weekly plan covering dataset preprocessing, SNN/LNN development, XGBoost classifier, and behavioral profiler.

### Challenges Faced
- Unclear dataset readiness and exact feature schema early in development.
- Need to coordinate model loading with backend without blocking the backend build.
- Ensuring concrete benchmark results instead of optimistic claims.

### How I Solved It
- Used the repository `data/feature_columns.txt` and `feature-service/preprocess.py` to align feature input expectations.
- Planned a mock inference component to let Builder B complete API wiring before actual model weights are available.
- Committed to saving and tracking real evaluation results in `models/model_version.json` and documented performance targets in `Docs/README.md`.

### Doubts / Questions with Answers
- Q: Should Builder A develop models before backend APIs exist?  
  A: Yes. Build models and a mock prediction wrapper in parallel, then swap real inference logic into `inference-service/main.py`.
- Q: Where should the trained weights go?  
  A: In `inference-service/weights/` or a shared model directory, with actual loading coordinated with Builder B.
- Q: Which performance metric matters most?  
  A: F1-score is primary, with latency as a second constraint for real-time inference.

## 2. Builder B — Backend Lead

### Work Done So Far
- Defined server-side domain ownership: FastAPI, PostgreSQL, Kafka, sandbox systems, and report generation.
- Documented allowed edit paths, integration points, and a backend roadmap.
- Planned independent development of mock endpoints and data flows so frontend work can start early.

### Challenges Faced
- Needing a backend API contract before the frontend and ML components were fully ready.
- Coordinating multi-service architecture across `inference-service`, `feature-service`, `feedback-service`, `ingestion-service`, and `sandbox-service`.
- Determining where to store and access inference results and feedback labels.

### How I Solved It
- Proposed a dummy FastAPI implementation with hardcoded JSON and WebSocket streams, enabling Builder C to build UI early.
- Planned modular route design in `inference-service/main.py` so model loading can be replaced cleanly later.
- Aligned Kafka and DB work with service ownership notes in the README files and `docker-compose.yml`.

### Doubts / Questions with Answers
- Q: Can the backend start with dummy data?  
  A: Yes. Use mocked API responses first, then switch to live data once models and DB schemas are available.
- Q: Where should the sandbox and honeypot run?  
  A: In an isolated service container, preferably with `network_mode: none` as planned in the README.
- Q: Should inference-service import ML libraries?  
  A: Keep API gateway light. The inference service can own ML imports while `inference-service/main.py` stays a clean route layer.

## 3. Builder C — Frontend Lead

### Work Done So Far
- Defined the UI domain: NeuroShield analyst dashboard and NovaTrust bank portal.
- Documented a plan for mock APIs, charts, state management, and integration with backend endpoints.
- Identified `dashboard/` and `simulation_portal/` as the main frontend work areas.

### Challenges Faced
- Backend endpoints and schemas were not finalized at the start.
- Need to build two separate interfaces that can both operate on mocked data.
- Ensuring the UI can integrate smoothly with backend WebSocket and REST endpoints later.

### How I Solved It
- Recommended mock JSON responses and MSW/`json-server` for front-end integration during development.
- Focused on reusable UI components, chart widgets, and responsive layout independent of live data.
- Kept API endpoint references generic so they can be updated later when Builder B finalizes the backend.

### Doubts / Questions with Answers
- Q: Should frontend wait for backend implementation?  
  A: No. Use mocks and component-first development to move in parallel.
- Q: Which ports should the dashboard and portal use?  
  A: Dashboard on `:3000` and bank portal on `:3001`, as noted in the plan.
- Q: What is the key integration point?  
  A: Swapping mock calls with real local endpoints once Builder B exposes FastAPI endpoints.

## 4. Builder D — DevOps/Research Lead

### Work Done So Far
- Documented infrastructure and research ownership, including Docker, CI/CD, dataset management, and academic validation.
- Identified `docker-compose.yml`, `monitoring/`, and `.github/workflows/` as primary control points.
- Defined a schedule for dataset placement, CI setup, and demo environment readiness.

### Challenges Faced
- Aligning service dependencies and Docker builds across multiple teams.
- Sourcing and organizing datasets without blocking model training or backend workflows.
- Turning research claims into verifiable documentation and benchmark evidence.

### How I Solved It
- Prioritized a one-command environment and CI pipeline so team members can verify builds quickly.
- Recommended placing datasets in a shared folder and using clear service contracts in `docker-compose.yml`.
- Committed to research logs in `Docs/` and to maintaining accurate claims in `Docs/README.md`.

### Doubts / Questions with Answers
- Q: Who owns `docker-compose.yml`?  
  A: Builder D is the primary owner, but edits should be coordinated with Builder B for service changes.
- Q: How should CI handle incomplete services?  
  A: Use service smoke tests and separate build stages; allow frontend/backend/model packages to compile independently.
- Q: What does research validation require?  
  A: Actual benchmark data, dataset provenance, and a clear statement of assumptions in the Docs folder.

## 5. Cross-Builder Integration Notes

- Builder A should provide a simple dummy prediction wrapper to Builder B until actual models are available.
- Builder B should expose stable mock API contracts so Builder C can complete UI work.
- Builder D should make sure Docker and CI are ready to build the current service stack with placeholder resources.
- All teams should update `Docs/TEAM_ROLES.md`, `Docs/MASTER_PLAN.md`, and the builder READMEs as work progresses.

---

### File purpose
This document is intended as a progress and handoff script for the team. It is based on current repository structure and builder planning notes in the `builder*/README.md` files.
