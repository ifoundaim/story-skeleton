from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Tuple

from .state import StoryState
from .beat_dsl import evaluate_preconditions


def _theme_alignment_score(beat: Dict[str, Any], state: StoryState) -> float:
    theme = (state.player or {}).get("theme", "").lower()
    tags = [t.lower() for t in beat.get("tags", [])]
    if not theme or not tags:
        return 0.5
    return 1.0 if theme in tags else 0.5


def _arc_progress_score(beat: Dict[str, Any], state: StoryState, npc_candidates: List[str]) -> float:
    # Reward under-served NPCs (few interactions) for beats that require an npc
    if not npc_candidates:
        return 0.0
    interactions = [int(state.npcs.get(n, {}).get("interactions", 0)) for n in npc_candidates]
    if not interactions:
        return 0.0
    min_inter = min(interactions)
    max_inter = max(interactions)
    if max_inter == 0:
        return 1.0
    return 1.0 - (min_inter / max(1, max_inter))


def _tension_fit_score(beat: Dict[str, Any], state: StoryState) -> float:
    target = state.target_tension
    current = float(state.tension)
    # Map closeness to score (within 15% is good)
    tolerance = 0.15
    diff = abs(current - target)
    return max(0.0, 1.0 - diff / tolerance)


def _diversity_penalty(beat: Dict[str, Any], state: StoryState) -> float:
    recent_tags: List[str] = state.flags.get("recent_tags", [])
    diversity_cfg = (state.flags.get("config") or {}).get("diversity") or {}
    penalty_per_repeat = float(diversity_cfg.get("penalty_per_repeat", 0.07))
    window = int(diversity_cfg.get("window", 4))
    tags = beat.get("tags", [])

    if not tags or not recent_tags:
        return 0.0

    recent_window = recent_tags[-window * 2 :]  # last N*2 tags considered
    repeats = sum(1 for tag in tags if tag in recent_window)
    return -penalty_per_repeat * float(repeats)


def _world_hook_match(beat: Dict[str, Any], state: StoryState) -> float:
    hooks = set(beat.get("hook_tags", []) or [])
    world = set((state.flags.get("world_hooks") or []))
    if not hooks or not world:
        return 0.0
    overlap = len(hooks & world)
    return min(1.0, overlap / max(1, len(hooks)))


def _player_synergy(beat: Dict[str, Any], state: StoryState) -> float:
    # Very simple synergy using player archetype
    archetype = (state.player or {}).get("archetype", "").lower()
    tags = [t.lower() for t in beat.get("tags", [])]
    if not archetype or not tags:
        return 0.5
    good = {
        "warrior": {"action", "conflict", "bond"},
        "sage": {"lore", "mentor", "reveal"},
        "trickster": {"choice", "ethics", "travel"},
    }
    matches = good.get(archetype, set())
    return 1.0 if any(tag in matches for tag in tags) else 0.5


def score_beat(beat: Dict[str, Any], state: StoryState, npc_candidates: List[str]) -> float:
    cfg = state.flags.get("config") or {}
    weights = cfg.get("weights") or {}

    score = 0.0
    score += float(weights.get("theme_alignment", 0.25)) * _theme_alignment_score(beat, state)
    score += float(weights.get("arc_progress", 0.20)) * _arc_progress_score(beat, state, npc_candidates)
    score += float(weights.get("tension_fit", 0.20)) * _tension_fit_score(beat, state)
    score += float(weights.get("diversity_penalty", -0.15)) * (1.0 + _diversity_penalty(beat, state))
    score += float(weights.get("world_hook_match", 0.10)) * _world_hook_match(beat, state)
    score += float(weights.get("player_synergy", 0.15)) * _player_synergy(beat, state)
    return score


def select_next_beat(state: StoryState, candidates: List[Dict[str, Any]], weights: Dict[str, float], rng: random.Random) -> Dict[str, Any]:
    # Score all candidates, add epsilon noise, pick top
    scored: List[Tuple[float, Dict[str, Any]]] = []
    epsilon = float(weights.get("epsilon", 0.02) or 0.02)

    for beat in candidates:
        # Determine whether this beat requires NPCs to be present
        npcs_allowed = beat.get("npcs_allowed", "any")
        requires_npc = npcs_allowed in ("one", "group")
        npc_candidates = list(state.npcs.keys()) if requires_npc else []
        base = score_beat(beat, state, npc_candidates)
        noise = rng.uniform(-epsilon, epsilon)
        scored.append((base + noise, beat))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_score, top_beat = scored[0]

    # Keep top candidates for telemetry
    state.flags["last_top_candidates"] = [
        {"id": b.get("id"), "score": round(s, 4)} for s, b in scored[:5]
    ]
    return top_beat

