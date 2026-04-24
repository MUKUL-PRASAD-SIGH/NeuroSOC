# Builder B: Backend Lead

## Overview of Team Tasks
- **Builder A (ML/AI Lead)**: Neural network components (SNN, LNN, Behavioral Profiler, Models).
- **Builder B (Backend Lead)**: FastAPI, PostgreSQL, Kafka, Sandbox, Microservices.
- **Builder C (Frontend Lead)**: Analyst Dashboard, Bank Simulation Portal.
- **Builder D (DevOps/Research Lead)**: Infrastructure, CI/CD, Docker, Datasets, Research.

## Your Domain & Responsibilities
You own all server-side logic: FastAPI application, PostgreSQL schema, Kafka streaming pipeline, sandbox/honeypot system, and report generation.

## Allowed Edit Paths (You may only edit these files/folders)
- `inference-service/api/`
- `inference-service/main.py` (FastAPI and routing logic)
- `feature-service/` (Kafka ingestion/API logic)
- `feedback-service/`
- `ingestion-service/`
- `retraining-service/`
- `sandbox-service/`
- *Note: Coordinate with Builder D for additions to `docker-compose.yml`.*

## Relevant Folders & Files to be Aware Of
- `docker-compose.yml`
- `Docs/`

## Parallel Workflow Strategy
- **Mocking for others**: Build out the API endpoints (FastAPI) and WebSocket streams returning hardcoded/dummy JSON data immediately. This allows Builder C (Frontend) to start building the UI without waiting for the database or Kafka to be ready.
- **Independent work**: You can build the Kafka streaming pipeline, PostgreSQL schema, and the Sandbox isolated environment using mock data generators. 
- **Integration point**: When Builder A's models are ready, replace your dummy inference calls in `inference-service` with the actual model loading and execution logic provided by Builder A.

## Detailed Implementation Plan
- **Week 1-2**: Backend service architecture and initial setup.
- **Week 3**: Feature service (CIC extraction) consuming raw-traffic Kafka topic.
- **Week 4**: Sandbox + honeypot. Deliverable: `core/deception/`, sandbox-service container isolated (`network_mode: none`).
- **Week 5**: Inference service wiring. Deliverable: API schema in `inference_service/main.py` writing mock (then real) verdicts to DB. NO ML imports in the API gateway.
- **Week 5-6**: FastAPI gateway routes. 
- **Week 7**: WebSocket alert stream polling DB every 2s.
- **Week 7-8**: Feedback + retraining services running.
- **Week 8**: Bank API routes.
- **Week 9**: Report generator.
- **Week 10**: Red team support.