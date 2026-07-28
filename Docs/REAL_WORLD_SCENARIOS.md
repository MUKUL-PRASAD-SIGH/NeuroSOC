# Real-World Simulation Scenarios

NeuroShield's simulation pipeline uses high-fidelity, profile-aware telemetry to mimic real-world interactions and attacks. This allows the system to be tested against human-like drift and automated hostile actions.

## 1. Trusted Customer (Alice Johnson)
**Scenario**: Known customer ISP, residential IP, standard browser fingerprint.
- **Network Profile**: Standard TLS 1.3 handshakes, nominal TTL (64), consistent packet sizes.
- **Behavioural Profile**: Human interaction cadence (~80ms keystrokes, natural mouse drift).
- **Outcome**: Ensemble (SNN + LNN + XGBoost) confirms legitimacy. No isolation.

## 2. Flagged But Innocent (Bob Carter)
**Scenario**: Mobile ISP source, VPN markers detected, new device fingerprint.
- **Network Profile**: Elevated TTL (128), VPN header markers, geo-mismatch with account history.
- **Behavioural Profile**: High-friction rhythm (hesitant typing, erratic mouse movement).
- **Outcome**: Ensemble detects borderline risk. Triggers **Soft Review Timeout** to contain risk without hard isolation.

## 3. Active Hacker (Unknown Intruder)
**Scenario**: Untrusted automated client probing the portal edge.
- **Network Profile**: `sqlmap/1.8` fingerprints, unencrypted probes on port 80, bulk data exfiltration on port 443.
- **Behavioural Profile**: Inhuman velocity (zero mouse drift, instant paste events, 2000x human speed).
- **Outcome**: **Critical Alert** triggered by behavioural spike. Lethal SQL injection payload results in **Hard Sandbox Isolation**.

## Enhanced Observability ("Hot" Simulation)
The simulation runners now feature:
- **Premium Descriptions**: High-intensity, security-focused descriptions for each phase.
- **Emoji-Enriched Logs**: Clear visual indicators (📡, 👤, 🚨, 🛡️) for better scannability.
- **Optimized Delays**: Phases are spaced (4500ms - 5500ms) to allow operators to read and analyze the live telemetry.
- **Ensemble Lock Insight**: Real-time logging of individual classifier scores (SNN/LNN/XGBoost) during the decision phase.

## Technical Implementation
- **Portal Script**: `simulation_portal/src/lib/systemFlowScenarios.ts`
- **Dashboard Script**: `dashboard/src/services/liveScripts.js`
- **API Bridge**: `portalApi.ts` supporting `reportWebAttack` and `postRawIngest`.
