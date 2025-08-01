from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ------------------------------------------------------------
# storage helpers
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "soul_map.json"


def _load() -> Dict[str, Any]:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save(data: Dict[str, Any]) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ------------------------------------------------------------
# default soul map structure
# ------------------------------------------------------------
VIRTUES = ["courage", "compassion", "wisdom", "creativity", "justice", "temperance"]
SHADOWS = ["fear", "pride", "apathy"]
MOTIVATIONS = ["selfActualization", "externalValidation", "collective"]
ARCHETYPES = [
    "hero",
    "rebel",
    "sage",
    "caregiver",
    "magician",
    "lover",
    "sovereign",
    "explorer",
]


def default_soulmap() -> Dict[str, Any]:
    return {
        "coreVirtues": {k: 0.0 for k in VIRTUES},
        "shadowIndex": {k: 0.0 for k in SHADOWS},
        "motivations": {k: 0.0 for k in MOTIVATIONS},
        "archetypeResonance": {k: 0.0 for k in ARCHETYPES},
        "dynamicStats": {"resilience": 50, "empathy": 50},
        "npcTrust": {},
        "intentVec": [0.0] * 768,
    }


# ------------------------------------------------------------
# delta map – minimal demo values
# ------------------------------------------------------------
CHOICE_DELTAS: Dict[str, Dict[str, Any]] = {
    "battle": {"coreVirtues": {"courage": 0.1}},
    "hide": {"coreVirtues": {"courage": -0.1}},
    "help_npc": {
        "coreVirtues": {"compassion": 0.2},
        "npcTrust": {"kaiTrust": 5},
    },
}


# ------------------------------------------------------------
# pydantic models
# ------------------------------------------------------------
class DeltaRequest(BaseModel):
    playerId: str
    choiceId: str


class SoulMapResponse(BaseModel):
    playerId: str
    traits: Dict[str, Any]
    summary: str


SoulMapResponse.model_rebuild()


# ------------------------------------------------------------
# API setup
# ------------------------------------------------------------
app = FastAPI(title="SoulMap API")


@app.get("/v1/soulmap/{player_id}", response_model=SoulMapResponse)
def get_soulmap(player_id: str) -> SoulMapResponse:
    data = _load()
    traits = data.setdefault(player_id, default_soulmap())
    _save(data)
    summary = ", ".join(f"{k}:{v:.2f}" for k, v in traits["coreVirtues"].items())
    return SoulMapResponse(playerId=player_id, traits=traits, summary=summary)


@app.post("/v1/soulmap/delta", response_model=SoulMapResponse)
def apply_delta(req: DeltaRequest) -> SoulMapResponse:
    data = _load()
    traits = data.setdefault(req.playerId, default_soulmap())
    delta = CHOICE_DELTAS.get(req.choiceId)
    if delta is None:
        raise HTTPException(404, "unknown choiceId")
    _apply_delta(traits, delta)
    data[req.playerId] = traits
    _save(data)
    summary = ", ".join(f"{k}:{v:.2f}" for k, v in traits["coreVirtues"].items())
    return SoulMapResponse(playerId=req.playerId, traits=traits, summary=summary)


@app.get("/soulmap/ui")
def soulmap_ui() -> str:
    return (
        "<html><body><h1>Soul Map</h1>"
        "<p>Placeholder visualization.</p></body></html>"
    )


# ------------------------------------------------------------
# helpers
# ------------------------------------------------------------

def _apply_delta(target: Dict[str, Any], delta: Dict[str, Any]) -> None:
    for key, value in delta.items():
        if isinstance(value, dict):
            node = target.setdefault(key, {})
            for sub, dv in value.items():
                node[sub] = _clamp(node.get(sub, 0.0) + dv, key, sub)
        elif key == "intentVec":
            target[key] = _add_vectors(target.get(key, [0.0] * 768), value)


def _add_vectors(a: List[float], b: List[float]) -> List[float]:
    return [x + y for x, y in zip(a, b)]


def _clamp(val: float, section: str, field: str) -> float:
    if section in {"dynamicStats", "npcTrust"}:
        return max(0.0, min(100.0, val))
    if section == "motivations":
        return max(0.0, min(1.0, val))
    return max(-1.0, min(1.0, val))

