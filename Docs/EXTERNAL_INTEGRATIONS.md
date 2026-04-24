# EXTERNAL INTEGRATIONS GUIDE — NeuroShield

> **What this doc covers:** Everything that CANNOT be done inside Antigravity and must be handled manually, externally, or with separate tooling.

---

## Why Some Things Must Stay External

Antigravity (vibe coding AI) is excellent at generating code but cannot:
- Register accounts on external services
- Access real databases or networks
- Run Python/Node.js to verify generated code actually works
- Handle security-sensitive credentials
- Download large files (datasets are 2–16 GB)
- Interface with neuromorphic hardware (Intel Loihi)

This document maps every external dependency and how to handle it.

---

## 1. Dataset Acquisition

### What Antigravity Can't Do
Download or process CIC datasets — they require human registration and agreement to terms.

### What You Do Instead

**CIC-IDS2017 (2.8M flows, ~8GB)**
1. Go to: https://www.unb.ca/cic/datasets/ids-2017.html
2. Fill free registration form (takes 2 minutes)
3. Download all CSV files from the MachineLearningCSV folder
4. Place in: `datasets/raw/CIC-IDS2017/`

**CSE-CIC-IDS2018 (16M+ flows, ~35GB)**
1. Go to: https://www.unb.ca/cic/datasets/ids-2018.html
2. Same free registration
3. Download CSV files
4. Place in: `datasets/raw/CIC-IDS2018/`

**CICIoT2023**
1. Go to: https://www.unb.ca/cic/datasets/iotdataset-2023.html
2. Download IoT CSV files
3. Place in: `datasets/raw/CICIoT2023/`

**CICIoMT2024**
1. Go to: https://www.unb.ca/cic/datasets/ciciomt-2024.html
2. Download medical IoT CSV files
3. Place in: `datasets/raw/CICIoMT2024/`

**NSL-KDD (public, no registration)**
```bash
wget https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTrain+.txt \
     -P datasets/raw/NSL-KDD/
wget https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTest+.txt \
     -P datasets/raw/NSL-KDD/
```

**IMPORTANT:** Due to size, if your dev machine can't store 50GB+ of data:
- Use Google Drive (mount in Colab)
- Use AWS S3 (free tier: 5GB limit — won't fit; use a small student account)
- Use only NSL-KDD + a sample of CIC-IDS2017 for development; use full datasets only for final training

---

## 2. Email / SMTP (Report Generator)

### What Antigravity Can't Do
Create or configure an email sending account.

### What You Do Instead

**Option A — SendGrid (Recommended, Free Tier: 100 emails/day)**
1. Go to: https://sendgrid.com — create free account
2. Settings → API Keys → Create API Key (Full Access)
3. Add to `.env`:
   ```
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USER=apikey
   SMTP_PASS=SG.your_actual_key_here
   REPORT_TO=yourteam@email.com
   ```

**Option B — Gmail (Dev Only)**
1. Enable 2FA on Gmail account
2. Go to: myaccount.google.com → Security → App Passwords
3. Create app password for "Mail"
4. Add to `.env`:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=yourteam@gmail.com
   SMTP_PASS=xxxx-xxxx-xxxx-xxxx  # App password
   ```

**NEVER commit `.env` to GitHub.** Use `.env.example` with placeholder values.

---

## 3. IP Geolocation (Threat Map)

### What Antigravity Can't Do
Subscribe to IP geolocation API services.

### What You Do Instead

**Option A — ip-api.com (Free: 45 req/min, no key required)**
```javascript
// In dashboard ThreatMap component
const geolocate = async (ip) => {
  const res = await fetch(`http://ip-api.com/json/${ip}`);
  const data = await res.json();
  return { lat: data.lat, lon: data.lon, country: data.country };
};
```
No setup needed. Rate limit: cache results in the backend to avoid repeated calls.

**Option B — MaxMind GeoLite2 (Free, offline database)**
1. Register at: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
2. Download `GeoLite2-City.mmdb`
3. Place at: `core/data/GeoLite2-City.mmdb`
4. Install: `pip install geoip2`
5. Tell Antigravity: "Use geoip2 with database at core/data/GeoLite2-City.mmdb to geolocate IPs"

---

## 4. Intel Loihi 2 (Neuromorphic Hardware)

### What Antigravity Can't Do
Apply for or configure Intel DevCloud access.

### What You Do Instead

**For Demo:** Use Norse (software SNN emulation) — fully sufficient for the demo and competitive submission. Loihi is a production optimization, not a requirement.

**If you want real Loihi (for research credit):**
1. Apply at: https://devcloud.intel.com/oneapi/get_started/
2. Select "Intel Neuromorphic Computing Lab" access
3. Wait 2–5 business days for approval
4. Once approved, SSH into DevCloud and install NxSDK:
   ```bash
   ssh devcloud
   conda create -n loihi python=3.8
   pip install nxsdk  # Intel's private SDK (only accessible from DevCloud)
   ```
5. Port the SNN encoder to NxSDK format (significant rewrite — plan 1 extra week)

**Recommendation:** Use Norse for the hackathon. Mention Loihi as the production target in presentation.

---

## 5. Domain & SSL Certificate (Optional for Demo)

### For Local Demo
No domain needed. Run everything on localhost.

### For Public Demo (Optional)
1. Purchase domain (e.g., neuroshield.tech) at Namecheap ~$10/year
2. Point A record to your cloud VM IP
3. Install Certbot for free Let's Encrypt SSL:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d neuroshield.tech -d bank.neuroshield.tech
   ```
4. Update nginx config (generated by Antigravity in Phase 11.1) with the cert paths

---

## 6. Cloud VM (If Local Machine Can't Run Everything)

### Recommended Specs (Minimum)
- 8 vCPU, 32GB RAM, 100GB SSD
- Ubuntu 22.04 LTS
- GPU optional (A100 ideal for SNN/LNN training; inference-service runs on CPU for demo)

### Service Resource Profile
| Container | CPU | RAM | GPU |
|---|---|---|---|
| feature-service | 1 vCPU | 1 GB | No |
| inference-service | 2 vCPU | 4 GB | Optional |
| feedback-service | 0.5 vCPU | 512 MB | No |
| retraining-service | 2 vCPU | 4 GB | Recommended |
| api | 1 vCPU | 1 GB | No |
| kafka + zookeeper | 1 vCPU | 2 GB | No |
| postgres + redis | 1 vCPU | 2 GB | No |
| dashboard + portal | 0.5 vCPU | 512 MB | No |

### Free/Cheap Options
| Provider | Option | Cost | Notes |
|---|---|---|---|
| Google Cloud | Free Trial ($300) | Free 90 days | Best for training |
| AWS | EC2 t3.xlarge | ~$0.17/hr | Good for demo |
| Oracle Cloud | Always Free VM | Free | 4 OCPU, 24GB RAM — sufficient for demo |
| Paperspace | P4000 GPU | ~$0.51/hr | Good for SNN training |

**Recommended flow:**
- Train models on Google Cloud (GPU, free trial)
- Save weights locally
- Run demo on Oracle Cloud Free Tier or local machine

---

## 7. GitHub Actions CI/CD

### What Antigravity Generates
The GitHub Actions YAML file structure.

### What You Configure Manually

1. Go to your GitHub repo → Settings → Secrets and Variables → Actions
2. Add these secrets:
   ```
   DOCKER_HUB_USERNAME    (your Docker Hub username)
   DOCKER_HUB_TOKEN       (Docker Hub access token)
   SENDGRID_API_KEY       (from Section 2)
   SLACK_WEBHOOK_URL      (for deployment notifications, optional)
   ```

3. The CI/CD pipeline (from Antigravity) should:
   - On every push to `develop`: Run pytest tests
   - On every PR to `main`: Run full integration test suite
   - On merge to `main`: Build Docker images and push to Docker Hub

---

## 8. Pre-Seeding Behavioral Profiles (Database)

### What Antigravity Can't Do
Generate realistic behavioral data that matches a real person's typing patterns.

### What You Do Instead

Run this seeding script (ask Antigravity to generate it):
```
Write a Python script called redteam/seed_profiles.py that:
1. Generates 10 synthetic "sessions" for user "normal1@novatrust.com" with:
   - Inter-keystroke intervals: random normal distribution, mean=90ms, std=15ms
   - Dwell times: random normal, mean=60ms, std=10ms
   - Mouse velocities: random normal, mean=200px/s, std=50px/s
   - Session duration: random uniform 120-600 seconds
2. Same for "normal2@novatrust.com" with faster typing (mean=40ms, std=8ms)
3. Same for "admin@novatrust.com" with mixed profile (mean=60ms, std=30ms)
4. Calls BehavioralProfiler.update_profile() for each synthetic session
5. Saves all profiles to PostgreSQL
Run this once after the database is initialized.
```

**When to run:**
```bash
# After docker-compose up and database schema applied:
python redteam/seed_profiles.py
```

---

## 9. Red Team Attack Scripts

### What Antigravity Generates
The Python code for attack scripts.

### What You Must Run Manually (Security Reasons)

These scripts must be run with specific permissions and only against your OWN demo environment:

```bash
# Always run in a separate terminal during demo
# NEVER run against any real system

# Brute force simulation (no root needed)
python redteam/attack_brute_force.py --target http://localhost:3001 --attempts 100

# DDoS simulation (requires root for Scapy raw sockets)
sudo python redteam/attack_ddos.py --target localhost --port 3001 --packets 5000

# Normal user simulation
python redteam/attack_normal_user.py --user normal1@novatrust.com --sessions 3

# Reset demo state (run between demo runs)
python redteam/reset_demo.py
```

**Ethical Note:** These scripts are for demonstration ONLY against your own system. Using them against any external system is illegal.

---

## 10. Weights & Model Storage

### What Antigravity Can't Do
Store large model weight files (SNN ~200MB, LNN ~50MB, XGBoost ~10MB).

### Weight Files Reference
| File | Owner | Written by | Read by |
|---|---|---|---|
| `weights/snn_best.pt` | @ml | training script | inference-service |
| `weights/lnn_reservoir.pt` | @ml | training script | inference-service |
| `weights/lnn_readout.pt` | @ml | training script | inference-service |
| `weights/xgb_classifier.pkl` | @ml (initial) / retraining-service (updates) | XGBoostThreatClassifier.train() | inference-service (hot-reloads on mtime change) |
| `datasets/scaler.pkl` | @ml | preprocess.py | feature-service |

### For development
Store locally at `weights/` (gitignored). The `inference-service` and `retraining-service` containers both mount `./weights:/weights` as a shared volume — changes by retraining-service are immediately visible to inference-service.

### For sharing between team members
1. HuggingFace Hub (Free, public or private repos):
   ```python
   from huggingface_hub import HfApi
   api = HfApi()
   api.upload_file(path_or_fileobj="weights/snn_best.pt", 
                   path_in_repo="snn_best.pt",
                   repo_id="your-org/neuroshield-weights")
   ```
2. Google Drive shared link (simplest for hackathon)
3. Git LFS (if using GitHub — 1GB free LFS storage)

**Add to `.gitignore`:**
```
weights/*.pt
weights/*.pkl
datasets/raw/
datasets/processed/
sandbox_data/
logs/demo_resets.log
```

---

## 11. Antigravity Input/Output Management

### What to Paste INTO Antigravity
- Full prompts from `MASTER_PLAN.md` (copy entire prompt blocks)
- Error messages (paste exact terminal output)
- Existing code files you want extended (paste the whole file)
- Schema definitions (paste SQL or Python dataclasses)

### What to Copy OUT of Antigravity
- Generated Python files → save to correct path immediately
- Generated React components → check for TypeScript errors before saving
- Generated SQL → run against dev database before committing
- Generated Dockerfiles → test `docker build` before committing

### Golden Rule
**Never trust Antigravity's output without running it.**
```bash
# After every Antigravity-generated Python file:
python -c "import [module]; print('OK')"

# After every Antigravity-generated React component:
npm run build  # Check for TypeScript errors

# After every Antigravity-generated SQL:
psql -U ns_user -d neuroshield -f [file.sql]

# After every Antigravity-generated Dockerfile:
docker build -t test-build .
```

### What Antigravity Commonly Gets Wrong
| What You Asked For | Common Mistake | How to Fix |
|---|---|---|
| Norse SNN code | Uses old Norse API | Provide `pip show norse` version, ask it to fix for that version |
| Kafka consumer | Missing `group_id` | Always specify group_id in your prompt |
| WebSocket code | Uses socket.io when you want native WS | Specify "use native WebSocket API, not socket.io-client" |
| Async FastAPI | Mixes sync/async | Specify "use async/await throughout, use asyncpg not psycopg2" |
| React hooks | Stale closure bugs in useEffect | Test with React StrictMode enabled |
| Docker multi-stage | Wrong COPY paths | Always test with `docker build` |
| SQL with arrays | Postgres array syntax errors | Specify "PostgreSQL 15 syntax" in prompt |

---

## Quick Reference: External Service Checklist

Before first demo run, verify each item:

**Data & Models**
- [ ] All 5 datasets downloaded and in `datasets/raw/`
- [ ] `preprocess.py` ran successfully, `unified_train.csv` exists and `scaler.pkl` saved
- [ ] SNN model trained, `weights/snn_best.pt` exists
- [ ] LNN reservoir trained, `weights/lnn_reservoir.pt` and `weights/lnn_readout.pt` exist
- [ ] XGBoost trained, `weights/xgb_classifier.pkl` exists
- [ ] `seed_profiles.py` ran, 3 user behavioral profiles in database

**Pipeline Services**
- [ ] `feature-service` starts and logs "Feature service started. Listening on raw-traffic..."
- [ ] `inference-service` starts and logs "Inference service ready..."
- [ ] `feedback-service` starts and logs "Feedback service started..."
- [ ] `retraining-service` starts and logs "Insufficient new data, skipping..." (expected on first run)
- [ ] End-to-end test: send behavioral event → confirm verdict appears in DB within 5 seconds

**Infrastructure**
- [ ] All Docker images built successfully (`docker-compose build`)
- [ ] All 7 pytest integration tests passing
- [ ] SMTP credentials working (`python -c "from reports.generator import test_email; test_email()"`)

**Frontends & Demo**
- [ ] Dashboard accessible at localhost:3000
- [ ] Bank portal accessible at localhost:3001
- [ ] `/verdict-display` shows split view with XGBoost confidence score
- [ ] Red team scripts tested against localhost (not external)
- [ ] Demo reset script `reset_demo.py` tested and working
- [ ] No `.env` file committed to GitHub (`git log --all -- .env`)
