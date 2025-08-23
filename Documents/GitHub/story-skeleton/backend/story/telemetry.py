from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def log_scene_decision(
    scene_index: int,
    selected_beat_id: str,
    top_candidates: List[Dict[str, Any]],
    npcs_present: List[str],
    trust_changes: Dict[str, float],
    tension_before_after: tuple[float, float],
) -> None:
    record = {
        "scene_index": scene_index,
        "selected_beat": selected_beat_id,
        "top_candidates": top_candidates,
        "npcs_present": npcs_present,
        "trust_changes": trust_changes,
        "tension": {
            "before": round(tension_before_after[0], 3),
            "after": round(tension_before_after[1], 3),
        },
    }
    print(json.dumps({"telemetry": record}))


def log_choice_generated(
    scene_index: int,
    beat_id: str,
    text: str,
    source: str = "auto3"
) -> None:
    """Log when a 3rd choice is generated."""
    record = {
        "scene_index": scene_index,
        "beat_id": beat_id,
        "choice_text": text,
        "source": source,
        "type": "choice_generated"
    }
    print(json.dumps({"telemetry": record}))


def log_free_text(
    scene_index: int,
    truncated_text: str,
    mapped_text: str
) -> None:
    """Log free-text processing."""
    record = {
        "scene_index": scene_index,
        "truncated_text": truncated_text,
        "mapped_text": mapped_text,
        "type": "free_text_processed"
    }
    print(json.dumps({"telemetry": record}))


def log_consequence_change(
    scene_index: int,
    changes: Dict[str, Any]
) -> None:
    """Log consequence fabric changes (flags, promises, reputation, resources)."""
    record = {
        "scene_index": scene_index,
        "consequence_changes": changes,
        "type": "consequence_change"
    }
    print(json.dumps({"telemetry": record}))


def log_toast_emitted(
    scene_index: int,
    kind: str,
    label: str,
    npc_id: Optional[str] = None,
    delta: Optional[float] = None
) -> None:
    """Log when a consequence toast is emitted."""
    record = {
        "scene_index": scene_index,
        "kind": kind,
        "label": label,
        "npc_id": npc_id,
        "delta": delta,
        "type": "toast_emitted"
    }
    print(json.dumps({"telemetry": record}))

