"""
Emotion service shim.
Provides a minimal API used by other modules:
- get_emotion_state(player_id): returns an emotion vector and optional metadata.

This avoids import errors like `No module named 'emotion.service'` in containers.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Any, Tuple

from .models import EMOTION_DIM, zero_emotion_vector, clip_emotion_vector

# File used elsewhere in the backend to persist emotion state
_DEFAULT_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "emotion_state.json")


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_json(path: str, data: Dict[str, Any]) -> None:
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception:
        # Best-effort only; callers should tolerate failure
        pass


def get_emotion_state(player_id: str) -> Dict[str, Any]:
    """
    Return the emotion state for a player as a dict with keys:
    - vector: list[float] of length EMOTION_DIM
    - log: list of recent deltas
    Falls back to zero vector when state is missing.
    """
    path = os.path.abspath(_DEFAULT_STATE_FILE)
    data = _read_json(path)
    entry = data.get(player_id, {"vector": zero_emotion_vector(), "log": []})

    # Sanitize/clip vector
    raw_vec = entry.get("vector", zero_emotion_vector())
    if not isinstance(raw_vec, list) or len(raw_vec) != EMOTION_DIM:
        raw_vec = zero_emotion_vector()
    entry["vector"] = clip_emotion_vector(raw_vec)

    # Ensure log shape
    entry["log"] = entry.get("log", [])
    if len(entry["log"]) > 50:
        entry["log"] = entry["log"][-50:]

    return entry


def set_emotion_state(player_id: str, vector: list[float], scene_tag: str | None = None) -> None:
    """Persist an emotion vector for a player (best-effort)."""
    path = os.path.abspath(_DEFAULT_STATE_FILE)
    data = _read_json(path)
    data[player_id] = {
        "vector": clip_emotion_vector(vector or zero_emotion_vector()),
        "log": data.get(player_id, {}).get("log", []),
    }
    if scene_tag:
        data[player_id]["log"].append({"sceneTag": scene_tag, "delta": [0]*EMOTION_DIM})
        if len(data[player_id]["log"]) > 50:
            data[player_id]["log"] = data[player_id]["log"][-50:]
    _write_json(path, data)


def get_emotion_vector(player_id: str) -> list[float]:
    """Return just the vector for convenience callers."""
    state = get_emotion_state(player_id)
    return state.get("vector", zero_emotion_vector())