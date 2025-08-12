from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


Phase = Literal["early", "mid", "late"]


@dataclass
class StoryState:
    scene_index: int
    phase: Phase
    tension: float
    target_curve: List[float]
    player: Dict[str, Any]
    npcs: Dict[str, Dict[str, Any]]  # trust: float, arc_state: str, interactions: int, last_invite_scene: Optional[int]
    party: List[str]
    flags: Dict[str, Any] = field(default_factory=dict)

    def update_phase_from_curve(self) -> None:
        # Derive phase from scene index heuristics (0–6 early, 7–21 mid, 22–29 late)
        if self.scene_index <= 6:
            self.phase = "early"
        elif self.scene_index <= 21:
            self.phase = "mid"
        else:
            self.phase = "late"

    def bump_interactions(self, npc_id: str, amount: int = 1) -> None:
        npc = self.npcs.get(npc_id)
        if npc is None:
            return
        npc["interactions"] = int(npc.get("interactions", 0)) + amount

    def set_arc(self, npc_id: str, new_state: str) -> None:
        npc = self.npcs.get(npc_id)
        if npc is None:
            return
        npc["arc_state"] = new_state

    def apply_trust_delta(self, npc_id: str, delta: float) -> None:
        npc = self.npcs.get(npc_id)
        if npc is None:
            return
        trust_before = float(npc.get("trust", 0.0))
        trust_after = max(0.0, min(1.0, trust_before + delta))
        npc["trust"] = trust_after

    def set_last_invite_scene(self, npc_id: str, scene_index: int) -> None:
        npc = self.npcs.get(npc_id)
        if npc is None:
            return
        npc["last_invite_scene"] = scene_index

    @property
    def target_tension(self) -> float:
        if not self.target_curve:
            return self.tension
        idx = max(0, min(len(self.target_curve) - 1, self.scene_index))
        return float(self.target_curve[idx])

    def record_recent_tags(self, tags: List[str]) -> None:
        recent_tags: List[str] = self.flags.setdefault("recent_tags", [])
        recent_tags.extend(tags)
        # Truncate to a reasonable window (use diversity.window if present)
        diversity_cfg = (self.flags.get("config") or {}).get("diversity") or {}
        window = int(diversity_cfg.get("window", 4)) * 3  # keep a larger memory to allow counting repeats
        if len(recent_tags) > window:
            self.flags["recent_tags"] = recent_tags[-window:]

