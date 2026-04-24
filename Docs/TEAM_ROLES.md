# TEAM ROLES & RESPONSIBILITY MATRIX — NeuroShield

---

## Team Overview

| # | Role | Code Name | Primary Domain | Antigravity Usage |
|---|---|---|---|---|
| 1 | **ML/AI Lead** | `@ml` | SNN, LNN, Behavioral Profiler | High |
| 2 | **Backend Lead** | `@backend` | FastAPI, DB, Kafka, Sandbox | High |
| 3 | **Frontend Lead** | `@frontend` | Dashboard, Bank Portal, UX | Very High |
| 4 | **DevOps/Research Lead** | `@devops` | Infra, CI/CD, Datasets, Research | Medium |

---

## Member 1 — ML/AI Lead (@ml)

### Core Responsibility
Owns all neural network components: SNN encoder, LNN reservoir, behavioral profiler, model training, and evaluation.

### Week-by-Week Tasks

| Week | Task | Antigravity Prompt Section | Deliverable |
|---|---|---|---|
| 1 | Dataset preprocessing | Phase 1.2 | `preprocess.py` running cleanly, `scaler.pkl` saved |
| 2 | SNN encoder + network | Phase 2.1, 2.2 | `core/snn/encoder.py`, `network.py` |
| 2–3 | SNN training + eval | Phase 2.3 | `weights/snn_best.pt`, confusion matrix |
| 3 | LNN reservoir + classifier | Phase 3.1, 3.2 | `core/lnn/reservoir.py`, `weights/lnn_reservoir.pt` |
| 3–4 | XGBoost ensemble classifier | PROMPT 05b | `core/inference/xgboost_classifier.py`, `weights/xgb_classifier.pkl` |
| 4 | Behavioral profiler | Phase 4.1, 4.2 | `core/behavioral/` |
| 5 | Wire inference pipeline | PROMPT 11 (ML side) | `inference_service/main.py` running end-to-end |
| 9–10 | Model evaluation against all datasets | Phase 10 | Benchmark results table (SNN, LNN, XGBoost F1 scores) |

### Key Responsibilities
- Achieve ≥ 92% F1-score (macro) on validation set across all three models (SNN, LNN, XGBoost)
- Ensure inference pipeline latency < 100ms per session end-to-end (SNN + LNN + XGBoost combined)
- Train XGBoost on fused feature vectors (snn_score + lnn_state + behavioral_delta) — PROMPT 05b
- Ensure `scaler.pkl` is saved by `preprocess.py` so `feature-service` can load it at startup
- Write model cards for SNN, LNN, and XGBoost (requirements, limitations, training data)
- Conduct ablation study: test XGBoost with and without SNN/LNN inputs; document results

### Tools
- PyTorch 2.x, Norse, scikit-learn, imbalanced-learn
- Weights & Biases (optional but recommended for experiment tracking)
- Intel Loihi DevCloud (if accessible)

### Antigravity Usage Pattern
- Use for: boilerplate neural network code, training loops, evaluation scripts, XGBoost pipeline glue
- Verify manually: STDP implementation, spectral radius scaling, spike encoding math, feature vector concatenation shape
- Never trust Antigravity for: exact Norse API version compatibility (always test imports); XGBoost feature_names alignment with training columns

---

## Member 2 — Backend Lead (@backend)

### Core Responsibility
Owns all server-side logic: FastAPI application, PostgreSQL schema, Kafka streaming pipeline, sandbox/honeypot system, and report generation.

### Week-by-Week Tasks

| Week | Task | Antigravity Prompt Section | Deliverable |
|---|---|---|---|
| 1–2 | Docker Compose setup (all 14 services) | PROMPT 01 | Working `docker-compose.yml` |
| 3 | Feature service (CIC extraction) | PROMPT 05c | `feature_service/` consuming raw-traffic Kafka topic |
| 4 | Sandbox + honeypot | Phase 5.2 | `core/deception/`, sandbox-service container isolated |
| 5 | Inference service wiring | PROMPT 11 | `inference_service/main.py` writing verdicts to DB |
| 5–6 | FastAPI gateway routes | PROMPT 06 | `api/main.py`, `schema.sql`, no ML imports in api |
| 7 | WebSocket alert stream | PROMPT 06 | `/ws/alerts` working, polling DB every 2s |
| 7–8 | Feedback + retraining services | PROMPT 12 | `feedback_service/`, `retraining_service/` running |
| 8 | Bank API routes | Phase 8.2 | `api/routes/bank.py` |
| 9 | Report generator | Phase 9 | `reports/generator.py` |
| 10 | Red team support | Phase 10.2 | Attack scripts ready |

### Key Responsibilities
- End-to-end pipeline: behavioral event POST → verdict in DB in < 5 seconds (all 4 pipeline containers healthy)
- Zero data loss on Kafka under demo load; each service uses a distinct `group_id`
- `sandbox-service` must have `network_mode: none` — this is security-critical per architecture plan
- `api` container must have NO ML imports (torch, norse, xgboost) — it is a gateway only
- `inference-service` hot-reloads `xgb_classifier.pkl` when `retraining-service` updates it
- PostgreSQL schema includes: `verdicts`, `labeled_training_data`, `sandbox_actions`, `honeypot_hits`, `alerts`, `sessions`, `users`, `user_profiles`
- API key rotation mechanism

### Tools
- FastAPI, asyncpg, psycopg2, Kafka-Python, Redis, Scapy
- Postman/Insomnia for API testing
- pgAdmin for database management

### Antigravity Usage Pattern
- Use for: Pydantic models, SQL DDL, CRUD operations, middleware, Kafka consumer/producer boilerplate
- Verify manually: Kafka `group_id` is unique per service; PostgreSQL connection pooling; `network_mode: none` on sandbox-service
- Never trust Antigravity for: security-sensitive code (authentication, session isolation, sandbox escape prevention) — review line by line

---

## Member 3 — Frontend Lead (@frontend)

### Core Responsibility
Owns all user-facing interfaces: the NeuroShield analyst dashboard and the NovaTrust Bank simulation portal. Heaviest Antigravity user on the team.

### Week-by-Week Tasks

| Week | Task | Antigravity Prompt Section | Deliverable |
|---|---|---|---|
| 6 | Analyst dashboard scaffold | Phase 7.1 | Dashboard running at :3000 |
| 6 | ThreatMap + AlertFeed | Phase 7.1 | Live map and alert scroll |
| 6–7 | StatsBar + charts | Phase 7.1 | Recharts timeline working |
| 7 | Bank portal scaffold | Phase 8.1 | Bank portal at :3001 |
| 7 | Behavioral tracker hook | Phase 8.1 | `useBehavioralTracker()` |
| 7 | Judge verdict split view | Phase 8.1 | `/verdict-display` route |
| 8 | Polish + responsive | — | Mobile/tablet-ready |
| 11 | Demo prep | Phase 11 | Demo script followed exactly |

### Key Responsibilities
- Dashboard must render without errors on first load
- Behavioral tracker MUST NOT miss any keystroke events
- Bank portal must pass visual credibility check (looks like a real bank)
- WebSocket reconnection must be automatic
- All loading states and error states implemented

### Tools
- React 18, TypeScript, TailwindCSS, Vite
- Recharts, D3.js, Leaflet.js
- Axios, native WebSocket
- Figma (for any wireframing)

### Antigravity Usage Pattern
- Use for: component boilerplate, chart setup, form structure, hook skeletons
- Iterate aggressively: paste error messages back into Antigravity immediately
- Always specify exact color codes, font names, and layout descriptions — Antigravity's default design is generic
- Test on: Chrome, Firefox, Safari minimum

---

## Member 4 — DevOps/Research Lead (@devops)

### Core Responsibility
Owns infrastructure, CI/CD, dataset management, research validation, and the research documentation. Also serves as the "integration glue" — connecting components built by other team members.

### Week-by-Week Tasks

| Week | Task | Antigravity Prompt Section | Deliverable |
|---|---|---|---|
| 1 | Manual repo + env setup | Phase 0.1 | Clean repo, all members onboarded |
| 1 | Dataset download + placement | Phase 1.1 | All 5 datasets in `datasets/raw/` |
| 2 | CI/CD pipeline | — | GitHub Actions workflow |
| 9–11 | Docker production build | Phase 11.1 | Multi-stage Dockerfiles |
| 10 | Integration test runner | Phase 10.1 | All 7 tests passing |
| 11 | Demo environment | Phase 11.2 | One-command demo start |
| 12 | Final submission | Phase 12 | Complete checklist |

### Research Responsibilities (Ongoing)
- Maintain `docs/RESEARCH_LOG.md`: log every paper read with relevance to the project
- Verify all accuracy claims against actual test results (update README.md Section 8)
- Source and cite all 5 datasets with proper attribution
- Write the project's academic abstract (500 words) for submission

### Antigravity Usage Pattern
- Use for: Dockerfile creation, GitHub Actions YAML, nginx config
- Verify manually: all security headers, volume mounts, non-root user configuration
- Never commit secrets to GitHub — use Antigravity to write `.env.example` only

---

## Communication & Sync Protocols

### Daily Standup (15 min, async in Slack/Discord)
```
Format:
✅ Done: [what was completed yesterday]
🔨 Doing: [what's in progress today]
⛔ Blocked: [any blockers — tag the relevant person]
```

### Integration Sync (Weekly, 1 hour)
- Every Sunday, all 4 members merge their branches to `develop`
- Run full integration test suite together
- Fix any breaking changes before next week starts

### Antigravity Code Review Protocol
1. @ml or @backend or @frontend generates code with Antigravity
2. They run the basic import/smoke test
3. Post the generated file in the team channel with: "Generated [filename] — needs review"
4. Any other member does a 10-minute review before it's merged
5. @devops is the final merge approver for all PRs to `main`

### Branch Strategy
```
main (production-ready only)
├── develop (integration branch)
│   ├── feature/snn-encoder       (@ml)
│   ├── feature/lnn-reservoir     (@ml)
│   ├── feature/fastapi-routes    (@backend)
│   ├── feature/sandbox           (@backend)
│   ├── feature/dashboard         (@frontend)
│   └── feature/bank-portal       (@frontend)
```

---

## Responsibility Matrix (RACI)

| Component | @ml | @backend | @frontend | @devops |
|---|---|---|---|---|
| SNN Engine | **R/A** | C | — | C |
| LNN Engine | **R/A** | C | — | C |
| XGBoost Classifier | **R/A** | C | — | C |
| Behavioral Profiler | **R/A** | C | C | — |
| Feature Service (CIC extraction) | C | **R/A** | — | C |
| Inference Service (pipeline) | R | **A** | — | C |
| Feedback Service | — | **R/A** | — | C |
| Retraining Service | R | **A** | — | C |
| FastAPI Gateway | — | **R/A** | C | C |
| PostgreSQL Schema | C | **R/A** | — | C |
| Sandbox/Honeypot | C | **R/A** | — | — |
| Analyst Dashboard | — | C | **R/A** | — |
| Bank Portal | — | C | **R/A** | — |
| Docker/Infra | — | C | C | **R/A** |
| Dataset Pipeline | R | — | — | **A** |
| Report Generator | — | **R/A** | — | C |
| Research Docs | C | C | — | **R/A** |
| Demo Preparation | C | C | C | **A** |

*R = Responsible, A = Accountable, C = Consulted*

---

## Risk Register

| Risk | Likelihood | Impact | Owner | Mitigation |
|---|---|---|---|---|
| Norse version incompatibility | High | High | @ml | Pin Norse==0.0.7 in requirements.txt |
| Dataset download takes too long | Medium | High | @devops | Start Week 1 Day 1; use cloud VM if slow |
| Antigravity generates wrong API | Medium | Medium | All | Always test imports before committing |
| WebSocket drops during demo | Medium | High | @backend | Implement auto-reconnect in dashboard |
| Bank portal looks fake | Medium | High | @frontend | Show to non-team members for credibility check |
| SNN accuracy < 90% | Low | High | @ml | Fallback: increase reservoir size; weight XGBoost more heavily |
| XGBoost feature vector shape mismatch | Medium | High | @ml + @backend | Verify `feature_columns.txt` is used consistently by feature-service AND training |
| Kafka drops messages between feature→inference | Low | High | @backend | Set `acks=all` on producer; verify consumer `group_id` uniqueness |
| sandbox-service escapes network isolation | Low | Critical | @backend | Verify `network_mode: none` in docker-compose; test with `docker exec ping` |
| Retraining overwrites good weights | Low | Medium | @ml + @backend | Keep `weights/xgb_best_backup.pkl`; retraining-service writes to temp file then renames |
| Kafka crashes under demo load | Low | Medium | @devops | Run demo with in-memory queue as fallback |
| Docker Compose fails on demo machine | Low | Critical | @devops | Pre-pull all images; have docker-compose.override.yml |
