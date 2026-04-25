from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

try:
    import psycopg2
    from psycopg2.extras import Json
except ImportError:  # pragma: no cover - optional in local smoke environments
    psycopg2 = None
    Json = None

from .signals import SESSION_VECTOR_SIZE


log = logging.getLogger(__name__)

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]


def _default_storage_dir() -> Path:
    configured = os.getenv("BEHAVIOR_PROFILE_DIR")
    if configured:
        return Path(configured).expanduser()

    candidates = [
        REPO_ROOT / "data" / "behavioral_profiles",
        SERVICE_ROOT / "data" / "behavioral_profiles",
        Path.cwd() / "data" / "behavioral_profiles",
    ]
    if os.name != "nt":
        candidates.insert(0, Path("/data/behavioral_profiles"))

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except OSError:
            continue
    return Path.cwd() / "behavioral_profiles"


@dataclass
class UserProfile:
    user_id: str
    profile_vector: np.ndarray
    profile_std: np.ndarray
    session_count: int
    last_updated: float
    alpha: float = 0.1

    def to_payload(self) -> dict:
        return {
            "user_id": self.user_id,
            "profile_vector": self.profile_vector.astype(float).tolist(),
            "profile_std": self.profile_std.astype(float).tolist(),
            "session_count": int(self.session_count),
            "last_updated": float(self.last_updated),
            "alpha": float(self.alpha),
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "UserProfile":
        return cls(
            user_id=str(payload["user_id"]),
            profile_vector=np.asarray(payload["profile_vector"], dtype=np.float32),
            profile_std=np.asarray(payload["profile_std"], dtype=np.float32),
            session_count=int(payload.get("session_count", 0)),
            last_updated=float(payload.get("last_updated", time.time())),
            alpha=float(payload.get("alpha", 0.1)),
        )


class BehavioralProfiler:
    def __init__(
        self,
        database_url: str | None = None,
        storage_dir: str | Path | None = None,
        alpha: float = 0.1,
    ) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        default_storage = _default_storage_dir()
        self.storage_dir = Path(storage_dir) if storage_dir else default_storage
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.alpha = alpha
        self._profiles: dict[str, UserProfile] = {}
        self._lock = threading.RLock()
        self._table_ready = False

    def _normalize_vector(self, session_vector: np.ndarray | list[float]) -> np.ndarray:
        vector = np.asarray(session_vector, dtype=np.float32).reshape(-1)
        if vector.shape[0] != SESSION_VECTOR_SIZE:
            raise ValueError(
                f"Expected a {SESSION_VECTOR_SIZE}-dimensional session vector, got {vector.shape[0]}."
            )
        vector = np.nan_to_num(vector, copy=False)
        return vector

    def _profile_path(self, user_id: str) -> Path:
        safe_user_id = "".join(character if character.isalnum() or character in ("-", "_") else "_" for character in user_id)
        return self.storage_dir / f"{safe_user_id}.json"

    def _connect(self):
        if not self.database_url or psycopg2 is None:
            return None
        return psycopg2.connect(self.database_url)

    def _ensure_table(self) -> None:
        if self._table_ready or not self.database_url or psycopg2 is None:
            return
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_behavior_profiles (
                        user_id TEXT PRIMARY KEY,
                        profile_vector JSONB NOT NULL,
                        profile_std JSONB NOT NULL,
                        session_count INTEGER NOT NULL,
                        last_updated DOUBLE PRECISION NOT NULL,
                        alpha DOUBLE PRECISION NOT NULL
                    )
                    """
                )
            connection.commit()
        self._table_ready = True

    def update_profile(self, user_id: str, session_vector: np.ndarray | list[float]) -> UserProfile:
        vector = self._normalize_vector(session_vector)
        with self._lock:
            profile = self.load_profile(user_id)
            if profile is None:
                profile = UserProfile(
                    user_id=user_id,
                    profile_vector=vector.copy(),
                    profile_std=np.zeros_like(vector),
                    session_count=1,
                    last_updated=time.time(),
                    alpha=self.alpha,
                )
            else:
                alpha = profile.alpha
                previous_mean = profile.profile_vector.copy()
                previous_var = np.square(profile.profile_std)
                updated_mean = (1.0 - alpha) * previous_mean + alpha * vector
                updated_var = (1.0 - alpha) * previous_var + alpha * np.square(vector - previous_mean)
                profile.profile_vector = updated_mean.astype(np.float32)
                profile.profile_std = np.sqrt(np.maximum(updated_var, 0.0)).astype(np.float32)
                profile.session_count += 1
                profile.last_updated = time.time()
            self._profiles[user_id] = profile
            self.save_profile(user_id)
            return profile

    def compute_delta(self, user_id: str, session_vector: np.ndarray | list[float]) -> float:
        vector = self._normalize_vector(session_vector)
        with self._lock:
            profile = self.load_profile(user_id)
            if profile is None:
                return 0.5
            base = profile.profile_vector.astype(np.float32)
            base_norm = float(np.linalg.norm(base))
            vector_norm = float(np.linalg.norm(vector))
            if base_norm <= 1e-8 or vector_norm <= 1e-8:
                return 0.0
            cosine_similarity = float(np.dot(base, vector) / (base_norm * vector_norm))
            delta = 1.0 - cosine_similarity
            return float(np.clip(delta, 0.0, 1.0))

    def classify_delta(self, delta: float) -> Literal["HACKER", "FORGETFUL_USER", "LEGITIMATE"]:
        if delta > 0.70:
            return "HACKER"
        if delta > 0.30:
            return "FORGETFUL_USER"
        return "LEGITIMATE"

    def save_profile(self, user_id: str) -> None:
        with self._lock:
            profile = self._profiles.get(user_id)
            if profile is None:
                return

            saved_to_database = False
            if self.database_url and psycopg2 is not None:
                try:
                    self._ensure_table()
                    with self._connect() as connection:
                        with connection.cursor() as cursor:
                            cursor.execute(
                                """
                                INSERT INTO user_behavior_profiles (
                                    user_id, profile_vector, profile_std, session_count, last_updated, alpha
                                ) VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (user_id) DO UPDATE SET
                                    profile_vector = EXCLUDED.profile_vector,
                                    profile_std = EXCLUDED.profile_std,
                                    session_count = EXCLUDED.session_count,
                                    last_updated = EXCLUDED.last_updated,
                                    alpha = EXCLUDED.alpha
                                """,
                                (
                                    profile.user_id,
                                    Json(profile.profile_vector.astype(float).tolist()),
                                    Json(profile.profile_std.astype(float).tolist()),
                                    profile.session_count,
                                    profile.last_updated,
                                    profile.alpha,
                                ),
                            )
                        connection.commit()
                    saved_to_database = True
                except Exception as exc:  # pragma: no cover - depends on runtime DB availability
                    log.warning("Failed to persist behavioral profile to PostgreSQL for user %s: %s", user_id, exc)

            if not saved_to_database:
                self._profile_path(user_id).write_text(
                    json.dumps(profile.to_payload(), indent=2),
                    encoding="utf-8",
                )

    def load_profile(self, user_id: str) -> UserProfile | None:
        with self._lock:
            cached = self._profiles.get(user_id)
            if cached is not None:
                return cached

            if self.database_url and psycopg2 is not None:
                try:
                    self._ensure_table()
                    with self._connect() as connection:
                        with connection.cursor() as cursor:
                            cursor.execute(
                                """
                                SELECT user_id, profile_vector, profile_std, session_count, last_updated, alpha
                                FROM user_behavior_profiles
                                WHERE user_id = %s
                                """,
                                (user_id,),
                            )
                            row = cursor.fetchone()
                    if row:
                        profile = UserProfile(
                            user_id=str(row[0]),
                            profile_vector=np.asarray(row[1], dtype=np.float32),
                            profile_std=np.asarray(row[2], dtype=np.float32),
                            session_count=int(row[3]),
                            last_updated=float(row[4]),
                            alpha=float(row[5]),
                        )
                        self._profiles[user_id] = profile
                        return profile
                except Exception as exc:  # pragma: no cover - depends on runtime DB availability
                    log.warning("Failed to load behavioral profile from PostgreSQL for user %s: %s", user_id, exc)

            path = self._profile_path(user_id)
            if not path.exists():
                return None
            payload = json.loads(path.read_text(encoding="utf-8"))
            profile = UserProfile.from_payload(payload)
            self._profiles[user_id] = profile
            return profile


__all__ = ["UserProfile", "BehavioralProfiler"]
