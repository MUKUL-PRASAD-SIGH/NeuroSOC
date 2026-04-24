"""
kafka_setup.py — NeuroShield Kafka Topic Initializer
Phase 1.1 per MASTER_PLAN.md

Creates all required Kafka topics with robust retry logic.

CHECKPOINT: Run this and verify these topics exist:
  raw-packets, extracted-features, verdicts, feedback, alerts

FIX (vs v1): 10 retries × 15s = 150s total wait.
  Confluent cp-kafka:7.5.0 takes 30-90s to fully initialise in Docker.
  5 × 10s = 50s was not enough → Kafka would refuse connections at boot.
"""

import os
import sys
import time
import logging

from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [kafka_setup] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

KAFKA_BOOTSTRAP  = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
MAX_RETRIES      = int(os.getenv("KAFKA_SETUP_RETRIES", "10"))   # ↑ from 5
RETRY_DELAY_SEC  = int(os.getenv("KAFKA_SETUP_DELAY", "15"))     # ↑ from 10

TOPICS: list[dict] = [
    {"name": "raw-packets",        "partitions": 3, "replication": 1},
    {"name": "extracted-features", "partitions": 3, "replication": 1},
    {"name": "verdicts",           "partitions": 1, "replication": 1},
    {"name": "feedback",           "partitions": 1, "replication": 1},
    {"name": "alerts",             "partitions": 1, "replication": 1},
]


def create_topics(admin: KafkaAdminClient) -> None:
    """Create all required topics.

    FIX: kafka-python 2.0.2 + Confluent broker 7.5.0 (identifies as 2.5.0)
    admin.create_topics() returns a CreateTopicsResponse_v3 object — NOT a dict.
    Iterating with .items() crashes with AttributeError.

    Correct approach: read response.topic_errors which is a list of
      (topic_name, error_code, error_message) tuples.
    Error code 36 = TopicAlreadyExists (safe to ignore).
    Error code  0 = Success.
    """
    new_topics = [
        NewTopic(
            name=t["name"],
            num_partitions=t["partitions"],
            replication_factor=t["replication"],
        )
        for t in TOPICS
    ]
    try:
        response = admin.create_topics(new_topics=new_topics, validate_only=False)

        # Handle both response formats defensively
        if hasattr(response, "topic_errors"):
            # kafka-python 2.0.2 with broker 2.5.x — returns response object directly
            for topic_name, error_code, error_message in response.topic_errors:
                if error_code == 0:
                    log.info("✅ Topic '%s' created.", topic_name)
                elif error_code == 36:          # TopicAlreadyExistsException
                    log.info("ℹ️  Topic '%s' already exists — skipping.", topic_name)
                else:
                    log.error(
                        "❌ Topic '%s': error_code=%d  message=%s",
                        topic_name, error_code, error_message,
                    )
                    raise RuntimeError(
                        f"Topic creation failed for '{topic_name}' "
                        f"(error_code={error_code})"
                    )
        elif hasattr(response, "items"):
            # Older kafka-python behaviour — returns dict of futures
            for topic_name, future in response.items():
                try:
                    future.result()
                    log.info("✅ Topic '%s' created.", topic_name)
                except TopicAlreadyExistsError:
                    log.info("ℹ️  Topic '%s' already exists — skipping.", topic_name)
                except Exception as exc:
                    log.error("❌ Failed to create topic '%s': %s", topic_name, exc)
                    raise
        else:
            raise RuntimeError(
                f"Unexpected create_topics() response type: {type(response)}. "
                "Update kafka-python or fix response parsing."
            )
    except TopicAlreadyExistsError:
        log.info("ℹ️  Topics already exist — skipping.")


def run() -> None:
    """Connect to Kafka with retries and create all topics."""
    log.info("Connecting to Kafka at %s  (max %d attempts, %ds gap)…",
             KAFKA_BOOTSTRAP, MAX_RETRIES, RETRY_DELAY_SEC)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            admin = KafkaAdminClient(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                client_id="neuroshield-setup",
                request_timeout_ms=15_000,
            )
            log.info("Connected on attempt %d/%d.", attempt, MAX_RETRIES)
            create_topics(admin)
            admin.close()
            log.info("✅ Kafka setup complete — all %d topics ready.", len(TOPICS))
            return

        except NoBrokersAvailable:
            log.warning(
                "Kafka not reachable (attempt %d/%d). Waiting %ds…",
                attempt, MAX_RETRIES, RETRY_DELAY_SEC,
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SEC)
            else:
                log.error(
                    "❌ Could not connect to Kafka after %d attempts (%ds total). "
                    "Is Kafka running at %s? Check: docker-compose ps kafka",
                    MAX_RETRIES, MAX_RETRIES * RETRY_DELAY_SEC, KAFKA_BOOTSTRAP,
                )
                sys.exit(1)

        except Exception as exc:  # noqa: BLE001
            log.error("❌ Unexpected error during Kafka setup: %s", exc)
            sys.exit(1)


if __name__ == "__main__":
    run()
