from __future__ import annotations

import math
from typing import Iterable

import numpy as np


SESSION_VECTOR_SIZE = 20
WORD_BOUNDARY_KEYS = {" ", "space", "spacebar", "tab", "enter", "return"}
ERROR_KEYS = {"backspace", "delete"}


def _sorted_events(events: Iterable[dict]) -> list[dict]:
    return sorted(
        [event for event in events if isinstance(event, dict)],
        key=lambda event: float(event.get("timestamp", 0.0) or 0.0),
    )


def _non_negative_array(values: list[float]) -> np.ndarray:
    if not values:
        return np.asarray([], dtype=np.float32)
    array = np.asarray(values, dtype=np.float32)
    return array[np.isfinite(array) & (array >= 0.0)]


def _millisecond_scale(timestamps: list[float]) -> float:
    if len(timestamps) < 2:
        return 1000.0
    deltas = [timestamps[index] - timestamps[index - 1] for index in range(1, len(timestamps))]
    deltas = [delta for delta in deltas if delta > 0]
    if not deltas:
        return 1000.0
    median_delta = float(np.median(np.asarray(deltas, dtype=np.float32)))
    return 1000.0 if median_delta <= 10.0 else 1.0


def _duration_seconds(events: list[dict]) -> float:
    if len(events) < 2:
        return 0.0
    timestamps = [float(event.get("timestamp", 0.0) or 0.0) for event in events]
    scale = _millisecond_scale(timestamps)
    duration = timestamps[-1] - timestamps[0]
    if duration <= 0:
        return 0.0
    if scale == 1.0:
        return duration / 1000.0
    return duration


def _mean_std(values: np.ndarray) -> tuple[float, float]:
    if values.size == 0:
        return 0.0, 0.0
    return float(values.mean()), float(values.std())


def _percentiles(values: np.ndarray) -> tuple[float, float]:
    if values.size == 0:
        return 0.0, 0.0
    q25, q75 = np.percentile(values, [25, 75])
    return float(q25), float(q75)


def extract_typing_rhythm(events: list[dict]) -> np.ndarray:
    ordered = _sorted_events(events)
    keydowns = [event for event in ordered if str(event.get("type", "")).lower() == "keydown"]
    timestamps = [float(event.get("timestamp", 0.0) or 0.0) for event in keydowns]
    if len(timestamps) < 2:
        return np.asarray([], dtype=np.float32)
    scale = _millisecond_scale(timestamps)
    intervals = [
        (timestamps[index] - timestamps[index - 1]) * scale
        for index in range(1, len(timestamps))
        if (timestamps[index] - timestamps[index - 1]) > 0
    ]
    return _non_negative_array(intervals)


def extract_dwell_times(events: list[dict]) -> np.ndarray:
    ordered = _sorted_events(events)
    timestamps = [float(event.get("timestamp", 0.0) or 0.0) for event in ordered]
    scale = _millisecond_scale(timestamps)
    active_keys: dict[str, list[float]] = {}
    dwell_times: list[float] = []

    for event in ordered:
        event_type = str(event.get("type", "")).lower()
        key = str(event.get("key", "UNKNOWN"))
        timestamp = float(event.get("timestamp", 0.0) or 0.0)
        if event_type == "keydown":
            active_keys.setdefault(key, []).append(timestamp)
        elif event_type == "keyup":
            stack = active_keys.get(key)
            if stack:
                start = stack.pop(0)
                dwell = (timestamp - start) * scale
                if dwell >= 0:
                    dwell_times.append(dwell)

    return _non_negative_array(dwell_times)


def extract_mouse_velocity(events: list[dict]) -> np.ndarray:
    ordered = [event for event in _sorted_events(events) if str(event.get("type", "")).lower() == "mousemove"]
    timestamps = [float(event.get("timestamp", 0.0) or 0.0) for event in ordered]
    scale = _millisecond_scale(timestamps)
    velocities: list[float] = []

    for index in range(1, len(ordered)):
        previous = ordered[index - 1]
        current = ordered[index]
        dt = (float(current.get("timestamp", 0.0) or 0.0) - float(previous.get("timestamp", 0.0) or 0.0)) * scale
        if dt <= 0:
            continue
        dx = float(current.get("x", 0.0) or 0.0) - float(previous.get("x", 0.0) or 0.0)
        dy = float(current.get("y", 0.0) or 0.0) - float(previous.get("y", 0.0) or 0.0)
        distance = math.hypot(dx, dy)
        velocities.append(distance / dt)

    return _non_negative_array(velocities)


def extract_mouse_curvature(events: list[dict]) -> np.ndarray:
    ordered = [event for event in _sorted_events(events) if str(event.get("type", "")).lower() == "mousemove"]
    if len(ordered) < 3:
        return np.asarray([], dtype=np.float32)

    curvatures: list[float] = []
    for index in range(2, len(ordered)):
        first = ordered[index - 2]
        second = ordered[index - 1]
        third = ordered[index]
        v1 = np.asarray(
            [
                float(second.get("x", 0.0) or 0.0) - float(first.get("x", 0.0) or 0.0),
                float(second.get("y", 0.0) or 0.0) - float(first.get("y", 0.0) or 0.0),
            ],
            dtype=np.float32,
        )
        v2 = np.asarray(
            [
                float(third.get("x", 0.0) or 0.0) - float(second.get("x", 0.0) or 0.0),
                float(third.get("y", 0.0) or 0.0) - float(second.get("y", 0.0) or 0.0),
            ],
            dtype=np.float32,
        )
        norm_product = float(np.linalg.norm(v1) * np.linalg.norm(v2))
        if norm_product <= 1e-8:
            continue
        cosine = float(np.clip(np.dot(v1, v2) / norm_product, -1.0, 1.0))
        curvatures.append(math.degrees(math.acos(cosine)))

    return _non_negative_array(curvatures)


def extract_session_vector(events: list[dict]) -> np.ndarray:
    ordered = _sorted_events(events)
    if not ordered:
        return np.zeros(SESSION_VECTOR_SIZE, dtype=np.float32)

    typing_rhythm = extract_typing_rhythm(ordered)
    dwell_times = extract_dwell_times(ordered)
    mouse_velocity = extract_mouse_velocity(ordered)
    mouse_curvature = extract_mouse_curvature(ordered)

    mean_iki, std_iki = _mean_std(typing_rhythm)
    mean_dwell, std_dwell = _mean_std(dwell_times)
    mean_velocity, std_velocity = _mean_std(mouse_velocity)
    mean_curve, std_curve = _mean_std(mouse_curvature)

    iki_p25, iki_p75 = _percentiles(typing_rhythm)
    dwell_p25, dwell_p75 = _percentiles(dwell_times)
    velocity_p25, velocity_p75 = _percentiles(mouse_velocity)

    duration_seconds = _duration_seconds(ordered)
    clicks = [event for event in ordered if str(event.get("type", "")).lower() == "click"]
    click_rate = float(len(clicks)) / max(duration_seconds / 60.0, 1e-6) if duration_seconds > 0 else 0.0

    scroll_events = [event for event in ordered if str(event.get("type", "")).lower() == "scroll"]
    scroll_positions = [float(event.get("y", 0.0) or 0.0) for event in scroll_events]
    scroll_depth = max(scroll_positions) - min(scroll_positions) if scroll_positions else 0.0

    pages = {
        str(event.get("page", "")).strip()
        for event in ordered
        if str(event.get("page", "")).strip()
    }
    page_count = float(len(pages))

    keydowns = [event for event in ordered if str(event.get("type", "")).lower() == "keydown"]
    error_key_count = sum(
        1
        for event in keydowns
        if str(event.get("key", "")).strip().lower() in ERROR_KEYS
    )
    error_rate = float(error_key_count) / max(len(keydowns), 1)

    pause_between_words: list[float] = []
    if len(keydowns) >= 2:
        timestamps = [float(event.get("timestamp", 0.0) or 0.0) for event in keydowns]
        scale = _millisecond_scale(timestamps)
        for index in range(1, len(keydowns)):
            previous_key = str(keydowns[index - 1].get("key", "")).strip().lower()
            if previous_key not in WORD_BOUNDARY_KEYS:
                continue
            delta = (timestamps[index] - timestamps[index - 1]) * scale
            if delta >= 0:
                pause_between_words.append(delta)
    mean_pause_between_words = float(np.mean(pause_between_words)) if pause_between_words else 0.0

    vector = np.asarray(
        [
            mean_iki,
            std_iki,
            mean_dwell,
            std_dwell,
            mean_velocity,
            std_velocity,
            mean_curve,
            std_curve,
            click_rate,
            float(scroll_depth),
            float(duration_seconds),
            page_count,
            error_rate,
            mean_pause_between_words,
            iki_p25,
            iki_p75,
            dwell_p25,
            dwell_p75,
            velocity_p25,
            velocity_p75,
        ],
        dtype=np.float32,
    )
    if vector.shape != (SESSION_VECTOR_SIZE,):
        raise ValueError(f"Expected a {SESSION_VECTOR_SIZE}-dimensional session vector, got {vector.shape}.")
    return vector


__all__ = [
    "SESSION_VECTOR_SIZE",
    "extract_typing_rhythm",
    "extract_dwell_times",
    "extract_mouse_velocity",
    "extract_mouse_curvature",
    "extract_session_vector",
]
