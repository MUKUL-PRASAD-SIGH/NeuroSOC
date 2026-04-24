# NeuroSOC-TRIAL: Generalization & Framework Transformation Plan

## Vision
Transform the highly specific, low-level `NeuroSOC-TRIAL` project into a generalized, plug-and-play Security Operations Center (SOC) framework capable of ingesting, processing, and analyzing **any** type of log data (e.g., Syslog, Windows Event Logs, CloudTrail, custom application logs) without requiring Python code changes from the end-user.

## 1. Architectural Transformation: From Hardcoded to Configuration-Driven

The current architecture is solid (Docker + Kafka microservices), but the internal logic of the services is tightly coupled to a specific use case (network traffic / 80 CICFlowMeter features). To generalize, we will shift to a **Configuration-Driven Pipeline**.

### Phase 1.1: The Universal Ingestion Engine (`ingestion-service`)
**Current State:** Hardcoded parsers for PCAP and NetFlow.
**Future State:** A universal parser that dynamically processes incoming streams based on user-defined schemas.
*   **Mechanism:** Analysts define "Log Source Definitions" (YAML/JSON) that specify how to parse incoming text, JSON, or binary data.
*   **Capabilities:** Regex extraction, JSON path mapping, CSV splitting, and timestamp normalization.
*   **Output:** Standardized JSON objects placed onto Kafka, regardless of the original log format.

### Phase 1.2: The Dynamic Feature Engine (`feature-service`)
**Current State:** Hardcoded calculation of 80 specific network features.
**Future State:** A dynamic stream-processing engine (potentially leveraging tools like ksqlDB, Apache Flink, or a generalized Python stream processor) that computes features on the fly based on configuration.
*   **Mechanism:** Analysts define "Feature Rules" (e.g., tumbling windows, sliding windows, group-by operations).
*   **Example Rule:** "Count the number of `event_id=4625` (Failed Logon) per `user_account` over a `10-minute` sliding window."
*   **Output:** Dynamic feature vectors placed onto Kafka, tagged with the pipeline/model they are intended for.

### Phase 1.3: Model Registry & Routing (`inference-service`)
**Current State:** Tightly coupled to a specific XGBoost model expecting 80 features.
**Future State:** A decoupled inference routing system.
*   **Mechanism:** Models are registered with an "Input Schema" (the specific features they require). The inference service listens for feature vectors, matches them to the appropriate model based on the schema/pipeline tag, and executes the inference.
*   **Support:** Allow plugging in various model types (Scikit-Learn, PyTorch, XGBoost, LLMs) via a standardized wrapper interface (e.g., MLflow formats).

## 2. Feasibility Assessment

**Highly Feasible.** The existing event-driven architecture using Kafka and Docker is the perfect foundation for a generalized processing pipeline. 
*   **Pros:** The services are already decoupled. We can rewrite the internals of one service without breaking the others, as long as the Kafka JSON contracts are maintained.
*   **Challenges:** Building a robust, performant Dynamic Feature Engine from scratch in Python can be complex (handling late-arriving data, state management). We may need to evaluate integrating an existing stream processing framework (like ksqlDB) to handle the heavy lifting of stateful aggregations if the Python implementation becomes a bottleneck.

## 3. SOC Analyst Experience (Plug-and-Play)

The primary goal is that a SOC Analyst should write **zero Python code** to onboard a new log source or model.

### 3.1 Pipeline-as-Code (YAML)
Analysts define end-to-end pipelines in a simple YAML syntax:

```yaml
name: "Brute_Force_Detection_Pipeline"
description: "Detects SSH brute force attempts from syslog"

ingestion:
  source_type: "syslog_tcp"
  port: 5140
  parser:
    type: "regex"
    pattern: '(?P<timestamp>\w+ \d+ \d+:\d+:\d+) (?P<host>\S+) sshd\[\d+\]: Failed password for (?P<user>\S+) from (?P<ip>\S+)'

feature_extraction:
  group_by: "ip"
  window: "5m"
  features:
    - name: "failed_attempts"
      calculation: "count()"
    - name: "unique_users_targeted"
      calculation: "nunique(user)"

inference:
  model_id: "xgboost_ssh_bruteforce_v1"
  action_on_alert: "publish_to_alerts_topic"
```

### 3.2 The Simulation Portal (No-Code UI)
The existing `simulation_portal` will be upgraded to a visual pipeline builder.
1.  **Upload Logs:** Analyst uploads a sample log file.
2.  **Visual Mapping:** Analyst highlights parts of the log to extract fields (auto-generating the regex/JSON path).
3.  **Feature Builder:** Dropdown menus to select aggregations (Count, Sum, Average, Unique) over time windows.
4.  **Model Link:** Select a pre-trained model from a dropdown.
5.  **Deploy:** The UI generates the YAML and pushes it to a configuration topic, dynamically reconfiguring the running microservices.

---

## Questions for Refining the Plan:

To ensure this framework meets your specific goals, please clarify the following:

1.  **Scale and Throughput:** What is the expected EPS (Events Per Second) for the log sources you want to ingest? If it's extremely high (10,000+ EPS), we might need to rely on technologies like Apache Flink or ksqlDB for the Feature Engine rather than pure Python.
2.  **Model Training:** Do you intend for the SOC analysts to train the models within this platform, or will they only be uploading pre-trained models (e.g., from a data science team) to be used for inference?
3.  **Alerting and Response:** Once the `inference-service` flags an anomaly, what should happen next? Should it just log to a database, send a Slack message, or trigger an automated SOAR playbook?
4.  **Log Sources:** What are the first 2-3 specific log types (e.g., Windows Event Logs, AWS CloudTrail, Nginx access logs) you would want to support as a proof-of-concept for this new generalized framework?
