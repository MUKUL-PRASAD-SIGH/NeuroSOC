# Builder D: DevOps/Research Lead

## Overview of Team Tasks
- **Builder A (ML/AI Lead)**: Neural network components (SNN, LNN, Behavioral Profiler, Models).
- **Builder B (Backend Lead)**: FastAPI, PostgreSQL, Kafka, Sandbox, Microservices.
- **Builder C (Frontend Lead)**: Analyst Dashboard, Bank Simulation Portal.
- **Builder D (DevOps/Research Lead)**: Infrastructure, CI/CD, Docker, Datasets, Research.

## Your Domain & Responsibilities
You own infrastructure, CI/CD, dataset management, research validation, and the research documentation. You connect components built by other team members.

## Allowed Edit Paths (You may only edit these files/folders)
- `docker-compose.yml` (Primary owner)
- `monitoring/`
- `.github/workflows/` (or other CI/CD paths)
- `Docs/` (Research logs, abstract, README)
- Any `Dockerfile` across all services.

## Relevant Folders & Files to be Aware Of
- The root of the project to ensure clean repository management.

## Parallel Workflow Strategy
- **Independent work**: You can immediately start setting up the GitHub Actions CI pipeline, defining the Dockerfiles for each service (using placeholder/empty code from the other builders if necessary), and constructing the `docker-compose.yml`.
- **Enabling others**: Download and place the datasets in the correct folders so Builder A can start training immediately. Set up the foundational Docker network so Builder B can start communicating between microservices.
- **Integration point**: Continually ensure that as Builders A, B, and C add dependencies (e.g., `package.json` or `requirements.txt`), the Docker containers still build successfully.

## Detailed Implementation Plan
- **Week 1**: Manual repo + env setup, dataset download + placement in `datasets/raw/`.
- **Week 2**: CI/CD pipeline setup (GitHub Actions workflow).
- **Week 9-11**: Docker production build with multi-stage Dockerfiles.
- **Week 10**: Integration test runner (all tests passing).
- **Week 11**: Demo environment setup (One-command demo start).
- **Week 12**: Final submission checklist.
- **Ongoing**: Maintain research logs, verify accuracy claims, source datasets, write academic abstract.