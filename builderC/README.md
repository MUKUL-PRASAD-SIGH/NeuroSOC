# Builder C: Frontend Lead

## Overview of Team Tasks
- **Builder A (ML/AI Lead)**: Neural network components (SNN, LNN, Behavioral Profiler, Models).
- **Builder B (Backend Lead)**: FastAPI, PostgreSQL, Kafka, Sandbox, Microservices.
- **Builder C (Frontend Lead)**: Analyst Dashboard, Bank Simulation Portal.
- **Builder D (DevOps/Research Lead)**: Infrastructure, CI/CD, Docker, Datasets, Research.

## Your Domain & Responsibilities
You own all user-facing interfaces: the NeuroShield analyst dashboard and the NovaTrust Bank simulation portal.

## Allowed Edit Paths (You may only edit these files/folders)
- `dashboard/` (and all its subdirectories)
- `simulation_portal/` (and all its subdirectories)

## Relevant Folders & Files to be Aware Of
- `Docs/` (especially `SIMULATION_PORTAL_SPEC.md` if it exists)

## Parallel Workflow Strategy
- **Independent work**: Do not wait for the backend API to be finished. Create mock JSON files or use a tool like `json-server` or MSW (Mock Service Worker) to simulate the API responses Builder B is working on. 
- **Development**: Focus entirely on the UI components, state management, charting (Recharts), and responsive design.
- **Integration point**: Once Builder B has the FastAPI server running (even with dummy data), swap out your mock API calls for the real local endpoints (e.g., `http://localhost:8000`).

## Detailed Implementation Plan
- **Week 6**: Analyst dashboard scaffold (running at :3000), ThreatMap + AlertFeed, StatsBar + charts. Use mock data for all charts and alerts.
- **Week 7**: Bank portal scaffold (running at :3001), Behavioral tracker hook (`useBehavioralTracker()`), Judge verdict split view.
- **Week 8**: Polish + responsive design (Mobile/tablet-ready). Connect to actual backend API when ready.
- **Week 11**: Demo prep, ensuring the demo script is followed exactly.