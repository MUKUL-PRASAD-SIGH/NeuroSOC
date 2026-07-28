"""
api/routes/dashboard.py

Bridges the inference runtime to the React analyst dashboard.

Exposes:
  GET  /api/alerts          — last 50 verdicts as human-readable alert cards
  GET  /api/stats           — headline counters
  GET  /api/model/version   — active model metadata
  WS   /ws/alerts           — live push of new verdicts to connected browsers
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# ── WebSocket connection registry ─────────────────────────────────────────────
_ws_clients: list[WebSocket] = []


async def broadcast_verdict(verdict_dict: dict[str, Any]) -> None:
    """Called by the inference runtime whenever a new verdict is produced."""
    alert = _verdict_to_alert(verdict_dict)
    payload = json.dumps(alert)
    dead: list[WebSocket] = []
    for ws in list(_ws_clients):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)


# ── Verdict → human-readable alert card ──────────────────────────────────────

_VERDICT_MESSAGES = {
    "HACKER": "Malicious session detected — automated threat response engaged.",
    "FORGETFUL_USER": "Anomalous behaviour consistent with a confused or locked-out user.",
    "LEGITIMATE": "Session verified as normal — no action required.",
    "INCONCLUSIVE": "Insufficient signal — session is being monitored.",
}

_VERDICT_SEVERITY = {
    "HACKER": "high",
    "FORGETFUL_USER": "medium",
    "LEGITIMATE": "low",
    "INCONCLUSIVE": "low",
}


def _human_ip_label(ip: str) -> str:
    """Best-effort location label from IP prefix (no external lookup needed)."""
    if ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172."):
        return "Internal network"
    if ip.startswith("185.220."):
        return "TOR exit node"
    if ip.startswith("1.1.1."):
        return "Cloudflare range"
    if ip.startswith("8.8."):
        return "Google range"
    return f"External — {ip}"


def _verdict_to_alert(v: dict[str, Any]) -> dict[str, Any]:
    verdict = str(v.get("verdict", "INCONCLUSIVE"))
    source_ip = str(v.get("source_ip", v.get("user_id", "unknown")))
    confidence = float(v.get("confidence", 0.0))
    xgb = str(v.get("xgb_class", ""))
    snn = float(v.get("snn_score", 0.0))
    lnn = str(v.get("lnn_class", ""))
    behav = float(v.get("behavioral_delta", 0.0))
    model_ver = str(v.get("model_version", "unknown"))
    ts = v.get("timestamp", time.time())

    # Build a plain-English message
    base_msg = _VERDICT_MESSAGES.get(verdict, _VERDICT_MESSAGES["INCONCLUSIVE"])
    detail_parts: list[str] = []
    if xgb and xgb not in ("BENIGN", ""):
        detail_parts.append(f"XGBoost flagged {xgb.lower().replace('_', ' ')}")
    if snn > 0.5:
        detail_parts.append(f"SNN spike score {snn:.2f}")
    if lnn and lnn != "BENIGN":
        detail_parts.append(f"LNN class {lnn.lower()}")
    if behav > 0.3:
        detail_parts.append(f"behavioural drift {behav:.2f}")
    message = base_msg
    if detail_parts:
        message += " — " + ", ".join(detail_parts) + "."

    # Build 20-dim radar from features_dict if present
    features = v.get("features_dict", {})
    dimension_keys = [
        ("flow_packets_per_s", "Packet Velocity"),
        ("flow_iat_std", "Session Drift"),
        ("syn_ratio", "SYN Pressure"),
        ("login_attempts", "Login Attempts"),
        ("flow_bytes_per_s", "Byte Rate"),
        ("unique_dst_ports", "Port Spread"),
        ("fwd_pkt_len_mean", "Fwd Pkt Size"),
        ("bwd_pkt_len_mean", "Bwd Pkt Size"),
        ("ack_ratio", "ACK Ratio"),
        ("rst_flag_count", "RST Flags"),
        ("fin_flag_count", "FIN Flags"),
        ("down_up_ratio", "Down/Up Ratio"),
        ("active_mean", "Active Time"),
        ("idle_mean", "Idle Time"),
        ("pkt_len_variance", "Pkt Variance"),
        ("fwd_iat_std", "Fwd IAT Std"),
        ("bwd_iat_std", "Bwd IAT Std"),
        ("flow_duration", "Flow Duration"),
        ("avg_packet_size", "Avg Pkt Size"),
        ("bytes_per_packet", "Bytes/Packet"),
    ]
    dimensions = []
    for key, label in dimension_keys:
        raw = float(features.get(key, 0.0))
        # Clamp to 0-100 for radar display
        scaled = min(100.0, round(raw * 100, 1)) if raw <= 1.0 else min(100.0, round(raw, 1))
        dimensions.append({"subject": label, "value": scaled})

    return {
        "id": str(v.get("session_id", uuid.uuid4())),
        "severity": _VERDICT_SEVERITY.get(verdict, "low"),
        "verdict": verdict,
        "score": round(confidence, 4),
        "message": message,
        "timestamp": ts if isinstance(ts, str) else _epoch_to_iso(ts),
        "sourceIp": source_ip,
        "userId": str(v.get("user_id", source_ip)),
        "userName": str(v.get("user_id", source_ip)),
        "locationLabel": _human_ip_label(source_ip),
        "modelVersion": model_ver,
        "dimensions": dimensions,
        "recentVerdicts": [],
        # Raw fields for analyst deep-dive
        "raw": {
            "snn_score": snn,
            "lnn_class": lnn,
            "xgb_class": xgb,
            "behavioral_delta": behav,
            "confidence": confidence,
        },
    }


def _epoch_to_iso(ts: float) -> str:
    import datetime
    return datetime.datetime.utcfromtimestamp(ts).isoformat() + "Z"


# ── Routes ────────────────────────────────────────────────────────────────────

def _get_runtime():
    """Late import to avoid circular dependency with main.py."""
    import main as svc
    return svc.runtime


@router.get("/api/alerts")
def get_alerts(limit: int = 50) -> list[dict[str, Any]]:
    runtime = _get_runtime()
    verdicts = runtime.latest_verdicts(limit)
    return [_verdict_to_alert(v) for v in verdicts]


@router.get("/api/stats")
def get_stats() -> dict[str, Any]:
    runtime = _get_runtime()
    verdicts = runtime.latest_verdicts(200)
    hacker_count = sum(1 for v in verdicts if v.get("verdict") == "HACKER")
    scores = [float(v.get("confidence", 0)) for v in verdicts]
    avg_score = round((sum(scores) / len(scores)) * 100, 2) if scores else 0.0
    return {
        "totalTransactions": runtime._processed_messages,
        "hackerDetections": hacker_count,
        "avgRiskScore": avg_score,
        "liveAlerts": len(verdicts),
    }


@router.get("/api/model/version")
def get_model_version() -> dict[str, Any]:
    runtime = _get_runtime()
    ver = runtime.engine.current_model_version or "unknown"
    f1 = runtime.engine.current_validation_f1 or {}
    return {
        "versions": [{"label": "Active", "value": ver}],
        "validationF1": [
            {"label": k.upper(), "value": round(float(v), 4)}
            for k, v in f1.items()
            if v is not None
        ],
        "lastRetrainedAt": None,
    }


@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket) -> None:
    await websocket.accept()
    _ws_clients.append(websocket)
    # Send current queue immediately on connect
    runtime = _get_runtime()
    snapshot = [_verdict_to_alert(v) for v in runtime.latest_verdicts(50)]
    await websocket.send_text(json.dumps(snapshot))
    try:
        while True:
            # Keep connection alive; new verdicts arrive via broadcast_verdict()
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"ping": True}))
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)
